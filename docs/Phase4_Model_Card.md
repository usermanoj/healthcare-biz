# Phase 4 - Consolidated Model Card

## Project

Hospital Operations & Revenue Risk Intelligence Platform

## Model Overview

| Model | Target | Selected Model | Test Macro F1 | Business Recall |
|---|---|---|---:|---:|
| Visit Risk Classification | risk_score | logistic_regression | 0.330425 | 0.301758 |
| Claim Outcome Classification | claim_status | random_forest | 0.356695 | 0.492188 |

## Intended Use

- Operational triage and staffing support for hospital visits.
- Revenue-cycle review and pre-submission claim risk prioritization.

## Not Intended Use

- Do not use as a standalone clinical diagnosis system.
- Do not auto-deny care or insurance claims based only on model output.
- Do not use without monitoring for drift, fairness gaps, and data-quality anomalies.

## Stakeholders

Risk model stakeholders: hospital administrators, clinical operations teams, doctors

Claim model stakeholders: finance teams, revenue-cycle teams, hospital administrators

## Major Limitations

- Dataset is synthetic and has weak visible signal between predictors and targets.
- Temporal anomalies were identified in Phase 1 and preserved as flags.
- Model performance is modest; predictions should support review workflows rather than automate final decisions.
- Fairness analysis is limited to available demographic/location/provider fields.

## Fairness and Safety

Fairness was evaluated on the test split by:

- gender
- city
- insurance provider

Segment gaps are documented in:

- `data_outputs/phase4/risk_fairness_gap_summary.csv`
- `data_outputs/phase4/claim_fairness_gap_summary.csv`

## Governance Recommendations

- Use human review for High Risk and Rejected prediction workflows.
- Monitor business-critical recall for High Risk visits and Rejected claims.
- Track segment performance by gender, city, and insurance provider.
- Retrain only after validating source-data quality and temporal consistency.

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
