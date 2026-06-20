# Phase 4 - Claim Model Evaluation Report

## Purpose

Identify claim outcome risk before submission to reduce revenue leakage.

## Selected Model

| Field | Value |
|---|---|
| Selected model | random_forest |
| Selection rule | Select higher test macro F1; if macro F1 is within 0.01, prefer the model with stronger business-critical recall. |
| Selection reason | Advanced model selected because it has the stronger test macro F1. |
| Artifact | `models/claim_selected_model.joblib` |

## Aggregate Metrics

| split | accuracy | balanced_accuracy | macro_precision | macro_recall | macro_f1 | weighted_f1 | business_class | business_recall |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| train | 0.7082 | 0.756432 | 0.724855 | 0.756432 | 0.691771 | 0.735637 | Rejected | 0.909871 |
| test | 0.4682 | 0.400805 | 0.377396 | 0.400805 | 0.356695 | 0.456436 | Rejected | 0.492188 |

Business-critical recall class: **Rejected**

## Train Classification Report

| class_label | precision | recall | f1_score | support |
| --- | --- | --- | --- | --- |
| Paid | 0.922799 | 0.661401 | 0.770534 | 11964 |
| Pending | 0.882576 | 0.698023 | 0.779525 | 5007 |
| Rejected | 0.36919 | 0.909871 | 0.525253 | 3029 |
| macro_avg | 0.724855 | 0.756432 | 0.691771 | 20000 |
| weighted_avg | 0.828885 | 0.7082 | 0.735637 | 20000 |

## Test Classification Report

| class_label | precision | recall | f1_score | support |
| --- | --- | --- | --- | --- |
| Paid | 0.642065 | 0.622648 | 0.632207 | 2976 |
| Pending | 0.268293 | 0.08758 | 0.132053 | 1256 |
| Rejected | 0.221831 | 0.492188 | 0.305825 | 768 |
| macro_avg | 0.377396 | 0.400805 | 0.356695 | 5000 |
| weighted_avg | 0.483626 | 0.4682 | 0.456436 | 5000 |

## Fairness and Segment Analysis

Segment-level performance was evaluated by gender, city, and insurance provider
on the test split.

### Fairness Gap Summary

| segment_column | min_recall_segment | min_business_recall | max_recall_segment | max_business_recall | business_recall_gap | segments_evaluated |
| --- | --- | --- | --- | --- | --- | --- |
| city | Delhi | 0.401786 | Bangalore | 0.533835 | 0.132049 | 6 |
| gender | M | 0.458333 | F | 0.522059 | 0.063726 | 2 |
| insurance_provider | SecureLife | 0.408377 | CareOne | 0.596386 | 0.188009 | 4 |

### Segment Detail

| segment_column | segment_value | row_count | accuracy | business_class | business_class_support | business_recall | prediction_business_class_rate | actual_business_class_rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| city | Delhi | 795 | 0.447799 | Rejected | 112 | 0.401786 | 0.327044 | 0.140881 |
| city | Mumbai | 831 | 0.483755 | Rejected | 120 | 0.475 | 0.315283 | 0.144404 |
| city | Chennai | 810 | 0.460494 | Rejected | 129 | 0.496124 | 0.348148 | 0.159259 |
| city | Hyderabad | 893 | 0.490482 | Rejected | 143 | 0.51049 | 0.354983 | 0.160134 |
| city | Pune | 853 | 0.463072 | Rejected | 131 | 0.519084 | 0.350528 | 0.153576 |
| city | Bangalore | 818 | 0.46088 | Rejected | 133 | 0.533835 | 0.347188 | 0.162592 |
| gender | M | 2411 | 0.483202 | Rejected | 360 | 0.458333 | 0.316051 | 0.149316 |
| gender | F | 2589 | 0.454229 | Rejected | 408 | 0.522059 | 0.363847 | 0.15759 |
| insurance_provider | SecureLife | 1210 | 0.482645 | Rejected | 191 | 0.408377 | 0.294215 | 0.157851 |
| insurance_provider | MediCareX | 1326 | 0.481146 | Rejected | 226 | 0.455752 | 0.319005 | 0.170437 |
| insurance_provider | HealthPlus | 1246 | 0.445425 | Rejected | 185 | 0.52973 | 0.378812 | 0.148475 |
| insurance_provider | CareOne | 1218 | 0.463054 | Rejected | 166 | 0.596386 | 0.371921 | 0.136289 |

## Explainability Summary

The explainability method depends on the selected model:

- Logistic Regression: strongest absolute class coefficients.
- Random Forest: impurity-based feature importance.

| feature | importance | explainability_type |
| --- | --- | --- |
| num__billed_amount | 0.1838519844761188 | random_forest_impurity_importance |
| num__days_since_registration | 0.0507234305226171 | random_forest_impurity_importance |
| num__provider_prior_rejection_rate | 0.0504113515645539 | random_forest_impurity_importance |
| num__length_of_stay_hours | 0.0500023556380198 | random_forest_impurity_importance |
| num__provider_prior_claim_count | 0.049045465088311 | random_forest_impurity_importance |
| num__billing_lag_days | 0.0472457957527667 | random_forest_impurity_importance |
| num__patient_prior_avg_los_hours | 0.0452292885559641 | random_forest_impurity_importance |
| num__age | 0.0441842737779434 | random_forest_impurity_importance |
| num__visit_week_of_year | 0.0371593881624597 | random_forest_impurity_importance |
| num__high_billed_amount_flag | 0.0279551491937641 | random_forest_impurity_importance |
| num__billing_day_of_week | 0.0252965751082946 | random_forest_impurity_importance |
| num__visit_day_of_week | 0.0251382480846127 | random_forest_impurity_importance |
| num__billing_month | 0.0238707398007863 | random_forest_impurity_importance |
| num__visit_month | 0.0232065798744697 | random_forest_impurity_importance |
| num__patient_prior_visit_count | 0.0226422361331224 | random_forest_impurity_importance |
| num__visit_quarter | 0.011353399681606 | random_forest_impurity_importance |
| num__chronic_flag | 0.0095308461394452 | random_forest_impurity_importance |
| num__billed_amount_outlier_flag | 0.0086270196856172 | random_forest_impurity_importance |
| cat__gender_F | 0.0085423513155479 | random_forest_impurity_importance |
| cat__gender_M | 0.0078698928849728 | random_forest_impurity_importance |

## Safety Interpretation

- Use the model to prioritize review, not to automate final clinical or finance
  decisions.
- Track business-critical recall over time because missing High Risk visits or
  Rejected claims has direct operational and financial impact.
- Monitor segment gaps; if gaps widen in production, retraining or workflow
  constraints should be reviewed before wider deployment.
