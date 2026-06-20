# Phase 3 - Model Development Report

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

**Business purpose:** Predict whether a hospital visit represents Low, Medium, or High operational/clinical risk to support triage, staffing, and resource planning.

**Target:** `risk_score`

### Feature Set Justification

| feature_group | business_reason |
| --- | --- |
| patient demographics | age, gender, city, chronic status, and age band capture patient-level risk context. |
| visit operations | department, visit type, doctor assignment, and LOS describe encounter complexity and resource use. |
| patient history | prior visit count and prior average LOS capture repeat-utilization and historical operational burden. |
| timing | visit month, weekday, weekend flag, and registration timing support seasonal and operational-flow analysis. |
| quality flags | temporal anomaly and missing-history flags preserve known reliability issues from Phase 2. |

### Time-Based Split

| Split Field | Value |
|---|---|
| Sort columns | visit_date, visit_id |
| Train rows | 20000 |
| Test rows | 5000 |
| Train date range | 2025-01-20 to 2025-11-08 |
| Test date range | 2025-11-08 to 2026-01-20 |

### Class Distribution

| split | class | count | pct |
| --- | --- | --- | --- |
| all | High | 5034 | 20.14 |
| all | Low | 12470 | 49.88 |
| all | Medium | 7496 | 29.98 |
| train | High | 4010 | 20.05 |
| train | Low | 9991 | 49.95 |
| train | Medium | 5999 | 30.0 |
| test | High | 1024 | 20.48 |
| test | Low | 2479 | 49.58 |
| test | Medium | 1497 | 29.94 |

### Test Metrics

| model | accuracy | balanced_accuracy | macro_f1 | weighted_f1 | High_recall |
| --- | --- | --- | --- | --- | --- |
| Logistic Regression baseline | 0.3462 | 0.337394 | 0.330425 | 0.357097 | 0.301758 |
| Random Forest advanced | 0.399 | 0.344868 | 0.336759 | 0.388935 | 0.109375 |

### Selected Risk Model

| Field | Value |
|---|---|
| Selected model | logistic_regression |
| Selection rule | Select higher test macro F1; if macro F1 is within 0.01, prefer the model with stronger business-critical recall. |
| Selection reason | Baseline selected because macro F1 is within 0.01 of the advanced model and business-critical recall is higher. |
| Artifact | `models/risk_selected_model.joblib` |
| Test macro F1 | 0.330425 |
| Test weighted F1 | 0.357097 |
| High-risk recall | 0.301758 |

## Model B - Claim Outcome Classification

**Business purpose:** Predict whether an insurance claim will be Paid, Pending, or Rejected before submission to support proactive revenue-risk control.

**Target:** `claim_status`

### Feature Set Justification

| feature_group | business_reason |
| --- | --- |
| claim economics | billed amount and high-bill flags represent financial exposure known at claim creation. |
| patient and encounter context | demographics, department, visit type, doctor, chronic status, and LOS describe claim complexity. |
| payer history | prior provider rejection rate uses only earlier claims and supports payer-risk estimation. |
| timing | billing lag and visit/billing calendar fields support payment-cycle and process-pattern learning. |
| quality flags | temporal anomaly and outlier flags preserve known data-reliability signals without using claim outcomes. |

### Time-Based Split

| Split Field | Value |
|---|---|
| Sort columns | billing_date, bill_id |
| Train rows | 20000 |
| Test rows | 5000 |
| Train date range | 2025-01-20 to 2025-11-10 |
| Test date range | 2025-11-10 to 2026-01-20 |

### Class Distribution

| split | class | count | pct |
| --- | --- | --- | --- |
| all | Paid | 14940 | 59.76 |
| all | Pending | 6263 | 25.05 |
| all | Rejected | 3797 | 15.19 |
| train | Paid | 11964 | 59.82 |
| train | Pending | 5007 | 25.04 |
| train | Rejected | 3029 | 15.14 |
| test | Paid | 2976 | 59.52 |
| test | Pending | 1256 | 25.12 |
| test | Rejected | 768 | 15.36 |

### Test Metrics

| model | accuracy | balanced_accuracy | macro_f1 | weighted_f1 | Rejected_recall |
| --- | --- | --- | --- | --- | --- |
| Logistic Regression baseline | 0.288 | 0.351877 | 0.280168 | 0.306201 | 0.596354 |
| Random Forest advanced | 0.4682 | 0.400805 | 0.356695 | 0.456436 | 0.492188 |

### Selected Claim Model

| Field | Value |
|---|---|
| Selected model | random_forest |
| Selection rule | Select higher test macro F1; if macro F1 is within 0.01, prefer the model with stronger business-critical recall. |
| Selection reason | Advanced model selected because it has the stronger test macro F1. |
| Artifact | `models/claim_selected_model.joblib` |
| Test macro F1 | 0.356695 |
| Test weighted F1 | 0.456436 |
| Rejected-claim recall | 0.492188 |

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

| artifact | path |
| --- | --- |
| Risk baseline model | models/risk_logistic_regression.joblib |
| Risk advanced model | models/risk_random_forest.joblib |
| Risk selected model | models/risk_selected_model.joblib |
| Claim baseline model | models/claim_logistic_regression.joblib |
| Claim advanced model | models/claim_random_forest.joblib |
| Claim selected model | models/claim_selected_model.joblib |

## Recommendation for Phase 4

Phase 4 should emphasize evaluation, explainability, and business impact rather
than just raw accuracy. In particular:

- inspect confusion matrices for High Risk and Rejected classes,
- evaluate feature importance and stability,
- perform fairness slices by gender, city, and insurance provider,
- create a model card documenting weak/strong points, assumptions, and
  deployment limitations.
