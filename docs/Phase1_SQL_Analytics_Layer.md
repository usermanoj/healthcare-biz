# Phase 1 - SQL Analytics Layer

## Purpose

Phase 1 builds the trusted SQL foundation for the Healthcare Business Capstone:
the Hospital Operations & Revenue Risk Intelligence Platform. The goal is to
convert the three raw CSV files into a structured relational database that
hospital leadership can use for operational, financial, and data-quality
decision-making.

The implementation uses SQLite because it is portable, self-contained, and easy
to grade. The schema design, constraints, keys, indexes, and SQL queries follow
the same relational principles that would apply in PostgreSQL, MySQL, or SQL
Server.

## Phase 1 Artifacts

| Artifact | Location | Purpose |
|---|---|---|
| SQLite database | `database/hospital_operations.db` | Queryable hospital analytics database |
| Schema SQL | `sql/phase1_schema.sql` | Raw staging tables, typed tables, constraints, keys, indexes |
| View SQL | `sql/phase1_views.sql` | Reusable KPI and data-quality views |
| Named query SQL | `sql/phase1_analysis_queries.sql` | Operational, financial, and data-quality analysis queries |
| Database build script | `scripts/build_phase1_database.py` | Rebuilds the SQLite database from CSV files |
| Query export script | `scripts/run_phase1_queries.py` | Exports each named query to `data_outputs/phase1` |
| Phase 1 notebook | `notebooks/Phase1_SQL.ipynb` | Notebook walkthrough for SQL analytics layer |
| Query outputs | `data_outputs/phase1/*.csv` | Auditable result files for each Phase 1 query |
| Load audit | `data_outputs/phase1/phase1_load_audit.json` | Row counts and quality summary after loading |

## Data Model

The database has two layers:

1. Raw staging tables: `raw_patients`, `raw_visits`, and `raw_billing`.
   These preserve source rows for duplicate and source-quality checks.
2. Typed relational tables: `patients`, `visits`, and `billing`.
   These enforce keys, types, domain checks, and foreign-key relationships.

### Core Tables

| Table | Primary Key | Foreign Keys | Business Role |
|---|---|---|---|
| `patients` | `patient_id` | None | Patient demographics, insurance, registration |
| `visits` | `visit_id` | `patient_id` -> `patients.patient_id` | Hospital encounter and operational data |
| `billing` | `bill_id` | `visit_id` -> `visits.visit_id` | Billing, approval, claim, and payment data |

### Relationship Design

`patients` to `visits` is one-to-many. One patient can have many visits.

`visits` to `billing` is one-to-one in the provided data. The `billing.visit_id`
field is unique and references `visits.visit_id`.

Foreign-key checks pass with 0 violations. The typed tables contain:

| Table | Row Count |
|---|---:|
| `patients` | 5,000 |
| `visits` | 25,000 |
| `billing` | 25,000 |

## Constraints and Validation Rules

The typed schema enforces:

- Unique patient, visit, and billing identifiers.
- Valid visit-to-patient and billing-to-visit relationships.
- Patient age between 0 and 120.
- Gender restricted to `M` or `F`.
- Chronic flag restricted to `0` or `1`.
- Visit type restricted to `OPD`, `ER`, or `ICU`.
- Risk score restricted to `Low`, `Medium`, or `High`.
- Claim status restricted to `Paid`, `Pending`, or `Rejected`.
- Non-negative length of stay, billed amount, approved amount, and payment days.
- Approved amount cannot exceed billed amount when approved amount is present.

The schema intentionally does not reject temporal inconsistencies such as billing
dates before visit dates. Those are business-rule quality issues and are captured
through reusable data-quality views so downstream EDA can investigate them.

## Reusable Views

| View | Purpose |
|---|---|
| `v_hospital_encounters` | Full patient, visit, and billing join for analytics |
| `v_department_kpis` | Department volume, LOS, high-risk rate, billed amount, approved amount, realization ratio |
| `v_insurance_kpis` | Provider-level visits, claims, rejection rate, payment delay, realization ratio |
| `v_city_patient_flow_kpis` | City-level patient count, visit count, and visits per patient |
| `v_quality_visits_without_billing` | Visits missing billing records |
| `v_quality_billing_without_visit` | Billing records with invalid visit references |
| `v_quality_duplicate_patient_ids_raw` | Duplicate patient IDs in the raw source |
| `v_quality_invalid_operational_values` | Missing or invalid LOS/payment-day values |
| `v_quality_missing_insurance_visits` | Visits linked to missing insurance provider |
| `v_quality_temporal_anomalies` | Visit-before-registration and bill-before-visit records |
| `v_quality_summary` | Consolidated quality-check counts |

