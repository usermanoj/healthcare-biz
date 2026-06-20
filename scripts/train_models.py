"""Train Phase 3 classification models for visit risk and claim outcome.

This script trains two model systems:
    Model A: Visit Risk Classification, target = risk_score
    Model B: Claim Outcome Classification, target = claim_status

Each model system uses:
    - leakage-aware feature selection
    - time-based train/test split
    - baseline Logistic Regression
    - tuned Random Forest advanced model
    - saved deployable .joblib artifacts
    - metrics and feature-set documentation
"""

from __future__ import annotations

import json
import sys
import warnings
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOCAL_LIB = PROJECT_ROOT / ".pythonlibs"
if LOCAL_LIB.exists():
    sys.path.insert(0, str(LOCAL_LIB))

import joblib
import numpy as np
import pandas as pd
from scipy.optimize import OptimizeWarning
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


MODEL_TABLE_PATH = PROJECT_ROOT / "data_outputs" / "model_table.csv"
FEATURE_SCHEMA_PATH = PROJECT_ROOT / "data_outputs" / "feature_schema.json"
PHASE3_OUTPUT_DIR = PROJECT_ROOT / "data_outputs" / "phase3"
MODELS_DIR = PROJECT_ROOT / "models"
RANDOM_STATE = 42

warnings.filterwarnings(
    "ignore",
    message="Unknown solver options: iprint",
    category=OptimizeWarning,
)


@dataclass(frozen=True)
class ModelTask:
    task_name: str
    business_name: str
    target: str
    sort_columns: list[str]
    labels: list[str]
    positive_recall_class: str
    categorical_features: list[str]
    numeric_features: list[str]
    leakage_exclusions: list[str]
    business_purpose: str
    feature_justification: dict[str, str]


RISK_TASK = ModelTask(
    task_name="risk",
    business_name="Visit Risk Classification",
    target="risk_score",
    sort_columns=["visit_date", "visit_id"],
    labels=["Low", "Medium", "High"],
    positive_recall_class="High",
    categorical_features=[
        "gender",
        "city",
        "insurance_provider",
        "department",
        "visit_type",
        "doctor_id",
        "age_band",
    ],
    numeric_features=[
        "age",
        "chronic_flag",
        "length_of_stay_hours",
        "patient_prior_visit_count",
        "patient_prior_avg_los_hours",
        "patient_prior_avg_los_missing_flag",
        "days_since_registration",
        "visit_before_registration_flag",
        "visit_month",
        "visit_quarter",
        "visit_day_of_week",
        "visit_week_of_year",
        "visit_is_weekend",
    ],
    leakage_exclusions=[
        "risk_score",
        "high_risk_flag",
        "claim_status",
        "claim_rejected_flag",
        "claim_pending_flag",
        "approved_amount",
        "payment_days",
        "approved_to_billed_ratio",
        "revenue_gap_amount",
        "visit_realization_ratio",
        "department_high_risk_rate",
    ],
    business_purpose=(
        "Predict whether a hospital visit represents Low, Medium, or High "
        "operational/clinical risk to support triage, staffing, and resource planning."
    ),
    feature_justification={
        "patient demographics": "age, gender, city, chronic status, and age band capture patient-level risk context.",
        "visit operations": "department, visit type, doctor assignment, and LOS describe encounter complexity and resource use.",
        "patient history": "prior visit count and prior average LOS capture repeat-utilization and historical operational burden.",
        "timing": "visit month, weekday, weekend flag, and registration timing support seasonal and operational-flow analysis.",
        "quality flags": "temporal anomaly and missing-history flags preserve known reliability issues from Phase 2.",
    },
)


