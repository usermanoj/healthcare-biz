# Phase 4 - Risk Model Evaluation Report

## Purpose

Prioritize visits for operational and clinical risk triage.

## Selected Model

| Field | Value |
|---|---|
| Selected model | logistic_regression |
| Selection rule | Select higher test macro F1; if macro F1 is within 0.01, prefer the model with stronger business-critical recall. |
| Selection reason | Baseline selected because macro F1 is within 0.01 of the advanced model and business-critical recall is higher. |
| Artifact | `models/risk_selected_model.joblib` |

## Aggregate Metrics

| split | accuracy | balanced_accuracy | macro_precision | macro_recall | macro_f1 | weighted_f1 | business_class | business_recall |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| train | 0.36235 | 0.376164 | 0.371616 | 0.376164 | 0.355825 | 0.372147 | High | 0.4202 |
| test | 0.3462 | 0.337394 | 0.338318 | 0.337394 | 0.330425 | 0.357097 | High | 0.301758 |

Business-critical recall class: **High**

## Train Classification Report

| class_label | precision | recall | f1_score | support |
| --- | --- | --- | --- | --- |
| Low | 0.542155 | 0.328896 | 0.409419 | 9991 |
| Medium | 0.340311 | 0.379397 | 0.358792 | 5999 |
| High | 0.232382 | 0.4202 | 0.299263 | 4010 |
| macro_avg | 0.371616 | 0.376164 | 0.355825 | 20000 |
| weighted_avg | 0.419502 | 0.36235 | 0.372147 | 20000 |

## Test Classification Report

| class_label | precision | recall | f1_score | support |
| --- | --- | --- | --- | --- |
| Low | 0.507572 | 0.365067 | 0.424683 | 2479 |
| Medium | 0.302339 | 0.345357 | 0.32242 | 1497 |
| High | 0.205043 | 0.301758 | 0.244172 | 1024 |
| macro_avg | 0.338318 | 0.337394 | 0.330425 | 5000 |
| weighted_avg | 0.384167 | 0.3462 | 0.357097 | 5000 |

## Fairness and Segment Analysis

Segment-level performance was evaluated by gender, city, and insurance provider
on the test split.

### Fairness Gap Summary

| segment_column | min_recall_segment | min_business_recall | max_recall_segment | max_business_recall | business_recall_gap | segments_evaluated |
| --- | --- | --- | --- | --- | --- | --- |
| city | Bangalore | 0.157895 | Pune | 0.463415 | 0.30552 | 6 |
| gender | F | 0.274621 | M | 0.330645 | 0.056024 | 2 |
| insurance_provider | CareOne | 0.242915 | HealthPlus | 0.348 | 0.105085 | 4 |

### Segment Detail

| segment_column | segment_value | row_count | accuracy | business_class | business_class_support | business_recall | prediction_business_class_rate | actual_business_class_rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| city | Bangalore | 830 | 0.380723 | High | 152 | 0.157895 | 0.186747 | 0.183133 |
| city | Mumbai | 815 | 0.353374 | High | 167 | 0.179641 | 0.196319 | 0.204908 |
| city | Chennai | 821 | 0.365408 | High | 167 | 0.245509 | 0.230207 | 0.20341 |
| city | Hyderabad | 894 | 0.3434 | High | 189 | 0.328042 | 0.313199 | 0.211409 |
| city | Delhi | 851 | 0.3349 | High | 185 | 0.410811 | 0.418331 | 0.217391 |
| city | Pune | 789 | 0.297845 | High | 164 | 0.463415 | 0.465146 | 0.207858 |
| gender | F | 2525 | 0.350495 | High | 528 | 0.274621 | 0.275248 | 0.209109 |
| gender | M | 2475 | 0.341818 | High | 496 | 0.330645 | 0.328081 | 0.200404 |
| insurance_provider | CareOne | 1235 | 0.37166 | High | 247 | 0.242915 | 0.261538 | 0.2 |
| insurance_provider | MediCareX | 1366 | 0.327233 | High | 290 | 0.282759 | 0.287701 | 0.212299 |
| insurance_provider | SecureLife | 1203 | 0.354115 | High | 237 | 0.337553 | 0.296758 | 0.197007 |
| insurance_provider | HealthPlus | 1196 | 0.333612 | High | 250 | 0.348 | 0.362876 | 0.20903 |

## Explainability Summary

The explainability method depends on the selected model:

- Logistic Regression: strongest absolute class coefficients.
- Random Forest: impurity-based feature importance.

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

## Safety Interpretation

- Use the model to prioritize review, not to automate final clinical or finance
  decisions.
- Track business-critical recall over time because missing High Risk visits or
  Rejected claims has direct operational and financial impact.
- Monitor segment gaps; if gaps widen in production, retraining or workflow
  constraints should be reviewed before wider deployment.