## Index Strategy

| Index | Supports |
|---|---|
| `idx_patients_city` | City-level patient flow and visits per patient |
| `idx_patients_insurance_provider` | Insurance provider billing and claim analytics |
| `idx_patients_registration_date` | Registration-date checks and future time features |
| `idx_visits_patient_id` | Patient-to-visit joins |
| `idx_visits_visit_date` | Time-based analysis and future train/test split support |
| `idx_visits_department` | Department volume and average LOS queries |
| `idx_visits_visit_type` | Visit-type distribution and future feature engineering |
| `idx_visits_risk_score` | Risk-score filtering |
| `idx_visits_doctor_id` | Doctor workload analysis |
| `idx_visits_department_risk` | High-risk percentage by department |
| `idx_visits_doctor_risk` | Doctors handling highest high-risk visit counts |
| `idx_billing_visit_id` | Visit-to-billing joins |
| `idx_billing_claim_status` | Claim rejection and status queries |
| `idx_billing_billing_date` | Billing time analysis and future monitoring |
| `idx_billing_payment_days` | Payment-delay analysis |
| `idx_billing_billed_amount` | High-billed claim identification |
| `idx_billing_claim_payment` | Claim-status and payment-delay combined queries |

## Operational Analysis Findings

### Top Departments by Visit Volume

| Department | Total Visits |
|---|---:|
| General | 4,228 |
| ER | 4,220 |
| Neurology | 4,165 |
| Orthopedics | 4,164 |
| Cardiology | 4,159 |
| ICU | 4,064 |

Leadership interpretation: visit volume is evenly distributed across
departments. General and ER have the highest demand, but the difference between
the largest and smallest department is modest.

### Highest Average Length of Stay

| Department | Total Visits | Avg LOS Hours |
|---|---:|---:|
| Neurology | 4,165 | 19.72 |
| Orthopedics | 4,164 | 19.66 |
| Cardiology | 4,159 | 19.60 |
| ER | 4,220 | 19.53 |
| General | 4,228 | 19.43 |

Leadership interpretation: average length of stay is close across departments.
Neurology and Orthopedics should be monitored first for patient-flow efficiency,
but there is no extreme departmental outlier in Phase 1.

### High-Risk Visit Percentage by Department

| Department | Total Visits | High-Risk Visits | High-Risk % |
|---|---:|---:|---:|
| ICU | 4,064 | 845 | 20.79 |
| ER | 4,220 | 872 | 20.66 |
| Neurology | 4,165 | 846 | 20.31 |
| Orthopedics | 4,164 | 842 | 20.22 |
| General | 4,228 | 839 | 19.84 |
| Cardiology | 4,159 | 790 | 18.99 |

Leadership interpretation: ICU and ER carry the highest high-risk share, which
fits operational expectations. These departments should be prioritized in the
later risk-classification workflow.

### Average Visits per Patient by City

| City | Total Patients | Total Visits | Avg Visits per Patient |
|---|---:|---:|---:|
| Pune | 831 | 4,221 | 5.08 |
| Hyderabad | 869 | 4,370 | 5.03 |
| Bangalore | 840 | 4,205 | 5.01 |
| Mumbai | 822 | 4,122 | 5.01 |
| Chennai | 801 | 3,975 | 4.96 |
| Delhi | 837 | 4,107 | 4.91 |

Leadership interpretation: visit frequency is broadly consistent by city.
Pune has the highest average visits per patient, while Delhi has the lowest.

### Doctors Handling Highest Number of High-Risk Visits

| Doctor ID | High-Risk Visits |
|---:|---:|
| 174 | 71 |
| 198 | 69 |
| 169 | 68 |
| 177 | 67 |
| 105 | 65 |
| 135 | 65 |
| 180 | 64 |
| 188 | 64 |
| 131 | 62 |
| 108 | 61 |

Leadership interpretation: these doctors are the highest-volume high-risk
handlers and should be considered in staffing, escalation, and workload review.

## Financial Analysis Findings

### Top Insurance Providers by Total Billed Amount

| Insurance Provider | Covered Patients | Total Visits | Total Billed Amount |
|---|---:|---:|---:|
| MediCareX | 1,281 | 6,532 | 134,591,163.08 |
| CareOne | 1,255 | 6,283 | 130,707,992.64 |
| HealthPlus | 1,241 | 6,220 | 130,180,740.75 |
| SecureLife | 1,190 | 5,965 | 126,289,039.58 |