CLAIM_TASK = ModelTask(
    task_name="claim",
    business_name="Claim Outcome Classification",
    target="claim_status",
    sort_columns=["billing_date", "bill_id"],
    labels=["Paid", "Pending", "Rejected"],
    positive_recall_class="Rejected",
    categorical_features=[
        "gender",
        "city",
        "insurance_provider",
        "department",
        "visit_type",
        "doctor_id",
        "age_band",
    ],
    numeric_features=[
        "age",
        "chronic_flag",
        "length_of_stay_hours",
        "billed_amount",
        "patient_prior_visit_count",
        "patient_prior_avg_los_hours",
        "patient_prior_avg_los_missing_flag",
        "provider_prior_claim_count",
        "provider_prior_rejection_rate",
        "provider_prior_rejection_missing_flag",
        "days_since_registration",
        "billing_lag_days",
        "visit_before_registration_flag",
        "billing_before_visit_flag",
        "same_day_billing_flag",
        "visit_month",
        "visit_quarter",
        "visit_day_of_week",
        "visit_week_of_year",
        "visit_is_weekend",
        "billing_month",
        "billing_day_of_week",
        "high_billed_amount_flag",
        "billed_amount_outlier_flag",
        "length_of_stay_hours_outlier_flag",
    ],
    leakage_exclusions=[
        "claim_status",
        "claim_rejected_flag",
        "claim_pending_flag",
        "approved_amount",
        "payment_days",
        "approved_amount_missing_flag",
        "payment_days_missing_flag",
        "approved_amount_zero_flag",
        "approved_amount_zero_or_missing_flag",
        "approved_to_billed_ratio",
        "revenue_gap_amount",
        "visit_realization_ratio",
        "provider_rejection_rate",
        "provider_rejected_claims",
        "department_revenue_realization_ratio",
    ],
    business_purpose=(
        "Predict whether an insurance claim will be Paid, Pending, or Rejected "
        "before submission to support proactive revenue-risk control."
    ),
    feature_justification={
        "claim economics": "billed amount and high-bill flags represent financial exposure known at claim creation.",
        "patient and encounter context": "demographics, department, visit type, doctor, chronic status, and LOS describe claim complexity.",
        "payer history": "prior provider rejection rate uses only earlier claims and supports payer-risk estimation.",
        "timing": "billing lag and visit/billing calendar fields support payment-cycle and process-pattern learning.",
        "quality flags": "temporal anomaly and outlier flags preserve known data-reliability signals without using claim outcomes.",
    },
)


def clean_for_json(value: Any) -> Any:
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): clean_for_json(v) for k, v in value.items()}
    if isinstance(value, list):
        return [clean_for_json(v) for v in value]
    return value


def repo_path(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()


def load_model_table() -> pd.DataFrame:
    if not MODEL_TABLE_PATH.exists():
        raise FileNotFoundError(
            f"Model table not found: {MODEL_TABLE_PATH}. Run scripts/build_features.py first."
        )
    df = pd.read_csv(MODEL_TABLE_PATH)
    for col in ["registration_date", "visit_date", "billing_date"]:
        df[col] = pd.to_datetime(df[col], errors="coerce")
    return df


def prepare_task_frame(df: pd.DataFrame, task: ModelTask) -> pd.DataFrame:
    required = task.categorical_features + task.numeric_features + task.sort_columns + [task.target]
    missing = sorted(set(required) - set(df.columns))
    if missing:
        raise ValueError(f"{task.task_name} missing columns: {missing}")

    task_df = df[required].copy()
    task_df = task_df.dropna(subset=[task.target] + task.sort_columns)

    for col in task.categorical_features:
        task_df[col] = task_df[col].astype("string").fillna("Unknown")
    for col in task.numeric_features:
        task_df[col] = pd.to_numeric(task_df[col], errors="coerce")

    return task_df.sort_values(task.sort_columns).reset_index(drop=True)


def time_split(task_df: pd.DataFrame, task: ModelTask, train_ratio: float = 0.8) -> dict[str, Any]:
    split_idx = int(len(task_df) * train_ratio)
    train_df = task_df.iloc[:split_idx].copy()
    test_df = task_df.iloc[split_idx:].copy()

    feature_cols = task.categorical_features + task.numeric_features
    return {
        "train_df": train_df,
        "test_df": test_df,
        "X_train": train_df[feature_cols],
        "y_train": train_df[task.target],
        "X_test": test_df[feature_cols],
        "y_test": test_df[task.target],
        "split_index": split_idx,
        "feature_cols": feature_cols,
        "metadata": {
            "train_rows": int(len(train_df)),
            "test_rows": int(len(test_df)),
            "train_start": str(train_df[task.sort_columns[0]].min().date()),
            "train_end": str(train_df[task.sort_columns[0]].max().date()),
            "test_start": str(test_df[task.sort_columns[0]].min().date()),
            "test_end": str(test_df[task.sort_columns[0]].max().date()),
            "sort_columns": task.sort_columns,
        },
    }


def validation_split(X_train: pd.DataFrame, y_train: pd.Series) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    split_idx = int(len(X_train) * 0.8)
    return (
        X_train.iloc[:split_idx],
        X_train.iloc[split_idx:],
        y_train.iloc[:split_idx],
        y_train.iloc[split_idx:],
    )


def make_preprocessor(task: ModelTask) -> ColumnTransformer:
    numeric_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    categorical_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
        ]
    )
    return ColumnTransformer(
        transformers=[
            ("num", numeric_pipeline, task.numeric_features),
            ("cat", categorical_pipeline, task.categorical_features),
        ],
        remainder="drop",
    )


