"""Run Phase 6 data validation, drift, prediction, and audit monitoring.

The script treats the earliest 80 percent of the historical model table as the
reference window and the latest 20 percent as the monitored window. This mirrors
the time-based validation strategy used in Phase 3 while producing reusable
monitoring artifacts for operations and governance review.
"""

from __future__ import annotations

import json
import math
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOCAL_LIB = PROJECT_ROOT / ".pythonlibs"
if LOCAL_LIB.exists() and str(LOCAL_LIB) not in sys.path:
    sys.path.insert(0, str(LOCAL_LIB))

import joblib


MODEL_TABLE_PATH = PROJECT_ROOT / "data_outputs" / "model_table.csv"
PHASE3_DIR = PROJECT_ROOT / "data_outputs" / "phase3"
PHASE5_DIR = PROJECT_ROOT / "data_outputs" / "phase5"
PHASE6_DIR = PROJECT_ROOT / "data_outputs" / "phase6"
MODELS_DIR = PROJECT_ROOT / "models"
LOG_PATH = PROJECT_ROOT / "logs" / "prediction_audit_log.jsonl"

PSI_WATCH_THRESHOLD = 0.10
PSI_DRIFT_THRESHOLD = 0.20
EPSILON = 1e-6


def rel_path(path: Path) -> str:
    return path.relative_to(PROJECT_ROOT).as_posix()


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def severity_from_psi(psi: float) -> str:
    if psi >= PSI_DRIFT_THRESHOLD:
        return "drift"
    if psi >= PSI_WATCH_THRESHOLD:
        return "watch"
    return "stable"


