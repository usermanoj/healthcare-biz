# Phase 2 - Exploratory Data Analysis & Data Quality Report

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
| Combined encounter rows | 25,000 |
| Modeling table rows | 25,000 |
| Modeling table columns | 69 |
| Total billed amount | 521,768,936.05 |
| Total approved amount | 387,155,888.37 |
| Overall revenue realization ratio | 0.7420 |

Risk-score distribution:

| risk_score | row_count |
| --- | --- |
| High | 5034 |
| Low | 12470 |
| Medium | 7496 |

Claim-status distribution:

| claim_status | row_count |
| --- | --- |
| Paid | 14940 |
| Pending | 6263 |
| Rejected | 3797 |

## Missing Value Analysis

| field_name | missing_count | missing_pct | zero_count | non_missing_count |
| --- | --- | --- | --- | --- |
| approved_amount | 1318 | 5.27 | 3597 | 23682 |
| payment_days | 790 | 3.16 | 0 | 24210 |
| length_of_stay_hours | 0 | 0.0 | 0 | 25000 |

Interpretation:

- `length_of_stay_hours` has no missing values, so operational LOS analysis is
  complete for Phase 2.
- `approved_amount` has missing values and zero values; both are important for
  revenue-risk analysis.
- `payment_days` has missing values and should be imputed or flagged before
  modeling, depending on the Phase 3 target.

## Distribution Analysis

### Department Distribution

| department | visit_count | patient_count | avg_los_hours | high_risk_rate | rejected_claim_rate | avg_payment_days | total_billed_amount | total_approved_amount | visit_pct | revenue_realization_ratio |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| General | 4228 | 2870 | 19.4349 | 0.1984 | 0.1521 | 12.9795 | 87131451.86 | 64690870.95 | 0.1691 | 0.7425 |
| ER | 4220 | 2850 | 19.535 | 0.2066 | 0.15 | 13.1337 | 88686960.35 | 65672329.38 | 0.1688 | 0.7405 |
| Neurology | 4165 | 2857 | 19.7181 | 0.2031 | 0.1505 | 13.0481 | 87310048.09 | 64708778.69 | 0.1666 | 0.7411 |
| Orthopedics | 4164 | 2832 | 19.6627 | 0.2022 | 0.1563 | 13.2584 | 87811455.8 | 65211585.83 | 0.1666 | 0.7426 |
| Cardiology | 4159 | 2817 | 19.601 | 0.1899 | 0.156 | 12.922 | 86071256.19 | 63705806.68 | 0.1664 | 0.7402 |
| ICU | 4064 | 2776 | 19.3552 | 0.2079 | 0.1462 | 12.9432 | 84757763.76 | 63166516.84 | 0.1626 | 0.7453 |

### Visit Type Distribution

| visit_type | visit_count | patient_count | avg_los_hours | high_risk_rate | rejected_claim_rate | avg_payment_days | total_billed_amount | total_approved_amount | visit_pct | revenue_realization_ratio |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ER | 8382 | 4039 | 19.4082 | 0.2059 | 0.16 | 12.9952 | 174903143.09 | 128799791.32 | 0.3353 | 0.7364 |
| OPD | 8381 | 4127 | 19.7127 | 0.2009 | 0.1477 | 13.0192 | 175780335.22 | 130956499.24 | 0.3352 | 0.745 |
| ICU | 8237 | 4089 | 19.5336 | 0.1972 | 0.1479 | 13.1317 | 171085457.74 | 127399597.81 | 0.3295 | 0.7447 |

### Insurance Provider Distribution

| insurance_provider | visit_count | patient_count | avg_los_hours | high_risk_rate | rejected_claim_rate | avg_payment_days | total_billed_amount | total_approved_amount | visit_pct | revenue_realization_ratio |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| MediCareX | 6532 | 1281 | 19.2785 | 0.2015 | 0.1525 | 13.009 | 134591163.08 | 100135468.79 | 0.2613 | 0.744 |
| CareOne | 6283 | 1255 | 19.5408 | 0.1975 | 0.1487 | 13.0269 | 130707992.64 | 96997758.17 | 0.2513 | 0.7421 |
| HealthPlus | 6220 | 1241 | 19.8506 | 0.2084 | 0.1497 | 13.0818 | 130180740.75 | 96251775.08 | 0.2488 | 0.7394 |
| SecureLife | 5965 | 1190 | 19.5502 | 0.198 | 0.1569 | 13.0781 | 126289039.58 | 93770886.33 | 0.2386 | 0.7425 |

### City Distribution

| city | visit_count | patient_count | avg_los_hours | high_risk_rate | rejected_claim_rate | avg_payment_days | total_billed_amount | total_approved_amount | visit_pct | revenue_realization_ratio |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Hyderabad | 4370 | 864 | 19.7772 | 0.2057 | 0.1547 | 13.0217 | 91097751.41 | 67365864.83 | 0.1748 | 0.7395 |
| Pune | 4221 | 824 | 19.5907 | 0.2137 | 0.1497 | 13.1176 | 87374577.4 | 64678050.39 | 0.1688 | 0.7402 |
| Bangalore | 4205 | 837 | 19.5717 | 0.1876 | 0.1539 | 12.9804 | 88492056.89 | 65332141.64 | 0.1682 | 0.7383 |
| Mumbai | 4122 | 821 | 19.3029 | 0.1931 | 0.1502 | 13.063 | 86407762.21 | 64338793.6 | 0.1649 | 0.7446 |
| Delhi | 4107 | 829 | 19.4727 | 0.2145 | 0.1468 | 13.1601 | 85800727.91 | 64208792.73 | 0.1643 | 0.7483 |
| Chennai | 3975 | 792 | 19.5802 | 0.193 | 0.156 | 12.9446 | 82596060.23 | 61232245.18 | 0.159 | 0.7413 |

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

| field_name | q1 | q3 | iqr | mild_low_threshold | mild_high_threshold | extreme_low_threshold | extreme_high_threshold | normal_count | missing_count | mild_low_count | mild_high_count | extreme_low_count | extreme_high_count | outlier_count | outlier_pct |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| billed_amount | 11582.45 | 28398.065 | 16815.615 | -13640.9725 | 53621.4875 | -38864.395 | 78844.91 | 24627 | 0 | 0 | 369 | 0 | 4 | 373 | 1.49 |
| payment_days | 8.0 | 17.0 | 9.0 | -5.5 | 30.5 | -19.0 | 44.0 | 23701 | 790 | 0 | 490 | 0 | 19 | 509 | 2.04 |
| length_of_stay_hours | 9.96 | 27.3125 | 17.3525 | -16.06875 | 53.34125 | -42.0975 | 79.37 | 24744 | 0 | 0 | 256 | 0 | 0 | 256 | 1.02 |

Interpretation:

- `billed_amount` and `length_of_stay_hours` contain high-side outliers that
  may represent high-resource or high-cost encounters.
- `payment_days` contains both missing values and high-side outliers.
- Outlier flags are retained in the modeling table rather than removing records,
  because high-cost and delayed-payment cases are business-relevant.

## Temporal and Business-Rule Quality

| quality_check | issue_count | issue_pct |
| --- | --- | --- |
| visit_before_registration | 12157 | 48.63 |
| billing_before_visit | 12389 | 49.56 |
| same_day_billing | 80 | 0.32 |
| high_billed_zero_or_missing_approved | 72 | 0.29 |

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
