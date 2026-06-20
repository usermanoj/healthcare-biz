"""Evaluate Phase 3 models for Phase 4 reporting and governance.

Outputs:
    data_outputs/phase4/
        risk_* evaluation files
        claim_* evaluation files
        fairness summaries
        explainability summaries
        consolidated model-card JSON

The evaluation is intentionally performed from saved model artifacts so Phase 4
validates the deployable objects, not just in-memory training results.
"""

from __future__ import annotations

import json
import sys
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
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)


MODEL_TABLE_PATH = PROJECT_ROOT / "data_outputs" / "model_table.csv"
PHASE3_DIR = PROJECT_ROOT / "data_outputs" / "phase3"
PHASE4_DIR = PROJECT_ROOT / "data_outputs" / "phase4"
FEATURE_SCHEMA_PATH = PROJECT_ROOT / "data_outputs" / "feature_schema.json"


TASKS = {
    "risk": {
        "target": "risk_score",
        "metrics_file": "risk_model_metrics.json",
        "feature_set_file": "risk_feature_set.json",
        "labels": ["Low", "Medium", "High"],
        "business_class": "High",
        "business_metric_name": "high_risk_recall",
        "sort_columns": ["visit_date", "visit_id"],
        "model_purpose": "Prioritize visits for operational and clinical risk triage.",
        "stakeholders": ["hospital administrators", "clinical operations teams", "doctors"],
    },
    "claim": {
        "target": "claim_status",
        "metrics_file": "claim_model_metrics.json",
        "feature_set_file": "claim_feature_set.json",
        "labels": ["Paid", "Pending", "Rejected"],
        "business_class": "Rejected",
        "business_metric_name": "rejected_claim_recall",
        "sort_columns": ["billing_date", "bill_id"],
        "model_purpose": "Identify claim outcome risk before submission to reduce revenue leakage.",
        "stakeholders": ["finance teams", "revenue-cycle teams", "hospital administrators"],
    },
}


SEGMENT_COLUMNS = ["gender", "city", "insurance_provider"]


def clean_for_json(value: Any) -> Any:
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, dict):
        return {str(k): clean_for_json(v) for k, v in value.items()}
    if isinstance(value, list):
        return [clean_for_json(v) for v in value]
    return value


