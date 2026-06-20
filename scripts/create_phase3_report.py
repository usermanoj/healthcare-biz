"""Create Phase 3 model development report from metrics outputs."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PHASE3_DIR = PROJECT_ROOT / "data_outputs" / "phase3"
REPORT_PATH = PROJECT_ROOT / "docs" / "Phase3_Model_Development_Report.md"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def markdown_table(rows: list[dict]) -> str:
    df = pd.DataFrame(rows).fillna("")
    headers = [str(col) for col in df.columns]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for _, row in df.iterrows():
        lines.append("| " + " | ".join(str(row[col]) for col in df.columns) + " |")
    return "\n".join(lines)


def model_metric_rows(metrics: dict) -> list[dict]:
    baseline = metrics["baseline_logistic_regression"]["test_metrics"]
    advanced = metrics["advanced_random_forest"]["test_metrics"]
    return [
        {
            "model": "Logistic Regression baseline",
            "accuracy": baseline["accuracy"],
            "balanced_accuracy": baseline["balanced_accuracy"],
            "macro_f1": baseline["macro_f1"],
            "weighted_f1": baseline["weighted_f1"],
            f"{baseline['business_recall_class']}_recall": baseline["business_recall"],
        },
        {
            "model": "Random Forest advanced",
            "accuracy": advanced["accuracy"],
            "balanced_accuracy": advanced["balanced_accuracy"],
            "macro_f1": advanced["macro_f1"],
            "weighted_f1": advanced["weighted_f1"],
            f"{advanced['business_recall_class']}_recall": advanced["business_recall"],
        },
    ]


def class_rows(metrics: dict) -> list[dict]:
    rows = []
    for split, dist in metrics["class_distribution"].items():
        for label, values in dist.items():
            rows.append(
                {
                    "split": split,
                    "class": label,
                    "count": values["count"],
                    "pct": values["pct"],
                }
            )
    return rows


def feature_rows(metrics: dict) -> list[dict]:
    rows = []
    for group, reason in metrics["features"]["feature_justification"].items():
        rows.append({"feature_group": group, "business_reason": reason})
    return rows


def artifact_rows(risk: dict, claim: dict) -> list[dict]:
    return [
        {
            "artifact": "Risk baseline model",
            "path": risk["baseline_logistic_regression"]["artifact"],
        },
        {
            "artifact": "Risk advanced model",
            "path": risk["advanced_random_forest"]["artifact"],
        },
        {
            "artifact": "Risk selected model",
            "path": risk["selected_model"]["artifact"],
        },
        {
            "artifact": "Claim baseline model",
            "path": claim["baseline_logistic_regression"]["artifact"],
        },
        {
            "artifact": "Claim advanced model",
            "path": claim["advanced_random_forest"]["artifact"],
        },
        {
            "artifact": "Claim selected model",
            "path": claim["selected_model"]["artifact"],
        },
    ]


def main() -> None:
    risk = read_json(PHASE3_DIR / "risk_model_metrics.json")
    claim = read_json(PHASE3_DIR / "claim_model_metrics.json")

    report = f"""# Phase 3 - Model Development Report

## Purpose

Phase 3 develops two classification systems for the Healthcare Business
Capstone:

1. **Visit Risk Classification**: predict `risk_score` as Low, Medium, or High.
2. **Claim Outcome Classification**: predict `claim_status` as Paid, Pending, or
   Rejected before submission.

Both systems use leakage-aware feature selection, an earliest-80% / latest-20%
time-based train/test split, a Logistic Regression baseline, and a tuned Random
Forest advanced model.

## Deliverables

| Deliverable | Location |
|---|---|
| Risk model notebook | `notebooks/02_risk_model.ipynb` |
| Claim model notebook | `notebooks/03_claim_model.ipynb` |
| Training script | `scripts/train_models.py` |
| Model artifacts | `models/*.joblib` |
| Risk metrics | `data_outputs/phase3/risk_model_metrics.json` |
| Claim metrics | `data_outputs/phase3/claim_model_metrics.json` |
| Feature schema | `data_outputs/feature_schema.json` |