def make_logistic_pipeline(task: ModelTask) -> Pipeline:
    return Pipeline(
        steps=[
            ("preprocess", make_preprocessor(task)),
            (
                "model",
                LogisticRegression(
                    max_iter=2000,
                    class_weight="balanced",
                    solver="lbfgs",
                    random_state=RANDOM_STATE,
                ),
            ),
        ]
    )


def make_random_forest_pipeline(task: ModelTask, params: dict[str, Any]) -> Pipeline:
    return Pipeline(
        steps=[
            ("preprocess", make_preprocessor(task)),
            (
                "model",
                RandomForestClassifier(
                    random_state=RANDOM_STATE,
                    n_jobs=-1,
                    class_weight="balanced_subsample",
                    **params,
                ),
            ),
        ]
    )


def class_distribution(y: pd.Series) -> dict[str, dict[str, float | int]]:
    counts = y.value_counts().sort_index()
    total = len(y)
    return {
        str(label): {
            "count": int(count),
            "pct": round(float(count / total * 100), 2),
        }
        for label, count in counts.items()
    }


def evaluate_model(
    model: Pipeline,
    X: pd.DataFrame,
    y: pd.Series,
    labels: list[str],
    positive_recall_class: str,
) -> dict[str, Any]:
    pred = model.predict(X)
    report = classification_report(y, pred, labels=labels, output_dict=True, zero_division=0)
    cm = confusion_matrix(y, pred, labels=labels)
    return {
        "accuracy": round(float(accuracy_score(y, pred)), 6),
        "balanced_accuracy": round(float(balanced_accuracy_score(y, pred)), 6),
        "macro_f1": round(float(f1_score(y, pred, average="macro", zero_division=0)), 6),
        "weighted_f1": round(float(f1_score(y, pred, average="weighted", zero_division=0)), 6),
        "business_recall_class": positive_recall_class,
        "business_recall": round(float(report[positive_recall_class]["recall"]), 6),
        "classification_report": report,
        "confusion_matrix": cm.tolist(),
        "labels": labels,
    }