def repo_path(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_data() -> pd.DataFrame:
    df = pd.read_csv(MODEL_TABLE_PATH)
    for col in ["registration_date", "visit_date", "billing_date"]:
        df[col] = pd.to_datetime(df[col], errors="coerce")
    return df


def sorted_task_frame(df: pd.DataFrame, task_key: str, feature_set: dict[str, Any]) -> pd.DataFrame:
    task = TASKS[task_key]
    features = feature_set["categorical_features"] + feature_set["numeric_features"]
    columns = sorted(set(features + [task["target"], *task["sort_columns"], *SEGMENT_COLUMNS]))
    task_df = df[columns].dropna(subset=[task["target"], *task["sort_columns"]]).copy()
    for col in feature_set["categorical_features"]:
        task_df[col] = task_df[col].astype("string").fillna("Unknown")
    for col in feature_set["numeric_features"]:
        task_df[col] = pd.to_numeric(task_df[col], errors="coerce")
    return task_df.sort_values(task["sort_columns"]).reset_index(drop=True)


def split_frame(task_df: pd.DataFrame, task_key: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    split_idx = int(len(task_df) * 0.8)
    return task_df.iloc[:split_idx].copy(), task_df.iloc[split_idx:].copy()


def feature_matrix(frame: pd.DataFrame, feature_set: dict[str, Any]) -> pd.DataFrame:
    return frame[feature_set["categorical_features"] + feature_set["numeric_features"]]


def classification_rows(y_true: pd.Series, y_pred: np.ndarray, labels: list[str]) -> pd.DataFrame:
    report = classification_report(y_true, y_pred, labels=labels, output_dict=True, zero_division=0)
    rows = []
    for label in labels:
        rows.append(
            {
                "class_label": label,
                "precision": round(float(report[label]["precision"]), 6),
                "recall": round(float(report[label]["recall"]), 6),
                "f1_score": round(float(report[label]["f1-score"]), 6),
                "support": int(report[label]["support"]),
            }
        )
    rows.append(
        {
            "class_label": "macro_avg",
            "precision": round(float(report["macro avg"]["precision"]), 6),
            "recall": round(float(report["macro avg"]["recall"]), 6),
            "f1_score": round(float(report["macro avg"]["f1-score"]), 6),
            "support": int(report["macro avg"]["support"]),
        }
    )
    rows.append(
        {
            "class_label": "weighted_avg",
            "precision": round(float(report["weighted avg"]["precision"]), 6),
            "recall": round(float(report["weighted avg"]["recall"]), 6),
            "f1_score": round(float(report["weighted avg"]["f1-score"]), 6),
            "support": int(report["weighted avg"]["support"]),
        }
    )
    return pd.DataFrame(rows)


def aggregate_metrics(y_true: pd.Series, y_pred: np.ndarray, labels: list[str], business_class: str) -> dict[str, Any]:
    return {
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 6),
        "balanced_accuracy": round(float(balanced_accuracy_score(y_true, y_pred)), 6),
        "macro_precision": round(float(precision_score(y_true, y_pred, labels=labels, average="macro", zero_division=0)), 6),
        "macro_recall": round(float(recall_score(y_true, y_pred, labels=labels, average="macro", zero_division=0)), 6),
        "macro_f1": round(float(f1_score(y_true, y_pred, labels=labels, average="macro", zero_division=0)), 6),
        "weighted_f1": round(float(f1_score(y_true, y_pred, labels=labels, average="weighted", zero_division=0)), 6),
        "business_class": business_class,
        "business_recall": round(
            float(recall_score(y_true, y_pred, labels=[business_class], average="macro", zero_division=0)),
            6,
        ),
    }


def save_confusion_matrix(path: Path, y_true: pd.Series, y_pred: np.ndarray, labels: list[str]) -> None:
    matrix = confusion_matrix(y_true, y_pred, labels=labels)
    matrix_df = pd.DataFrame(
        matrix,
        index=[f"actual_{label}" for label in labels],
        columns=[f"pred_{label}" for label in labels],
    )
    matrix_df.to_csv(path)


def fairness_by_segment(
    frame: pd.DataFrame,
    y_pred: np.ndarray,
    task_key: str,
) -> pd.DataFrame:
    task = TASKS[task_key]
    eval_df = frame[[task["target"], *SEGMENT_COLUMNS]].copy()
    eval_df["prediction"] = y_pred
    eval_df["is_business_class"] = eval_df[task["target"]].eq(task["business_class"])
    eval_df["business_class_correct"] = (
        eval_df[task["target"]].eq(task["business_class"])
        & eval_df["prediction"].eq(task["business_class"])
    )
    eval_df["correct"] = eval_df[task["target"]].eq(eval_df["prediction"])

    rows = []
    for segment_col in SEGMENT_COLUMNS:
        for segment_value, group in eval_df.groupby(segment_col, dropna=False):
            business_support = int(group["is_business_class"].sum())
            business_recall = (
                float(group["business_class_correct"].sum() / business_support)
                if business_support > 0
                else np.nan
            )
            rows.append(
                {
                    "segment_column": segment_col,
                    "segment_value": segment_value,
                    "row_count": int(len(group)),
                    "accuracy": round(float(group["correct"].mean()), 6),
                    "business_class": task["business_class"],
                    "business_class_support": business_support,
                    "business_recall": round(business_recall, 6) if pd.notna(business_recall) else None,
                    "prediction_business_class_rate": round(
                        float(group["prediction"].eq(task["business_class"]).mean()), 6
                    ),
                    "actual_business_class_rate": round(
                        float(group[task["target"]].eq(task["business_class"]).mean()), 6
                    ),
                }
            )
    fairness = pd.DataFrame(rows)
    return fairness.sort_values(["segment_column", "business_recall", "row_count"], ascending=[True, True, False])


def fairness_gap_summary(fairness: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for segment_col, group in fairness.groupby("segment_column"):
        valid = group.dropna(subset=["business_recall"])
        if valid.empty:
            continue
        min_row = valid.loc[valid["business_recall"].idxmin()]
        max_row = valid.loc[valid["business_recall"].idxmax()]
        rows.append(
            {
                "segment_column": segment_col,
                "min_recall_segment": min_row["segment_value"],
                "min_business_recall": min_row["business_recall"],
                "max_recall_segment": max_row["segment_value"],
                "max_business_recall": max_row["business_recall"],
                "business_recall_gap": round(float(max_row["business_recall"] - min_row["business_recall"]), 6),
                "segments_evaluated": int(valid.shape[0]),
            }
        )
    return pd.DataFrame(rows)


def selected_model_feature_summary(task_key: str, metrics: dict[str, Any]) -> pd.DataFrame:
    selected_name = metrics["selected_model"]["model_name"]
    if selected_name == "random_forest":
        source = pd.read_csv(PHASE3_DIR / f"{task_key}_random_forest_feature_importance.csv")
        source["explainability_type"] = "random_forest_impurity_importance"
        return source.head(20)

    # Logistic Regression selected for risk: summarize strongest absolute
    # coefficients across one-vs-rest class coefficients.
    model = joblib.load(PROJECT_ROOT / metrics["selected_model"]["artifact"])
    preprocessor = model.named_steps["preprocess"]
    estimator = model.named_steps["model"]
    feature_names = preprocessor.get_feature_names_out()
    coef = estimator.coef_
    rows = []
    for class_label, class_coef in zip(estimator.classes_, coef):
        top_indices = np.argsort(np.abs(class_coef))[::-1][:15]
        for idx in top_indices:
            rows.append(
                {
                    "class_label": class_label,
                    "feature": feature_names[idx],
                    "coefficient": round(float(class_coef[idx]), 8),
                    "abs_coefficient": round(float(abs(class_coef[idx])), 8),
                    "explainability_type": "logistic_regression_coefficient",
                }
            )
    return pd.DataFrame(rows).sort_values("abs_coefficient", ascending=False).head(30)


def evaluate_task(df: pd.DataFrame, task_key: str) -> dict[str, Any]:
    task = TASKS[task_key]
    metrics = load_json(PHASE3_DIR / task["metrics_file"])
    feature_set = load_json(PHASE3_DIR / task["feature_set_file"])
    task_df = sorted_task_frame(df, task_key, feature_set)
    train_df, test_df = split_frame(task_df, task_key)
    model = joblib.load(PROJECT_ROOT / metrics["selected_model"]["artifact"])

    result = {
        "task_name": task_key,
        "target": task["target"],
        "selected_model": metrics["selected_model"],
        "model_purpose": task["model_purpose"],
        "stakeholders": task["stakeholders"],
        "labels": task["labels"],
    }

    for split_name, split_df in [("train", train_df), ("test", test_df)]:
        X = feature_matrix(split_df, feature_set)
        y = split_df[task["target"]]
        pred = model.predict(X)

        split_metrics = aggregate_metrics(y, pred, task["labels"], task["business_class"])
        result[f"{split_name}_metrics"] = split_metrics

        classification_rows(y, pred, task["labels"]).to_csv(
            PHASE4_DIR / f"{task_key}_{split_name}_classification_report.csv",
            index=False,
        )
        save_confusion_matrix(
            PHASE4_DIR / f"{task_key}_{split_name}_confusion_matrix.csv",
            y,
            pred,
            task["labels"],
        )

        if split_name == "test":
            fairness = fairness_by_segment(split_df, pred, task_key)
            fairness.to_csv(PHASE4_DIR / f"{task_key}_fairness_by_segment.csv", index=False)
            fairness_gaps = fairness_gap_summary(fairness)
            fairness_gaps.to_csv(PHASE4_DIR / f"{task_key}_fairness_gap_summary.csv", index=False)
            result["fairness_gap_summary"] = fairness_gaps.to_dict(orient="records")

    explanation = selected_model_feature_summary(task_key, metrics)
    explanation.to_csv(PHASE4_DIR / f"{task_key}_selected_model_explainability.csv", index=False)
    result["top_explainability_items"] = explanation.head(10).to_dict(orient="records")

    (PHASE4_DIR / f"{task_key}_evaluation_summary.json").write_text(
        json.dumps(clean_for_json(result), indent=2),
        encoding="utf-8",
    )
    return result


def write_model_card(risk: dict[str, Any], claim: dict[str, Any]) -> None:
    card = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "project": "Hospital Operations & Revenue Risk Intelligence Platform",
        "model_family": "Phase 3 classification systems evaluated in Phase 4",
        "source_data": repo_path(MODEL_TABLE_PATH),
        "feature_schema": repo_path(FEATURE_SCHEMA_PATH),
        "models": {
            "risk": risk,
            "claim": claim,
        },
        "intended_use": [
            "Operational triage and staffing support for hospital visits.",
            "Revenue-cycle review and pre-submission claim risk prioritization.",
        ],
        "not_intended_use": [
            "Do not use as a standalone clinical diagnosis system.",
            "Do not auto-deny care or insurance claims based only on model output.",
            "Do not use without monitoring for drift, fairness gaps, and data-quality anomalies.",
        ],
        "major_limitations": [
            "Dataset is synthetic and has weak visible signal between predictors and targets.",
            "Temporal anomalies were identified in Phase 1 and preserved as flags.",
            "Model performance is modest; predictions should support review workflows rather than automate final decisions.",
            "Fairness analysis is limited to available demographic/location/provider fields.",
        ],
        "governance_recommendations": [
            "Use human review for High Risk and Rejected prediction workflows.",
            "Monitor business-critical recall for High Risk visits and Rejected claims.",
            "Track segment performance by gender, city, and insurance provider.",
            "Retrain only after validating source-data quality and temporal consistency.",
        ],
    }
    (PHASE4_DIR / "model_card.json").write_text(
        json.dumps(clean_for_json(card), indent=2),
        encoding="utf-8",
    )


def update_feature_schema(risk: dict[str, Any], claim: dict[str, Any]) -> None:
    schema = load_json(FEATURE_SCHEMA_PATH)
    schema["phase4_evaluation_explainability"] = {
        "updated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "evaluation_output_dir": repo_path(PHASE4_DIR),
        "risk": {
            "selected_model": risk["selected_model"],
            "train_metrics": risk["train_metrics"],
            "test_metrics": risk["test_metrics"],
            "fairness_gap_summary_artifact": repo_path(PHASE4_DIR / "risk_fairness_gap_summary.csv"),
            "explainability_artifact": repo_path(PHASE4_DIR / "risk_selected_model_explainability.csv"),
        },
        "claim": {
            "selected_model": claim["selected_model"],
            "train_metrics": claim["train_metrics"],
            "test_metrics": claim["test_metrics"],
            "fairness_gap_summary_artifact": repo_path(PHASE4_DIR / "claim_fairness_gap_summary.csv"),
            "explainability_artifact": repo_path(PHASE4_DIR / "claim_selected_model_explainability.csv"),
        },
        "model_card_artifact": repo_path(PHASE4_DIR / "model_card.json"),
    }
    FEATURE_SCHEMA_PATH.write_text(json.dumps(clean_for_json(schema), indent=2), encoding="utf-8")


def main() -> None:
    PHASE4_DIR.mkdir(parents=True, exist_ok=True)
    df = load_data()
    risk = evaluate_task(df, "risk")
    claim = evaluate_task(df, "claim")
    write_model_card(risk, claim)
    update_feature_schema(risk, claim)

    summary = {
        "risk_selected_model": risk["selected_model"]["model_name"],
        "risk_test_macro_f1": risk["test_metrics"]["macro_f1"],
        "risk_test_business_recall": risk["test_metrics"]["business_recall"],
        "claim_selected_model": claim["selected_model"]["model_name"],
        "claim_test_macro_f1": claim["test_metrics"]["macro_f1"],
        "claim_test_business_recall": claim["test_metrics"]["business_recall"],
    }
    (PHASE4_DIR / "phase4_evaluation_summary.json").write_text(
        json.dumps(clean_for_json(summary), indent=2),
        encoding="utf-8",
    )
    print(json.dumps(clean_for_json(summary), indent=2))


if __name__ == "__main__":
    main()