Leadership interpretation: MediCareX represents the largest billed exposure and
should receive close attention in revenue-risk monitoring.

### Highest Claim Rejection Rate by Provider

| Insurance Provider | Total Claims | Rejected Claims | Rejection Rate % |
|---|---:|---:|---:|
| SecureLife | 5,965 | 936 | 15.69 |
| MediCareX | 6,532 | 996 | 15.25 |
| HealthPlus | 6,220 | 931 | 14.97 |
| CareOne | 6,283 | 934 | 14.87 |

Leadership interpretation: SecureLife has the highest rejection rate, while
MediCareX has the largest absolute number of rejected claims. Both deserve
attention from the finance team.

### Average Payment Delay by Provider

| Insurance Provider | Total Claims | Claims with Payment Days | Avg Payment Days |
|---|---:|---:|---:|
| SecureLife | 5,965 | 5,785 | 13.08 |
| HealthPlus | 6,220 | 6,000 | 13.08 |
| CareOne | 6,283 | 6,099 | 13.03 |
| MediCareX | 6,532 | 6,326 | 13.01 |

Leadership interpretation: payment delay is nearly identical across providers.
The stronger financial signal in Phase 1 is rejection and realization rather
than payment-day variation.

### Revenue Realization Ratio by Department

| Department | Total Claims | Total Billed Amount | Total Approved Amount | Realization Ratio |
|---|---:|---:|---:|---:|
| ICU | 4,064 | 84,757,763.76 | 63,166,516.84 | 0.7453 |
| Orthopedics | 4,164 | 87,811,455.80 | 65,211,585.83 | 0.7426 |
| General | 4,228 | 87,131,451.86 | 64,690,870.95 | 0.7425 |
| Neurology | 4,165 | 87,310,048.09 | 64,708,778.69 | 0.7411 |
| ER | 4,220 | 88,686,960.35 | 65,672,329.38 | 0.7405 |
| Cardiology | 4,159 | 86,071,256.19 | 63,705,806.68 | 0.7402 |

Leadership interpretation: realization ratios are tightly clustered near 74%.
Cardiology and ER are the lowest and should be monitored for revenue leakage.

### High-Billed Claims with Zero or Missing Approved Amount

The Phase 1 query defines high-billed claims as the top 5% of billed amounts
using `NTILE(20)`. It found 72 high-billed visits where approved amount is zero
or missing. These records are exported to:

`data_outputs/phase1/financial_high_billed_zero_or_missing_approved.csv`

Leadership interpretation: these claims are high-value revenue-risk candidates.
They should be prioritized for manual finance review and later claim-outcome
prediction.

## Data Quality and Integrity Results

| Quality Check | Issue Count | Severity |
|---|---:|---|
| Billing records without visit record | 0 | Critical relationship integrity |
| Visits without billing record | 0 | Critical relationship integrity |
| Duplicate patient_id values in raw source | 0 | Primary key integrity |
| Missing or invalid length_of_stay_hours/payment_days | 790 | Operational data quality |
| Visits linked to missing insurance provider | 0 | Revenue analytics completeness |
| Temporal anomalies: visit before registration or bill before visit | 20,569 | Business logic consistency |

Interpretation:

- Primary and foreign-key integrity is strong.
- Missing payment-day values are present and should be handled carefully in EDA.
- A large number of temporal anomalies exist. These should not be ignored.
  They may reflect synthetic data generation limitations, but they affect
  feature engineering such as days since registration, billing lag, and
  time-based modeling.

## Reproducibility

Run Phase 1 from the project root:

```powershell
python scripts/build_phase1_database.py
python scripts/run_phase1_queries.py
python scripts/create_phase1_notebook.py
```

Expected database path:

```text
database/hospital_operations.db
```

Expected query output folder:

```text
data_outputs/phase1/
```

## Phase 2 Handoff

Phase 2 should use `v_hospital_encounters` or a SQL extract from it as the
starting point for EDA. The following Phase 1 fields and flags should be carried
forward:

- Patient demographics: age, gender, city, insurance provider, chronic flag.
- Operational fields: department, visit type, length of stay, doctor ID,
  visit date.
- Billing fields: billed amount, approved amount, claim status, payment days,
  billing date.
- Data-quality flags: missing payment days, zero/missing approved amount,
  temporal anomalies.
- Business aggregates: provider rejection rate, patient visit frequency,
  department average LOS, and department realization ratio.

Important leakage note for later phases: `approved_amount` and `payment_days`
are outcome/post-outcome fields for claim status. They should not be used as
predictors if Model B is framed as pre-submission claim-outcome prediction.