## Model A - Visit Risk Classification

**Business purpose:** {risk["business_purpose"]}

**Target:** `{risk["target"]}`

### Feature Set Justification

{markdown_table(feature_rows(risk))}

### Time-Based Split

| Split Field | Value |
|---|---|
| Sort columns | {", ".join(risk["split"]["sort_columns"])} |
| Train rows | {risk["split"]["train_rows"]} |
| Test rows | {risk["split"]["test_rows"]} |
| Train date range | {risk["split"]["train_start"]} to {risk["split"]["train_end"]} |
| Test date range | {risk["split"]["test_start"]} to {risk["split"]["test_end"]} |

### Class Distribution

{markdown_table(class_rows(risk))}

### Test Metrics

{markdown_table(model_metric_rows(risk))}

### Selected Risk Model

| Field | Value |
|---|---|
| Selected model | {risk["selected_model"]["model_name"]} |
| Selection rule | {risk["selected_model"]["selection_rule"]} |
| Selection reason | {risk["selected_model"]["selection_reason"]} |
| Artifact | `{risk["selected_model"]["artifact"]}` |
| Test macro F1 | {risk["selected_model"]["test_macro_f1"]} |
| Test weighted F1 | {risk["selected_model"]["test_weighted_f1"]} |
| High-risk recall | {risk["selected_model"]["test_business_recall"]} |

## Model B - Claim Outcome Classification

**Business purpose:** {claim["business_purpose"]}

**Target:** `{claim["target"]}`

### Feature Set Justification

{markdown_table(feature_rows(claim))}

### Time-Based Split

| Split Field | Value |
|---|---|
| Sort columns | {", ".join(claim["split"]["sort_columns"])} |
| Train rows | {claim["split"]["train_rows"]} |
| Test rows | {claim["split"]["test_rows"]} |
| Train date range | {claim["split"]["train_start"]} to {claim["split"]["train_end"]} |
| Test date range | {claim["split"]["test_start"]} to {claim["split"]["test_end"]} |

### Class Distribution

{markdown_table(class_rows(claim))}

### Test Metrics

{markdown_table(model_metric_rows(claim))}

### Selected Claim Model

| Field | Value |
|---|---|
| Selected model | {claim["selected_model"]["model_name"]} |
| Selection rule | {claim["selected_model"]["selection_rule"]} |
| Selection reason | {claim["selected_model"]["selection_reason"]} |
| Artifact | `{claim["selected_model"]["artifact"]}` |
| Test macro F1 | {claim["selected_model"]["test_macro_f1"]} |
| Test weighted F1 | {claim["selected_model"]["test_weighted_f1"]} |
| Rejected-claim recall | {claim["selected_model"]["test_business_recall"]} |

## Class Imbalance Strategy

The target classes are not evenly distributed. The modeling approach uses:

- `class_weight='balanced'` in Logistic Regression.
- `class_weight='balanced_subsample'` in Random Forest.
- macro F1 for model selection so minority-class performance matters.
- business-critical recall for High Risk visits and Rejected claims.

## Leakage Controls

Risk model exclusions include risk-target fields, claim outcome fields,
approved/payment fields, revenue-gap fields, and target-derived department
high-risk rates.

Claim model exclusions include claim-target fields, approved amount, payment
days, approval/realization ratios, revenue gap, full-history provider rejection
rate, and department realization ratio. The claim model uses
`provider_prior_rejection_rate`, which is time-aware and based on earlier
claims only.

## Saved Model Artifacts

{markdown_table(artifact_rows(risk, claim))}

## Recommendation for Phase 4

Phase 4 should emphasize evaluation, explainability, and business impact rather
than just raw accuracy. In particular:

- inspect confusion matrices for High Risk and Rejected classes,
- evaluate feature importance and stability,
- perform fairness slices by gender, city, and insurance provider,
- create a model card documenting weak/strong points, assumptions, and
  deployment limitations.
"""

    REPORT_PATH.write_text(report, encoding="utf-8")
    print(f"Wrote report: {REPORT_PATH}")


if __name__ == "__main__":
    main()
