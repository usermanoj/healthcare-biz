"""Create Phase 4 evaluation, explainability, and model-card reports."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PHASE4_DIR = PROJECT_ROOT / "data_outputs" / "phase4"
DOCS_DIR = PROJECT_ROOT / "docs"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def markdown_table(df: pd.DataFrame | list[dict]) -> str:
    if isinstance(df, list):
        df = pd.DataFrame(df)
    clean = df.fillna("")
    headers = [str(col) for col in clean.columns]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for _, row in clean.iterrows():
        lines.append("| " + " | ".join(str(row[col]) for col in clean.columns) + " |")
    return "\n".join(lines)


def metric_rows(summary: dict) -> list[dict]:
    return [
        {"split": "train", **summary["train_metrics"]},
        {"split": "test", **summary["test_metrics"]},
    ]


def create_model_report(task_key: str, title: str, business_class_label: str) -> None:
    summary = read_json(PHASE4_DIR / f"{task_key}_evaluation_summary.json")
    train_report = pd.read_csv(PHASE4_DIR / f"{task_key}_train_classification_report.csv")
    test_report = pd.read_csv(PHASE4_DIR / f"{task_key}_test_classification_report.csv")
    fairness = pd.read_csv(PHASE4_DIR / f"{task_key}_fairness_by_segment.csv")
    fairness_gap = pd.read_csv(PHASE4_DIR / f"{task_key}_fairness_gap_summary.csv")
    explainability = pd.read_csv(PHASE4_DIR / f"{task_key}_selected_model_explainability.csv")

    report = f"""# Phase 4 - {title} Evaluation Report

## Purpose

{summary["model_purpose"]}

## Selected Model

| Field | Value |
|---|---|
| Selected model | {summary["selected_model"]["model_name"]} |
| Selection rule | {summary["selected_model"]["selection_rule"]} |
| Selection reason | {summary["selected_model"].get("selection_reason", "")} |
| Artifact | `{summary["selected_model"]["artifact"]}` |

## Aggregate Metrics

{markdown_table(metric_rows(summary))}

Business-critical recall class: **{business_class_label}**

## Train Classification Report

{markdown_table(train_report)}

## Test Classification Report

{markdown_table(test_report)}

## Fairness and Segment Analysis

Segment-level performance was evaluated by gender, city, and insurance provider
on the test split.

### Fairness Gap Summary

{markdown_table(fairness_gap)}

### Segment Detail

{markdown_table(fairness)}

## Explainability Summary

The explainability method depends on the selected model:

- Logistic Regression: strongest absolute class coefficients.
- Random Forest: impurity-based feature importance.

{markdown_table(explainability.head(25))}

## Safety Interpretation

- Use the model to prioritize review, not to automate final clinical or finance
  decisions.
- Track business-critical recall over time because missing High Risk visits or
  Rejected claims has direct operational and financial impact.
- Monitor segment gaps; if gaps widen in production, retraining or workflow
  constraints should be reviewed before wider deployment.
"""

    (DOCS_DIR / f"Phase4_{task_key.title()}_Model_Evaluation_Report.md").write_text(
        report,
        encoding="utf-8",
    )


def create_explainability_report() -> None:
    risk_explain = pd.read_csv(PHASE4_DIR / "risk_selected_model_explainability.csv")
    claim_explain = pd.read_csv(PHASE4_DIR / "claim_selected_model_explainability.csv")

    report = f"""# Phase 4 - Explainability Summary

## Purpose

This summary explains the main drivers used by the selected Phase 3 models.
The goal is stakeholder trust: hospital teams should understand what kinds of
signals influence predictions before deployment.

## Risk Model Explainability

The selected risk model is Logistic Regression, so explanations use the
strongest absolute coefficients across risk classes.

{markdown_table(risk_explain.head(30))}

## Claim Model Explainability

The selected claim model is Random Forest, so explanations use impurity-based
feature importance.

{markdown_table(claim_explain.head(30))}

## Interpretation Notes

- Explainability is directional and model-specific; it does not prove clinical
  or financial causality.
- Operational fields, historical utilization, payer history, and temporal flags
  should be interpreted with the Phase 2 data-quality findings in mind.
- Because the dataset is synthetic and signal is modest, explainability should
  support audit and review rather than strong causal claims.
"""

    (DOCS_DIR / "Phase4_Explainability_Summary.md").write_text(report, encoding="utf-8")


def create_model_card_report() -> None:
    card = read_json(PHASE4_DIR / "model_card.json")
    risk = card["models"]["risk"]
    claim = card["models"]["claim"]

    report = f"""# Phase 4 - Consolidated Model Card

## Project

{card["project"]}

## Model Overview

| Model | Target | Selected Model | Test Macro F1 | Business Recall |
|---|---|---|---:|---:|
| Visit Risk Classification | risk_score | {risk["selected_model"]["model_name"]} | {risk["test_metrics"]["macro_f1"]} | {risk["test_metrics"]["business_recall"]} |
| Claim Outcome Classification | claim_status | {claim["selected_model"]["model_name"]} | {claim["test_metrics"]["macro_f1"]} | {claim["test_metrics"]["business_recall"]} |

## Intended Use

{chr(10).join(f"- {item}" for item in card["intended_use"])}

## Not Intended Use

{chr(10).join(f"- {item}" for item in card["not_intended_use"])}

## Stakeholders

Risk model stakeholders: {", ".join(risk["stakeholders"])}

Claim model stakeholders: {", ".join(claim["stakeholders"])}

## Major Limitations

{chr(10).join(f"- {item}" for item in card["major_limitations"])}

## Fairness and Safety

Fairness was evaluated on the test split by:

- gender
- city
- insurance provider

Segment gaps are documented in:

- `data_outputs/phase4/risk_fairness_gap_summary.csv`
- `data_outputs/phase4/claim_fairness_gap_summary.csv`

## Governance Recommendations

{chr(10).join(f"- {item}" for item in card["governance_recommendations"])}

## Imbalance Improvement Options

Recommended next steps for improving minority-class performance:

- Tune hyperparameters further, especially class weights, tree depth,
  `min_samples_leaf`, and thresholding rules.
- Add interaction features such as billed amount versus department average,
  billed amount versus provider rejection history, and LOS versus department
  average LOS.
- Test resampling strategies such as SMOTE, undersampling, or hybrid
  over/under-sampling inside the training split only.
- Evaluate changes using business-critical recall for High Risk visits and
  Rejected claims, not only accuracy.

## Production Readiness Notes

- Keep model predictions advisory and review-based.
- Log prediction inputs, outputs, timestamps, model versions, and segment fields.
- Monitor feature drift, prediction drift, and business-critical recall.
- Retrain only after validating data-quality and temporal-consistency issues.
"""

    (DOCS_DIR / "Phase4_Model_Card.md").write_text(report, encoding="utf-8")


def main() -> None:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    create_model_report("risk", "Risk Model", "High")
    create_model_report("claim", "Claim Model", "Rejected")
    create_explainability_report()
    create_model_card_report()
    print(f"Wrote Phase 4 reports under {DOCS_DIR}")


if __name__ == "__main__":
    main()