def split_reference_current(
    df: pd.DataFrame,
    sort_columns: list[str],
    train_ratio: float = 0.80,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    sorted_df = df.sort_values(sort_columns).reset_index(drop=True)
    split_idx = int(len(sorted_df) * train_ratio)
    reference = sorted_df.iloc[:split_idx].copy()
    current = sorted_df.iloc[split_idx:].copy()
    return reference, current


def psi_from_proportions(reference_props: pd.Series, current_props: pd.Series) -> float:
    categories = sorted(set(reference_props.index) | set(current_props.index))
    psi = 0.0
    for category in categories:
        reference_value = max(float(reference_props.get(category, 0.0)), EPSILON)
        current_value = max(float(current_props.get(category, 0.0)), EPSILON)
        psi += (current_value - reference_value) * math.log(current_value / reference_value)
    return round(float(psi), 6)


def categorical_psi(reference: pd.Series, current: pd.Series) -> tuple[float, dict[str, float], dict[str, float]]:
    reference_clean = reference.astype("string").fillna("__MISSING__")
    current_clean = current.astype("string").fillna("__MISSING__")
    reference_props = reference_clean.value_counts(normalize=True)
    current_props = current_clean.value_counts(normalize=True)
    psi = psi_from_proportions(reference_props, current_props)
    return (
        psi,
        {str(key): round(float(value), 6) for key, value in reference_props.items()},
        {str(key): round(float(value), 6) for key, value in current_props.items()},
    )


def numeric_bins(reference: pd.Series, max_bins: int = 10) -> np.ndarray:
    numeric_reference = pd.to_numeric(reference, errors="coerce").dropna()
    if numeric_reference.empty or numeric_reference.nunique() <= 1:
        return np.array([-np.inf, np.inf])
    quantiles = np.linspace(0, 1, max_bins + 1)
    edges = np.unique(np.quantile(numeric_reference, quantiles))
    if len(edges) <= 2:
        min_value = float(numeric_reference.min())
        max_value = float(numeric_reference.max())
        if min_value == max_value:
            return np.array([-np.inf, np.inf])
        edges = np.array([min_value, max_value])
    edges[0] = -np.inf
    edges[-1] = np.inf
    return edges


def numeric_psi(reference: pd.Series, current: pd.Series) -> tuple[float, dict[str, float], dict[str, float]]:
    bins = numeric_bins(reference)
    reference_bucket = pd.cut(pd.to_numeric(reference, errors="coerce"), bins=bins, include_lowest=True)
    current_bucket = pd.cut(pd.to_numeric(current, errors="coerce"), bins=bins, include_lowest=True)

    reference_labels = reference_bucket.astype("string").fillna("__MISSING__")
    current_labels = current_bucket.astype("string").fillna("__MISSING__")
    reference_props = reference_labels.value_counts(normalize=True)
    current_props = current_labels.value_counts(normalize=True)
    psi = psi_from_proportions(reference_props, current_props)
    return (
        psi,
        {str(key): round(float(value), 6) for key, value in reference_props.items()},
        {str(key): round(float(value), 6) for key, value in current_props.items()},
    )


def compute_feature_drift(
    reference: pd.DataFrame,
    current: pd.DataFrame,
    categorical_features: list[str],
    numeric_features: list[str],
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for feature in categorical_features:
        psi, reference_dist, current_dist = categorical_psi(reference[feature], current[feature])
        rows.append(
            {
                "feature": feature,
                "feature_type": "categorical",
                "psi": psi,
                "severity": severity_from_psi(psi),
                "reference_missing_rate": round(float(reference[feature].isna().mean()), 6),
                "current_missing_rate": round(float(current[feature].isna().mean()), 6),
                "reference_summary": json.dumps(reference_dist, sort_keys=True),
                "current_summary": json.dumps(current_dist, sort_keys=True),
            }
        )
    for feature in numeric_features:
        psi, reference_dist, current_dist = numeric_psi(reference[feature], current[feature])
        rows.append(
            {
                "feature": feature,
                "feature_type": "numeric",
                "psi": psi,
                "severity": severity_from_psi(psi),
                "reference_missing_rate": round(float(reference[feature].isna().mean()), 6),
                "current_missing_rate": round(float(current[feature].isna().mean()), 6),
                "reference_summary": json.dumps(reference_dist, sort_keys=True),
                "current_summary": json.dumps(current_dist, sort_keys=True),
            }
        )
    return pd.DataFrame(rows).sort_values("psi", ascending=False)


def expected_numeric_rules(reference: pd.DataFrame, numeric_features: list[str]) -> dict[str, dict[str, float]]:
    rules: dict[str, dict[str, float]] = {}
    for feature in numeric_features:
        series = pd.to_numeric(reference[feature], errors="coerce")
        rules[feature] = {
            "reference_min": round(float(series.min()), 6),
            "reference_max": round(float(series.max()), 6),
        }

    hard_rules = {
        "age": {"hard_min": 0.0, "hard_max": 120.0},
        "chronic_flag": {"hard_min": 0.0, "hard_max": 1.0},
        "length_of_stay_hours": {"hard_min": 0.0},
        "billed_amount": {"hard_min": 0.0},
        "approved_amount": {"hard_min": 0.0},
        "payment_days": {"hard_min": 0.0},
        "patient_prior_visit_count": {"hard_min": 0.0},
        "patient_prior_avg_los_hours": {"hard_min": 0.0},
        "provider_prior_claim_count": {"hard_min": 0.0},
        "provider_prior_rejection_rate": {"hard_min": 0.0, "hard_max": 1.0},
        "days_since_registration": {},
        "billing_lag_days": {},
        "visit_month": {"hard_min": 1.0, "hard_max": 12.0},
        "visit_quarter": {"hard_min": 1.0, "hard_max": 4.0},
        "visit_day_of_week": {"hard_min": 0.0, "hard_max": 6.0},
        "visit_week_of_year": {"hard_min": 1.0, "hard_max": 53.0},
        "billing_month": {"hard_min": 1.0, "hard_max": 12.0},
        "billing_day_of_week": {"hard_min": 0.0, "hard_max": 6.0},
    }
    for feature, feature_rules in hard_rules.items():
        if feature in rules:
            rules[feature].update(feature_rules)

    for feature in numeric_features:
        if feature.endswith("_flag") and feature in rules:
            rules[feature].update({"hard_min": 0.0, "hard_max": 1.0})
    return rules


def add_validation_row(
    rows: list[dict[str, Any]],
    check_type: str,
    field: str,
    rule: str,
    expected: str,
    observed: str,
    violation_count: int,
    denominator: int,
    severity: str,
) -> None:
    violation_rate = 0.0 if denominator == 0 else violation_count / denominator
    rows.append(
        {
            "check_type": check_type,
            "field": field,
            "rule": rule,
            "expected": expected,
            "observed": observed,
            "violation_count": int(violation_count),
            "denominator": int(denominator),
            "violation_rate": round(float(violation_rate), 6),
            "severity": severity,
        }
    )


def validate_current_data(
    reference: pd.DataFrame,
    current: pd.DataFrame,
    categorical_features: list[str],
    numeric_features: list[str],
    required_fields: list[str],
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    current_count = len(current)

    for field in required_fields:
        missing_count = int(current[field].isna().sum())
        add_validation_row(
            rows,
            "missing_value",
            field,
            "Required model input should be populated.",
            "missing_count = 0",
            f"missing_count = {missing_count}",
            missing_count,
            current_count,
            "fail" if missing_count else "pass",
        )

    for field in categorical_features:
        reference_categories = set(reference[field].dropna().astype(str).unique())
        current_categories = set(current[field].dropna().astype(str).unique())
        unseen_categories = sorted(current_categories - reference_categories)
        violation_count = int(current[field].dropna().astype(str).isin(unseen_categories).sum())
        add_validation_row(
            rows,
            "unseen_category",
            field,
            "Incoming category should be present in reference data.",
            json.dumps(sorted(reference_categories)),
            json.dumps(unseen_categories),
            violation_count,
            current_count,
            "fail" if violation_count else "pass",
        )

    numeric_rules = expected_numeric_rules(reference, numeric_features)
    for field, rules in numeric_rules.items():
        current_numeric = pd.to_numeric(current[field], errors="coerce")
        reference_min = rules["reference_min"]
        reference_max = rules["reference_max"]
        outside_reference = current_numeric.notna() & (
            (current_numeric < reference_min) | (current_numeric > reference_max)
        )
        add_validation_row(
            rows,
            "reference_range",
            field,
            "Incoming numeric values should remain within observed reference min/max.",
            f"[{reference_min}, {reference_max}]",
            f"min={round(float(current_numeric.min()), 6)}, max={round(float(current_numeric.max()), 6)}",
            int(outside_reference.sum()),
            int(current_numeric.notna().sum()),
            "warn" if outside_reference.any() else "pass",
        )

        hard_min = rules.get("hard_min")
        hard_max = rules.get("hard_max")
        if hard_min is not None or hard_max is not None:
            hard_violation = pd.Series(False, index=current_numeric.index)
            expected_parts: list[str] = []
            if hard_min is not None:
                hard_violation = hard_violation | (current_numeric < hard_min)
                expected_parts.append(f">= {hard_min:g}")
            if hard_max is not None:
                hard_violation = hard_violation | (current_numeric > hard_max)
                expected_parts.append(f"<= {hard_max:g}")
            hard_violation = hard_violation & current_numeric.notna()
            add_validation_row(
                rows,
                "business_range",
                field,
                "Incoming numeric values should pass business validity limits.",
                " and ".join(expected_parts),
                f"min={round(float(current_numeric.min()), 6)}, max={round(float(current_numeric.max()), 6)}",
                int(hard_violation.sum()),
                int(current_numeric.notna().sum()),
                "fail" if hard_violation.any() else "pass",
            )

    critical_fields = ["approved_amount", "payment_days", "length_of_stay_hours"]
    for field in critical_fields:
        if field in current.columns:
            missing_count = int(current[field].isna().sum())
            invalid_count = int((pd.to_numeric(current[field], errors="coerce") < 0).sum())
            add_validation_row(
                rows,
                "critical_field_quality",
                field,
                "Critical Phase 2 reliability field should be non-missing and non-negative.",
                "missing = 0 and negative = 0",
                f"missing={missing_count}, negative={invalid_count}",
                missing_count + invalid_count,
                current_count,
                "fail" if missing_count + invalid_count else "pass",
            )
    return pd.DataFrame(rows)


def prepare_model_frame(df: pd.DataFrame, feature_set: dict[str, Any]) -> pd.DataFrame:
    features = feature_set["categorical_features"] + feature_set["numeric_features"]
    model_frame = df[features].copy()
    for column in feature_set["categorical_features"]:
        model_frame[column] = model_frame[column].astype("string").fillna("Unknown")
    for column in feature_set["numeric_features"]:
        model_frame[column] = pd.to_numeric(model_frame[column], errors="coerce")
    return model_frame


def prediction_distribution(model: Any, df: pd.DataFrame, feature_set: dict[str, Any]) -> pd.Series:
    predictions = pd.Series(model.predict(prepare_model_frame(df, feature_set)), name="prediction")
    return predictions.astype(str).value_counts(normalize=True)


def compute_prediction_drift(
    df: pd.DataFrame,
    task_name: str,
    model_path: Path,
    feature_set: dict[str, Any],
    sort_columns: list[str],
    business_class: str,
) -> dict[str, Any]:
    model = joblib.load(model_path)
    reference, current = split_reference_current(df, sort_columns)
    reference_dist = prediction_distribution(model, reference, feature_set)
    current_dist = prediction_distribution(model, current, feature_set)
    psi = psi_from_proportions(reference_dist, current_dist)
    return {
        "task_name": task_name,
        "model_artifact": rel_path(model_path),
        "reference_rows": int(len(reference)),
        "current_rows": int(len(current)),
        "reference_prediction_distribution": {
            str(key): round(float(value), 6) for key, value in reference_dist.items()
        },
        "current_prediction_distribution": {
            str(key): round(float(value), 6) for key, value in current_dist.items()
        },
        "prediction_psi": psi,
        "severity": severity_from_psi(psi),
        "business_class": business_class,
        "reference_business_class_rate": round(float(reference_dist.get(business_class, 0.0)), 6),
        "current_business_class_rate": round(float(current_dist.get(business_class, 0.0)), 6),
    }


def summarize_audit_log(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "log_path": rel_path(path),
            "available": False,
            "record_count": 0,
            "message": "No prediction audit log found. Start the API and make predictions to populate this log.",
        }

    records: list[dict[str, Any]] = []
    invalid_line_count = 0
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            try:
                records.append(json.loads(stripped))
            except json.JSONDecodeError:
                invalid_line_count += 1

    model_versions = sorted({str(record.get("model_version")) for record in records if record.get("model_version")})
    api_versions = sorted({str(record.get("api_version")) for record in records if record.get("api_version")})
    request_ids = [record.get("request_id") for record in records if record.get("request_id")]
    missing_required_metadata = sum(
        1
        for record in records
        if not all(
            record.get(field)
            for field in [
                "request_id",
                "model_name",
                "model_version",
                "prediction",
                "feature_hash",
                "logged_at_utc",
            ]
        )
    )
    model_counts = Counter(str(record.get("model_name", "unknown")) for record in records)
    logged_times = sorted(str(record.get("logged_at_utc")) for record in records if record.get("logged_at_utc"))

    return {
        "log_path": rel_path(path),
        "available": True,
        "record_count": int(len(records)),
        "invalid_line_count": int(invalid_line_count),
        "model_record_counts": dict(sorted(model_counts.items())),
        "model_versions": model_versions,
        "api_versions": api_versions,
        "missing_required_metadata_count": int(missing_required_metadata),
        "duplicate_request_id_count": int(sum(count - 1 for count in Counter(request_ids).values() if count > 1)),
        "unique_feature_hash_count": int(len({record.get("feature_hash") for record in records if record.get("feature_hash")})),
        "first_logged_at_utc": logged_times[0] if logged_times else None,
        "last_logged_at_utc": logged_times[-1] if logged_times else None,
    }


def load_model_table() -> pd.DataFrame:
    date_columns = ["registration_date", "visit_date", "billing_date"]
    return pd.read_csv(MODEL_TABLE_PATH, parse_dates=date_columns)


def main() -> None:
    PHASE6_DIR.mkdir(parents=True, exist_ok=True)
    df = load_model_table()
    risk_feature_set = read_json(PHASE3_DIR / "risk_feature_set.json")
    claim_feature_set = read_json(PHASE3_DIR / "claim_feature_set.json")

    risk_reference, risk_current = split_reference_current(df, ["visit_date", "visit_id"])
    claim_reference, claim_current = split_reference_current(df, ["billing_date", "bill_id"])

    categorical_features = sorted(
        set(risk_feature_set["categorical_features"]) | set(claim_feature_set["categorical_features"])
    )
    numeric_features = sorted(
        set(risk_feature_set["numeric_features"])
        | set(claim_feature_set["numeric_features"])
        | {"approved_amount", "payment_days"}
    )
    required_fields = sorted(set(categorical_features) | set(risk_feature_set["numeric_features"]) | set(claim_feature_set["numeric_features"]))

    validation_report = validate_current_data(
        reference=claim_reference,
        current=claim_current,
        categorical_features=categorical_features,
        numeric_features=numeric_features,
        required_fields=required_fields,
    )
    validation_report.to_csv(PHASE6_DIR / "data_validation_report.csv", index=False)

    risk_feature_drift = compute_feature_drift(
        reference=risk_reference,
        current=risk_current,
        categorical_features=risk_feature_set["categorical_features"],
        numeric_features=risk_feature_set["numeric_features"],
    )
    risk_feature_drift.insert(0, "model_task", "risk")

    claim_feature_drift = compute_feature_drift(
        reference=claim_reference,
        current=claim_current,
        categorical_features=claim_feature_set["categorical_features"],
        numeric_features=claim_feature_set["numeric_features"],
    )
    claim_feature_drift.insert(0, "model_task", "claim")

    feature_drift = pd.concat([risk_feature_drift, claim_feature_drift], ignore_index=True)
    feature_drift = feature_drift.sort_values("psi", ascending=False)
    feature_drift.to_csv(PHASE6_DIR / "feature_drift_report.csv", index=False)

    prediction_drift = [
        compute_prediction_drift(
            df=df,
            task_name="risk",
            model_path=MODELS_DIR / "risk_selected_model.joblib",
            feature_set=risk_feature_set,
            sort_columns=["visit_date", "visit_id"],
            business_class="High",
        ),
        compute_prediction_drift(
            df=df,
            task_name="claim",
            model_path=MODELS_DIR / "claim_selected_model.joblib",
            feature_set=claim_feature_set,
            sort_columns=["billing_date", "bill_id"],
            business_class="Rejected",
        ),
    ]
    pd.DataFrame(prediction_drift).to_csv(PHASE6_DIR / "prediction_drift_report.csv", index=False)

    audit_summary = summarize_audit_log(LOG_PATH)
    write_json(PHASE6_DIR / "audit_log_summary.json", audit_summary)

    validation_counts = validation_report["severity"].value_counts().to_dict()
    feature_drift_counts = feature_drift["severity"].value_counts().to_dict()
    prediction_drift_counts = Counter(row["severity"] for row in prediction_drift)
    summary = {
        "generated_at_utc": utc_now(),
        "source_model_table": rel_path(MODEL_TABLE_PATH),
        "monitoring_method": {
            "reference_window": "Earliest 80 percent of records using the same time ordering as model validation.",
            "current_window": "Latest 20 percent of records used as a simulated incoming monitoring window.",
            "feature_drift_metric": "Population Stability Index for numeric and categorical model inputs.",
            "prediction_drift_metric": "Population Stability Index across predicted class distributions.",
            "psi_thresholds": {
                "stable": f"< {PSI_WATCH_THRESHOLD}",
                "watch": f">= {PSI_WATCH_THRESHOLD} and < {PSI_DRIFT_THRESHOLD}",
                "drift": f">= {PSI_DRIFT_THRESHOLD}",
            },
        },
        "row_counts": {
            "total_model_table_rows": int(len(df)),
            "risk_reference_rows": int(len(risk_reference)),
            "risk_current_rows": int(len(risk_current)),
            "claim_reference_rows": int(len(claim_reference)),
            "claim_current_rows": int(len(claim_current)),
        },
        "date_windows": {
            "risk_reference": {
                "start": str(risk_reference["visit_date"].min().date()),
                "end": str(risk_reference["visit_date"].max().date()),
            },
            "risk_current": {
                "start": str(risk_current["visit_date"].min().date()),
                "end": str(risk_current["visit_date"].max().date()),
            },
            "claim_reference": {
                "start": str(claim_reference["billing_date"].min().date()),
                "end": str(claim_reference["billing_date"].max().date()),
            },
            "claim_current": {
                "start": str(claim_current["billing_date"].min().date()),
                "end": str(claim_current["billing_date"].max().date()),
            },
        },
        "data_validation": {
            "checks": int(len(validation_report)),
            "severity_counts": {str(key): int(value) for key, value in validation_counts.items()},
            "failed_checks": int((validation_report["severity"] == "fail").sum()),
            "warning_checks": int((validation_report["severity"] == "warn").sum()),
        },
        "feature_drift": {
            "features_evaluated": int(len(feature_drift)),
            "severity_counts": {str(key): int(value) for key, value in feature_drift_counts.items()},
            "top_drift_features": feature_drift.head(10)[["model_task", "feature", "feature_type", "psi", "severity"]].to_dict("records"),
        },
        "prediction_drift": {
            "tasks_evaluated": int(len(prediction_drift)),
            "severity_counts": {str(key): int(value) for key, value in prediction_drift_counts.items()},
            "tasks": prediction_drift,
        },
        "audit_log": audit_summary,
        "output_artifacts": {
            "data_validation_report": rel_path(PHASE6_DIR / "data_validation_report.csv"),
            "feature_drift_report": rel_path(PHASE6_DIR / "feature_drift_report.csv"),
            "prediction_drift_report": rel_path(PHASE6_DIR / "prediction_drift_report.csv"),
            "audit_log_summary": rel_path(PHASE6_DIR / "audit_log_summary.json"),
        },
    }
    write_json(PHASE6_DIR / "drift_detection_summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
