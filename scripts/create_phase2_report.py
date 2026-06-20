"""Create the Phase 2 markdown data quality and EDA report."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PHASE2_DIR = PROJECT_ROOT / "data_outputs" / "phase2"
DOCS_DIR = PROJECT_ROOT / "docs"
REPORT_PATH = DOCS_DIR / "Phase2_EDA_Data_Quality_Report.md"


def markdown_table(df: pd.DataFrame) -> str:
    clean = df.copy()
    clean = clean.fillna("")
    headers = [str(col) for col in clean.columns]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for _, row in clean.iterrows():
        values = [str(row[col]) for col in clean.columns]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def money(value: float) -> str:
    return f"{value:,.2f}"


def pct(value: float) -> str:
    return f"{value:.2f}%"


def main() -> None:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    profile = json.loads((PHASE2_DIR / "phase2_eda_profile.json").read_text(encoding="utf-8"))
    missing = pd.read_csv(PHASE2_DIR / "missing_values_summary.csv")
    outliers = pd.read_csv(PHASE2_DIR / "outlier_summary.csv")
    temporal = pd.read_csv(PHASE2_DIR / "temporal_quality_summary.csv")
    department = pd.read_csv(PHASE2_DIR / "distribution_by_department.csv")
    visit_type = pd.read_csv(PHASE2_DIR / "distribution_by_visit_type.csv")
    provider = pd.read_csv(PHASE2_DIR / "distribution_by_insurance_provider.csv")
    city = pd.read_csv(PHASE2_DIR / "distribution_by_city.csv")

    report = f"""# Phase 2 - Exploratory Data Analysis & Data Quality Report

## Business Purpose

Phase 2 evaluates hospital operations, financial performance, and data
reliability before model development. The analysis starts from the trusted
Phase 1 SQL view `v_hospital_encounters`, then creates a modeling-ready dataset
with engineered operational, financial, temporal, and data-quality features.

## Deliverables Created

| Deliverable | Location |
|---|---|
| EDA notebook | `notebooks/01_eda.ipynb` |
| Feature engineering script | `scripts/build_features.py` |
| Modeling dataset | `data_outputs/model_table.csv` |
| Feature schema | `data_outputs/feature_schema.json` |
| Phase 2 summary outputs | `data_outputs/phase2/` |
| Data quality report | `docs/Phase2_EDA_Data_Quality_Report.md` |

## Dataset Summary

| Metric | Value |
|---|---:|
| Combined encounter rows | {profile["encounter_rows"]:,} |
| Modeling table rows | {profile["model_table_rows"]:,} |
| Modeling table columns | {profile["model_table_columns"]:,} |
| Total billed amount | {money(profile["total_billed_amount"])} |
| Total approved amount | {money(profile["total_approved_amount"])} |
| Overall revenue realization ratio | {profile["overall_revenue_realization_ratio"]:.4f} |

Risk-score distribution:

{markdown_table(pd.DataFrame(profile["risk_score_distribution"].items(), columns=["risk_score", "row_count"]))}

Claim-status distribution:

{markdown_table(pd.DataFrame(profile["claim_status_distribution"].items(), columns=["claim_status", "row_count"]))}

## Missing Value Analysis

{markdown_table(missing)}

Interpretation:

- `length_of_stay_hours` has no missing values, so operational LOS analysis is
  complete for Phase 2.
- `approved_amount` has missing values and zero values; both are important for
  revenue-risk analysis.
- `payment_days` has missing values and should be imputed or flagged before
  modeling, depending on the Phase 3 target.

## Distribution Analysis

### Department Distribution

{markdown_table(department)}

### Visit Type Distribution

{markdown_table(visit_type)}

### Insurance Provider Distribution

{markdown_table(provider)}

### City Distribution

{markdown_table(city)}

Interpretation:

- Department, city, provider, and visit-type volumes are broadly balanced.
- High-risk rates and rejection rates vary modestly across groups, which means
  Phase 3 should not expect one simple categorical split to dominate model
  performance.
- Financial exposure is large across every provider, making claim-risk
  monitoring relevant even when percentage differences are small.

## Outlier Detection and Classification

Outliers were classified using the IQR method:

- mild low/high: outside 1.5 x IQR
- extreme low/high: outside 3.0 x IQR
- missing: null value
- normal: within the mild thresholds

{markdown_table(outliers)}

Interpretation:

- `billed_amount` and `length_of_stay_hours` contain high-side outliers that
  may represent high-resource or high-cost encounters.
- `payment_days` contains both missing values and high-side outliers.
- Outlier flags are retained in the modeling table rather than removing records,
  because high-cost and delayed-payment cases are business-relevant.

## Temporal and Business-Rule Quality

{markdown_table(temporal)}

Interpretation:

- Visit-before-registration and billing-before-visit records are retained as
  explicit flags.
- These records should not be silently corrected because doing so would hide a
  material data reliability risk.
- Phase 3 should use time-based splits carefully and avoid relying on raw
  temporal calculations without considering these anomaly flags.

## Engineered Features

The modeling table includes:

- patient visit frequency: `patient_total_visits`
- patient average LOS: `patient_avg_los_hours`
- time-aware patient history: `patient_prior_visit_count`,
  `patient_prior_avg_los_hours`
- provider rejection behavior: `provider_rejection_rate`,
  `provider_prior_rejection_rate`
- department aggregates: `department_avg_los_hours`,
  `department_high_risk_rate`, `department_revenue_realization_ratio`
- registration and billing timing: `days_since_registration`,
  `billing_lag_days`
- time-based visit features: visit year, month, quarter, week, day of week,
  weekend flag
- data-quality flags: missingness, temporal anomalies, zero/missing approvals,
  high-billed zero/missing approval, and outlier flags

## Modeling Readiness Notes

The dataset is ready for Phase 3, with two target variables:

- Visit Risk Classification target: `risk_score`
- Claim Outcome Classification target: `claim_status`

Important leakage controls for Phase 3:

- Do not use `risk_score` or `high_risk_flag` as predictors for the risk model.
- Do not use `claim_status`, `claim_rejected_flag`, or `claim_pending_flag` as
  predictors for the claim model.
- Do not use `approved_amount`, `payment_days`, `approved_to_billed_ratio`,
  `revenue_gap_amount`, or `visit_realization_ratio` as predictors for a
  pre-submission claim-outcome model.
- `provider_rejection_rate` is useful for EDA, but for claim modeling it should
  be recomputed on training data only or replaced with the historical
  `provider_prior_rejection_rate` feature.

## Business Recommendations Before Modeling

1. Treat payment-day missingness and approved-amount missingness as revenue
   process signals, not only technical missing values.
2. Prioritize high-billed claims with zero or missing approvals for finance
   review.
3. Retain temporal anomaly flags for monitoring and governance.
4. Use stratified model evaluation by department, city, insurance provider, and
   visit type because group-level differences are modest but business-relevant.
5. Carry the feature schema into Phase 3 so model training remains leakage-aware
   and reproducible.
"""

    REPORT_PATH.write_text(report, encoding="utf-8")
    print(f"Wrote report: {REPORT_PATH}")


if __name__ == "__main__":
    main()