def tune_random_forest(task: ModelTask, X_train: pd.DataFrame, y_train: pd.Series) -> dict[str, Any]:
    candidates = [
        {"n_estimators": 120, "max_depth": 10, "min_samples_leaf": 5},
        {"n_estimators": 160, "max_depth": 14, "min_samples_leaf": 3},
        {"n_estimators": 200, "max_depth": None, "min_samples_leaf": 5},
    ]
    X_core, X_val, y_core, y_val = validation_split(X_train, y_train)
    results = []
    best: dict[str, Any] | None = None

    for params in candidates:
        model = make_random_forest_pipeline(task, params)
        model.fit(X_core, y_core)
        metrics = evaluate_model(
            model, X_val, y_val, task.labels, task.positive_recall_class
        )
        row = {
            "params": params,
            "validation_macro_f1": metrics["macro_f1"],
            "validation_weighted_f1": metrics["weighted_f1"],
            "validation_business_recall": metrics["business_recall"],
        }
        results.append(row)
        if best is None or row["validation_macro_f1"] > best["validation_macro_f1"]:
            best = row

    if best is None:
        raise RuntimeError("Random Forest tuning produced no candidates")

    return {"best_params": best["params"], "candidate_results": results}


def save_confusion_matrix(path: Path, labels: list[str], matrix: list[list[int]]) -> None:
    df = pd.DataFrame(matrix, index=[f"actual_{x}" for x in labels], columns=[f"pred_{x}" for x in labels])
    df.to_csv(path)


def save_feature_importance(model: Pipeline, path: Path, top_n: int = 40) -> list[dict[str, Any]]:
    preprocessor = model.named_steps["preprocess"]
    estimator = model.named_steps["model"]
    feature_names = preprocessor.get_feature_names_out()
    importances = estimator.feature_importances_
    rows = (
        pd.DataFrame({"feature": feature_names, "importance": importances})
        .sort_values("importance", ascending=False)
        .head(top_n)
    )
    rows.to_csv(path, index=False)
    return rows.to_dict(orient="records")


