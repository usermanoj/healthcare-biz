# Phase 4 - Explainability Summary

## Purpose

This summary explains the main drivers used by the selected Phase 3 models.
The goal is stakeholder trust: hospital teams should understand what kinds of
signals influence predictions before deployment.

## Risk Model Explainability

The selected risk model is Logistic Regression, so explanations use the
strongest absolute coefficients across risk classes.

| class_label | feature | coefficient | abs_coefficient | explainability_type |
| --- | --- | --- | --- | --- |
| Medium | cat__doctor_id_198 | -0.33292702 | 0.33292702 | logistic_regression_coefficient |
| High | cat__doctor_id_198 | 0.29546147 | 0.29546147 | logistic_regression_coefficient |
| Medium | cat__doctor_id_110 | 0.2871 | 0.2871 | logistic_regression_coefficient |
| Medium | cat__doctor_id_169 | -0.27620797 | 0.27620797 | logistic_regression_coefficient |
| High | cat__doctor_id_128 | -0.25208254 | 0.25208254 | logistic_regression_coefficient |
| Low | cat__doctor_id_136 | 0.25106538 | 0.25106538 | logistic_regression_coefficient |
| High | cat__doctor_id_148 | -0.2415164 | 0.2415164 | logistic_regression_coefficient |
| High | cat__doctor_id_137 | -0.22822389 | 0.22822389 | logistic_regression_coefficient |
| High | cat__doctor_id_169 | 0.22746634 | 0.22746634 | logistic_regression_coefficient |
| High | cat__doctor_id_135 | 0.22481644 | 0.22481644 | logistic_regression_coefficient |
| High | cat__doctor_id_111 | -0.21952939 | 0.21952939 | logistic_regression_coefficient |
| High | cat__doctor_id_134 | -0.21442231 | 0.21442231 | logistic_regression_coefficient |
| Medium | cat__doctor_id_159 | 0.21236755 | 0.21236755 | logistic_regression_coefficient |
| High | cat__doctor_id_157 | -0.21096877 | 0.21096877 | logistic_regression_coefficient |
| High | cat__doctor_id_167 | -0.21088727 | 0.21088727 | logistic_regression_coefficient |
| High | cat__doctor_id_178 | 0.21072496 | 0.21072496 | logistic_regression_coefficient |
| High | cat__doctor_id_105 | 0.20712027 | 0.20712027 | logistic_regression_coefficient |
| High | cat__doctor_id_174 | 0.19268471 | 0.19268471 | logistic_regression_coefficient |
| High | cat__doctor_id_109 | -0.19211909 | 0.19211909 | logistic_regression_coefficient |
| High | cat__doctor_id_110 | -0.19156756 | 0.19156756 | logistic_regression_coefficient |
| Medium | cat__doctor_id_121 | -0.18622918 | 0.18622918 | logistic_regression_coefficient |
| Low | cat__doctor_id_108 | -0.18603788 | 0.18603788 | logistic_regression_coefficient |
| Low | cat__doctor_id_197 | -0.17729463 | 0.17729463 | logistic_regression_coefficient |
| Low | cat__doctor_id_167 | 0.17705406 | 0.17705406 | logistic_regression_coefficient |
| Low | cat__doctor_id_128 | 0.17508393 | 0.17508393 | logistic_regression_coefficient |
| Low | cat__doctor_id_157 | 0.17450369 | 0.17450369 | logistic_regression_coefficient |
| Medium | cat__doctor_id_164 | -0.17405251 | 0.17405251 | logistic_regression_coefficient |
| Low | cat__doctor_id_102 | 0.17019781 | 0.17019781 | logistic_regression_coefficient |
| Medium | cat__doctor_id_160 | 0.16799401 | 0.16799401 | logistic_regression_coefficient |
| Medium | cat__doctor_id_134 | 0.16642102 | 0.16642102 | logistic_regression_coefficient |

## Claim Model Explainability

The selected claim model is Random Forest, so explanations use impurity-based
feature importance.

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

## Interpretation Notes

- Explainability is directional and model-specific; it does not prove clinical
  or financial causality.
- Operational fields, historical utilization, payer history, and temporal flags
  should be interpreted with the Phase 2 data-quality findings in mind.
- Because the dataset is synthetic and signal is modest, explainability should
  support audit and review rather than strong causal claims.
