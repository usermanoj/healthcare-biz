# Phase 6 Governance and Compliance Document

Generated at UTC: 2026-06-20T08:13:07+00:00

## Governance Objective

The objective of Phase 6 is to keep the healthcare AI system reliable after deployment by validating incoming data, detecting feature and prediction drift, maintaining traceable audit metadata, and defining a controlled retraining strategy.

## System Inventory

| Component | Current Artifact or Version | Governance Purpose |
| --- | --- | --- |
| Risk classification model | `models/risk_selected_model.joblib` | Flags Low, Medium, or High visit risk for operational triage. |
| Claim outcome model | `models/claim_selected_model.joblib` | Predicts Paid, Pending, or Rejected claim outcome for revenue-risk planning. |
| API service | `src/healthcare_api/main.py` | Provides validated real-time scoring endpoints. |
| Feature schema | `data_outputs/phase3/risk_feature_set.json`, `data_outputs/phase3/claim_feature_set.json` | Defines production model inputs and leakage exclusions. |
| Monitoring runner | `scripts/run_monitoring.py` | Produces validation, drift, prediction, and audit summaries. |
| Audit log | `logs/prediction_audit_log.jsonl` | Records prediction metadata with request ID, model version, prediction, probability payload, feature hash, and timestamp. |

## Data Validation Controls

- Required model inputs are checked for missing values before monitoring outputs are accepted.
- Numeric features are checked against observed reference min/max values to identify records outside the original model envelope.
- Business validity ranges are enforced for fields such as age, binary flags, billed amount, payment days, length of stay, months, weekdays, and rates.
- Categorical features are compared against reference categories to detect unseen payer, city, department, visit type, gender, doctor, or age-band values.
- Critical reliability fields from Phase 2, including approved amount, payment days, and length of stay, are monitored even when they are not all used as pre-submission model inputs.

## Drift Monitoring Controls

- Feature drift status counts from the latest run: drift: 10, stable: 42.
- Prediction drift status counts from the latest run: stable: 1, watch: 1.
- PSI below 0.10 is stable, 0.10 to below 0.20 requires watch-list review, and 0.20 or higher requires drift investigation.
- Risk predictions are monitored for shifts in High Risk prediction rate.
- Claim predictions are monitored for shifts in Rejected claim prediction rate.
- Drift alerts should be reviewed with hospital operations, billing leadership, and data science before changing model behavior.

## Auditability and Traceability

- Latest audit-log availability: True.
- Latest audit-log record count: 6.
- Model versions observed in audit log: claim-v1.0.0-phase3, risk-v1.0.0-phase3.
- The API logs prediction metadata and a feature hash, not full raw payloads. This supports investigation while reducing exposure of sensitive input data in logs.
- Audit logs should be retained according to the hospital's records policy and protected with access controls equivalent to other operational analytics logs.

## Human Oversight Requirements

- Predictions are decision-support signals, not autonomous clinical or billing decisions.
- High Risk visit predictions should be reviewed by authorized operational or clinical staff before affecting prioritization.
- Rejected claim predictions should be used to trigger finance review, not to deny or delay care.
- Any model output challenged by staff should be logged, investigated, and reviewed during model governance meetings.

## Known Limitations and Assumptions

- The capstone data is historical and structured; it does not include free-text clinical notes, lab results, medication history, or real-time bed capacity.
- Phase 4 found modest test performance, so the models should be treated as early decision-support prototypes.
- Temporal anomalies such as visit-before-registration and billing-before-visit flags exist in the data and are explicitly monitored rather than silently discarded.
- The current monitoring run uses the latest 20 percent of the historical data as a simulated current window. A production deployment should replace this with actual scored production records and delayed outcome labels.
- Compliance readiness requires hospital security, privacy, legal, and clinical governance review before any real patient use.

## Retraining Strategy

- Run data validation daily for incoming scoring batches or API request aggregates.
- Run feature and prediction drift checks weekly while volume is low, then daily when production volume is sufficient.
- Recompute labeled performance monthly or whenever enough new outcomes arrive to create a statistically meaningful evaluation window.
- Trigger retraining review if any core feature or prediction PSI is at or above 0.20 for two consecutive monitoring runs.
- Trigger urgent review if High Risk recall or Rejected claim recall falls materially below the Phase 4 baseline after labels are available.
- Retrain using the same leakage-safe feature policy from Phase 3, perform the Phase 4 evaluation and fairness review again, and publish a refreshed model card before promotion.
- Promote a new model only after documented approval from data science, hospital operations, finance, and governance stakeholders.

## Incident Response

- Stop automated dashboard consumption if validation failures affect required fields or if an audit log is unavailable during production scoring.
- Freeze model promotion if unseen categories indicate an upstream integration change that has not been mapped.
- Notify stakeholders when drift status reaches the drift threshold, document root cause, and decide whether to recalibrate, retrain, or temporarily fall back to rules-based review.
- Preserve the model artifact, feature schema, monitoring outputs, and audit summaries for every incident review.

## Phase 6 Submission Artifacts

- `scripts/run_monitoring.py`
- `scripts/create_phase6_reports.py`
- `data_outputs/phase6/data_validation_report.csv`
- `data_outputs/phase6/feature_drift_report.csv`
- `data_outputs/phase6/prediction_drift_report.csv`
- `data_outputs/phase6/audit_log_summary.json`
- `data_outputs/phase6/drift_detection_summary.json`
- `docs/Phase6_Drift_Detection_Report.md`
- `docs/Phase6_Governance_Compliance.md`

## Reproduction Commands

Run these commands from the project root using the same Python environment used for model training and API deployment:

```bash
python scripts/run_monitoring.py
python scripts/create_phase6_reports.py
```