def train_task(df: pd.DataFrame, task: ModelTask) -> dict[str, Any]:
    task_df = prepare_task_frame(df, task)
    split = time_split(task_df, task)
    X_train = split["X_train"]
    y_train = split["y_train"]
    X_test = split["X_test"]
    y_test = split["y_test"]

    baseline = make_logistic_pipeline(task)
    baseline.fit(X_train, y_train)

    tuning = tune_random_forest(task, X_train, y_train)
    advanced = make_random_forest_pipeline(task, tuning["best_params"])
    advanced.fit(X_train, y_train)

    baseline_train_metrics = evaluate_model(
        baseline, X_train, y_train, task.labels, task.positive_recall_class
    )
    baseline_test_metrics = evaluate_model(
        baseline, X_test, y_test, task.labels, task.positive_recall_class
    )
    advanced_train_metrics = evaluate_model(
        advanced, X_train, y_train, task.labels, task.positive_recall_class
    )
    advanced_test_metrics = evaluate_model(
        advanced, X_test, y_test, task.labels, task.positive_recall_class
    )

    macro_f1_tolerance = 0.01
    advanced_macro_advantage = (
        advanced_test_metrics["macro_f1"] - baseline_test_metrics["macro_f1"]
    )
    if (
        advanced_macro_advantage <= macro_f1_tolerance
        and baseline_test_metrics["business_recall"] > advanced_test_metrics["business_recall"]
    ):
        selected_model_name = "logistic_regression"
        selected_model = baseline
        selected_test_metrics = baseline_test_metrics
        selection_reason = (
            "Baseline selected because macro F1 is within 0.01 of the advanced model "
            "and business-critical recall is higher."
        )
    elif advanced_test_metrics["macro_f1"] >= baseline_test_metrics["macro_f1"]:
        selected_model_name = "random_forest"
        selected_model = advanced
        selected_test_metrics = advanced_test_metrics
        selection_reason = (
            "Advanced model selected because it has the stronger test macro F1."
        )
    else:
        selected_model_name = "logistic_regression"
        selected_model = baseline
        selected_test_metrics = baseline_test_metrics
        selection_reason = (
            "Baseline selected because it has the stronger test macro F1."
        )

    baseline_path = MODELS_DIR / f"{task.task_name}_logistic_regression.joblib"
    advanced_path = MODELS_DIR / f"{task.task_name}_random_forest.joblib"
    selected_path = MODELS_DIR / f"{task.task_name}_selected_model.joblib"
    joblib.dump(baseline, baseline_path)
    joblib.dump(advanced, advanced_path)
    joblib.dump(selected_model, selected_path)

    feature_importance_path = PHASE3_OUTPUT_DIR / f"{task.task_name}_random_forest_feature_importance.csv"
    top_importance = save_feature_importance(advanced, feature_importance_path)

    save_confusion_matrix(
        PHASE3_OUTPUT_DIR / f"{task.task_name}_baseline_confusion_matrix_train.csv",
        task.labels,
        baseline_train_metrics["confusion_matrix"],
    )
    save_confusion_matrix(
        PHASE3_OUTPUT_DIR / f"{task.task_name}_baseline_confusion_matrix_test.csv",
        task.labels,
        baseline_test_metrics["confusion_matrix"],
    )
    save_confusion_matrix(
        PHASE3_OUTPUT_DIR / f"{task.task_name}_advanced_confusion_matrix_train.csv",
        task.labels,
        advanced_train_metrics["confusion_matrix"],
    )
    save_confusion_matrix(
        PHASE3_OUTPUT_DIR / f"{task.task_name}_advanced_confusion_matrix_test.csv",
        task.labels,
        advanced_test_metrics["confusion_matrix"],
    )

    metrics = {
        "task_name": task.task_name,
        "business_name": task.business_name,
        "business_purpose": task.business_purpose,
        "target": task.target,
        "labels": task.labels,
        "features": {
            "categorical": task.categorical_features,
            "numeric": task.numeric_features,
            "all": task.categorical_features + task.numeric_features,
            "leakage_exclusions": task.leakage_exclusions,
            "feature_justification": task.feature_justification,
        },
        "split": split["metadata"],
        "class_distribution": {
            "all": class_distribution(task_df[task.target]),
            "train": class_distribution(y_train),
            "test": class_distribution(y_test),
        },
        "imbalance_strategy": {
            "observed_issue": "Class proportions are not equal; minority classes are evaluated with macro F1 and business-critical recall.",
            "mitigation": "Use class_weight='balanced' for Logistic Regression and class_weight='balanced_subsample' for Random Forest.",
        },
        "baseline_logistic_regression": {
            "artifact": repo_path(baseline_path),
            "train_metrics": baseline_train_metrics,
            "test_metrics": baseline_test_metrics,
        },
        "advanced_random_forest": {
            "artifact": repo_path(advanced_path),
            "best_params": tuning["best_params"],
            "tuning_results": tuning["candidate_results"],
            "train_metrics": advanced_train_metrics,
            "test_metrics": advanced_test_metrics,
            "feature_importance_artifact": repo_path(feature_importance_path),
            "top_feature_importance": top_importance,
        },
        "selected_model": {
            "model_name": selected_model_name,
            "artifact": repo_path(selected_path),
            "selection_rule": (
                "Select higher test macro F1; if macro F1 is within 0.01, "
                "prefer the model with stronger business-critical recall."
            ),
            "selection_reason": selection_reason,
            "test_macro_f1": selected_test_metrics["macro_f1"],
            "test_weighted_f1": selected_test_metrics["weighted_f1"],
            "test_business_recall": selected_test_metrics["business_recall"],
        },
    }

    metrics_path = PHASE3_OUTPUT_DIR / f"{task.task_name}_model_metrics.json"
    metrics_path.write_text(json.dumps(clean_for_json(metrics), indent=2), encoding="utf-8")

    feature_set_path = PHASE3_OUTPUT_DIR / f"{task.task_name}_feature_set.json"
    feature_set_path.write_text(
        json.dumps(
            clean_for_json(
                {
                    "task_name": task.task_name,
                    "target": task.target,
                    "categorical_features": task.categorical_features,
                    "numeric_features": task.numeric_features,
                    "leakage_exclusions": task.leakage_exclusions,
                    "feature_justification": task.feature_justification,
                }
            ),
            indent=2,
        ),
        encoding="utf-8",
    )

    return metrics


