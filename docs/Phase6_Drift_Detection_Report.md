# Phase 6 Drift Detection Report

Generated at UTC: 2026-06-20T08:13:07+00:00

## Business Purpose

This report monitors whether the deployed hospital risk and claim models remain reliable as operational patterns and payer behavior change. It focuses on incoming data validation, feature drift, prediction drift, and audit-log readiness.

## Monitoring Design

- Source table: `data_outputs/model_table.csv`
- Reference window: earliest 80 percent of records, aligned to the Phase 3 time-based validation design.
- Current window: latest 20 percent of records, used here as a simulated incoming monitoring period.
- Risk reference dates: 2025-01-20 to 2025-11-08
- Risk current dates: 2025-11-08 to 2026-01-20
- Claim reference dates: 2025-01-20 to 2025-11-10
- Claim current dates: 2025-11-10 to 2026-01-20
- Drift metric: Population Stability Index (PSI).
- PSI interpretation: stable below 0.10, watch from 0.10 to below 0.20, drift at or above 0.20.

## Data Validation Results

- Total checks: 93
- Severity counts: fail: 2, pass: 84, warn: 7
- Failed checks: 2
- Warning checks: 7

| check_type | field | severity | violation_count | violation_rate | observed |
| --- | --- | --- | --- | --- | --- |
| critical_field_quality | approved_amount | fail | 247 | 4.94% | missing=247, negative=0 |
| critical_field_quality | payment_days | fail | 159 | 3.18% | missing=159, negative=0 |
| reference_range | provider_prior_claim_count | warn | 4176 | 83.52% | min=4755.0, max=6531.0 |
| reference_range | billing_month | warn | 2163 | 43.26% | min=1.0, max=12.0 |
| reference_range | billing_lag_days | warn | 488 | 9.76% | min=-67.0, max=364.0 |
| reference_range | payment_days | warn | 2 | 0.04% | min=1.0, max=55.0 |
| reference_range | approved_amount | warn | 1 | 0.02% | min=0.0, max=88539.01 |
| reference_range | billed_amount | warn | 1 | 0.02% | min=500.0, max=88539.01 |
| reference_range | length_of_stay_hours | warn | 1 | 0.02% | min=0.5, max=78.42 |

## Feature Drift Results

- Features evaluated: 52
- Severity counts: drift: 10, stable: 42

| model_task | feature | feature_type | psi | severity | current_missing_rate |
| --- | --- | --- | --- | --- | --- |
| claim | provider_prior_claim_count | numeric | 12.433856 | drift | 0.00% |
| risk | visit_month | numeric | 12.07834 | drift | 0.00% |
| claim | billing_month | numeric | 12.018478 | drift | 0.00% |
| risk | visit_week_of_year | numeric | 10.49868 | drift | 0.00% |
| claim | provider_prior_rejection_rate | numeric | 5.615319 | drift | 0.00% |
| claim | billing_lag_days | numeric | 5.38717 | drift | 0.00% |
| risk | visit_quarter | numeric | 5.207644 | drift | 0.00% |
| risk | days_since_registration | numeric | 4.746542 | drift | 0.00% |
| risk | patient_prior_visit_count | numeric | 1.538276 | drift | 0.00% |
| risk | patient_prior_avg_los_hours | numeric | 0.369347 | drift | 0.00% |
| risk | doctor_id | categorical | 0.024622 | stable | 0.00% |
| claim | doctor_id | categorical | 0.02366 | stable | 0.00% |

## Prediction Drift Results

- Tasks evaluated: 2
- Severity counts: stable: 1, watch: 1

| task_name | business_class | prediction_psi | severity | reference_business_rate | current_business_rate |
| --- | --- | --- | --- | --- | --- |
| risk | High | 0.02018 | stable | 36.25% | 30.14% |
| claim | Rejected | 0.149347 | watch | 37.33% | 34.08% |

## Audit Log Monitoring

- Audit log available: True
- Record count: 6
- Invalid JSON lines: 0
- Missing required metadata count: 0
- Duplicate request ID count: 4
- Model versions observed: claim-v1.0.0-phase3, risk-v1.0.0-phase3

## Recommended Monitoring Actions

- Treat any failed required-input check as a release blocker for automated scoring.
- Treat failed critical-field quality checks as governance risks that require investigation before leadership reporting.
- Investigate warning-level reference-range violations before using predictions in dashboards, because they indicate cases outside the original training envelope.
- Escalate any PSI value at or above 0.20 for data science review before the next reporting cycle.
- Compare monitored prediction drift with actual outcomes once labels are available; drift alone does not prove performance degradation.
- Preserve audit summaries and model versions with each monitoring run so future investigations can reconstruct which model produced which prediction.

## Output Artifacts

- `data_outputs/phase6/data_validation_report.csv`
- `data_outputs/phase6/feature_drift_report.csv`
- `data_outputs/phase6/prediction_drift_report.csv`
- `data_outputs/phase6/audit_log_summary.json`
- `data_outputs/phase6/drift_detection_summary.json`

## Reproduction Commands

Run these commands from the project root using the same Python environment used for model training and API deployment:

```bash
python scripts/run_monitoring.py
python scripts/create_phase6_reports.py
```