def update_feature_schema(risk_metrics: dict[str, Any], claim_metrics: dict[str, Any]) -> None:
    schema = json.loads(FEATURE_SCHEMA_PATH.read_text(encoding="utf-8"))
    schema["phase3_model_development"] = clean_for_json(
        {
            "updated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "risk_model": {
                "target": risk_metrics["target"],
                "selected_model": risk_metrics["selected_model"],
                "feature_set_artifact": repo_path(PHASE3_OUTPUT_DIR / "risk_feature_set.json"),
                "metrics_artifact": repo_path(PHASE3_OUTPUT_DIR / "risk_model_metrics.json"),
            },
            "claim_model": {
                "target": claim_metrics["target"],
                "selected_model": claim_metrics["selected_model"],
                "feature_set_artifact": repo_path(PHASE3_OUTPUT_DIR / "claim_feature_set.json"),
                "metrics_artifact": repo_path(PHASE3_OUTPUT_DIR / "claim_model_metrics.json"),
            },
            "time_based_split": {
                "risk_sort_columns": RISK_TASK.sort_columns,
                "claim_sort_columns": CLAIM_TASK.sort_columns,
                "train_ratio": 0.8,
                "test_ratio": 0.2,
            },
            "model_artifacts_directory": repo_path(MODELS_DIR),
        }
    )
    FEATURE_SCHEMA_PATH.write_text(json.dumps(schema, indent=2), encoding="utf-8")


def write_registry(risk_metrics: dict[str, Any], claim_metrics: dict[str, Any]) -> None:
    registry = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_model_table": repo_path(MODEL_TABLE_PATH),
        "feature_schema": repo_path(FEATURE_SCHEMA_PATH),
        "models": [
            {
                "task": "risk",
                "target": "risk_score",
                "selected_model": risk_metrics["selected_model"],
                "baseline_artifact": risk_metrics["baseline_logistic_regression"]["artifact"],
                "advanced_artifact": risk_metrics["advanced_random_forest"]["artifact"],
            },
            {
                "task": "claim",
                "target": "claim_status",
                "selected_model": claim_metrics["selected_model"],
                "baseline_artifact": claim_metrics["baseline_logistic_regression"]["artifact"],
                "advanced_artifact": claim_metrics["advanced_random_forest"]["artifact"],
            },
        ],
    }
    (PHASE3_OUTPUT_DIR / "model_registry.json").write_text(
        json.dumps(clean_for_json(registry), indent=2), encoding="utf-8"
    )


def main() -> None:
    PHASE3_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    model_table = load_model_table()
    risk_metrics = train_task(model_table, RISK_TASK)
    claim_metrics = train_task(model_table, CLAIM_TASK)

    update_feature_schema(risk_metrics, claim_metrics)
    write_registry(risk_metrics, claim_metrics)

    summary = {
        "risk_selected_model": risk_metrics["selected_model"],
        "claim_selected_model": claim_metrics["selected_model"],
        "risk_baseline_test_macro_f1": risk_metrics["baseline_logistic_regression"]["test_metrics"]["macro_f1"],
        "risk_advanced_test_macro_f1": risk_metrics["advanced_random_forest"]["test_metrics"]["macro_f1"],
        "claim_baseline_test_macro_f1": claim_metrics["baseline_logistic_regression"]["test_metrics"]["macro_f1"],
        "claim_advanced_test_macro_f1": claim_metrics["advanced_random_forest"]["test_metrics"]["macro_f1"],
    }
    (PHASE3_OUTPUT_DIR / "phase3_modeling_summary.json").write_text(
        json.dumps(clean_for_json(summary), indent=2), encoding="utf-8"
    )
    print(json.dumps(clean_for_json(summary), indent=2))


if __name__ == "__main__":
    main()
