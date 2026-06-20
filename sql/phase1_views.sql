-- Reusable business and data-quality views for Phase 1.

PRAGMA foreign_keys = ON;

CREATE VIEW v_hospital_encounters AS
SELECT
    v.visit_id,
    v.patient_id,
    p.age,
    p.gender,
    p.city,
    p.insurance_provider,
    p.chronic_flag,
    p.registration_date,
    v.visit_date,
    v.department,
    v.visit_type,
    v.length_of_stay_hours,
    v.risk_score,
    v.doctor_id,
    b.bill_id,
    b.billed_amount,
    b.approved_amount,
    b.claim_status,
    b.payment_days,
    b.billing_date,
    CASE
        WHEN b.billed_amount > 0 AND b.approved_amount IS NOT NULL
            THEN b.approved_amount / b.billed_amount
        ELSE NULL
    END AS visit_realization_ratio
FROM visits v
JOIN patients p
    ON p.patient_id = v.patient_id
LEFT JOIN billing b
    ON b.visit_id = v.visit_id;

CREATE VIEW v_department_kpis AS
SELECT
    department,
    COUNT(*) AS total_visits,
    ROUND(AVG(length_of_stay_hours), 2) AS avg_length_of_stay_hours,
    SUM(CASE WHEN risk_score = 'High' THEN 1 ELSE 0 END) AS high_risk_visits,
    ROUND(
        100.0 * SUM(CASE WHEN risk_score = 'High' THEN 1 ELSE 0 END) / COUNT(*),
        2
    ) AS high_risk_visit_pct,
    ROUND(SUM(billed_amount), 2) AS total_billed_amount,
    ROUND(SUM(COALESCE(approved_amount, 0)), 2) AS total_approved_amount,
    ROUND(SUM(COALESCE(approved_amount, 0)) / NULLIF(SUM(billed_amount), 0), 4)
        AS revenue_realization_ratio
FROM v_hospital_encounters
GROUP BY department;

CREATE VIEW v_insurance_kpis AS
SELECT
    insurance_provider,
    COUNT(DISTINCT patient_id) AS covered_patients,
    COUNT(*) AS total_visits,
    ROUND(SUM(billed_amount), 2) AS total_billed_amount,
    ROUND(SUM(COALESCE(approved_amount, 0)), 2) AS total_approved_amount,
    SUM(CASE WHEN claim_status = 'Rejected' THEN 1 ELSE 0 END) AS rejected_claims,
    ROUND(
        100.0 * SUM(CASE WHEN claim_status = 'Rejected' THEN 1 ELSE 0 END) / COUNT(*),
        2
    ) AS claim_rejection_rate_pct,
    ROUND(AVG(payment_days), 2) AS avg_payment_days,
    ROUND(SUM(COALESCE(approved_amount, 0)) / NULLIF(SUM(billed_amount), 0), 4)
        AS revenue_realization_ratio
FROM v_hospital_encounters
GROUP BY insurance_provider;

CREATE VIEW v_city_patient_flow_kpis AS
WITH patient_visit_counts AS (
    SELECT
        p.patient_id,
        p.city,
        COUNT(v.visit_id) AS visit_count
    FROM patients p
    LEFT JOIN visits v
        ON v.patient_id = p.patient_id
    GROUP BY p.patient_id, p.city
)
SELECT
    city,
    COUNT(*) AS total_patients,
    SUM(visit_count) AS total_visits,
    ROUND(AVG(visit_count), 2) AS avg_visits_per_patient
FROM patient_visit_counts
GROUP BY city;

CREATE VIEW v_quality_visits_without_billing AS
SELECT
    v.visit_id,
    v.patient_id,
    v.visit_date,
    v.department,
    v.visit_type,
    v.risk_score
FROM visits v
LEFT JOIN billing b
    ON b.visit_id = v.visit_id
WHERE b.visit_id IS NULL;

CREATE VIEW v_quality_billing_without_visit AS
SELECT
    b.bill_id,
    b.visit_id,
    b.billed_amount,
    b.approved_amount,
    b.claim_status,
    b.payment_days,
    b.billing_date
FROM billing b
LEFT JOIN visits v
    ON v.visit_id = b.visit_id
WHERE v.visit_id IS NULL;

CREATE VIEW v_quality_duplicate_patient_ids_raw AS
SELECT
    CAST(patient_id AS INTEGER) AS patient_id,
    COUNT(*) AS duplicate_count
FROM raw_patients
GROUP BY patient_id
HAVING COUNT(*) > 1;

CREATE VIEW v_quality_invalid_operational_values AS
SELECT
    'visits' AS source_table,
    CAST(visit_id AS INTEGER) AS record_id,
    'length_of_stay_hours' AS field_name,
    length_of_stay_hours AS field_value,
    'Missing or invalid length_of_stay_hours' AS issue_description
FROM raw_visits
WHERE TRIM(COALESCE(length_of_stay_hours, '')) = ''
   OR CAST(length_of_stay_hours AS REAL) < 0
UNION ALL
SELECT
    'billing' AS source_table,
    CAST(bill_id AS INTEGER) AS record_id,
    'payment_days' AS field_name,
    payment_days AS field_value,
    'Missing or invalid payment_days' AS issue_description
FROM raw_billing
WHERE TRIM(COALESCE(payment_days, '')) = ''
   OR CAST(payment_days AS REAL) < 0;

CREATE VIEW v_quality_missing_insurance_visits AS
SELECT
    v.visit_id,
    v.patient_id,
    p.city,
    p.insurance_provider,
    v.department,
    v.visit_date
FROM visits v
JOIN patients p
    ON p.patient_id = v.patient_id
WHERE p.insurance_provider IS NULL
   OR TRIM(p.insurance_provider) = '';

CREATE VIEW v_quality_temporal_anomalies AS
SELECT
    visit_id,
    patient_id,
    registration_date,
    visit_date,
    billing_date,
    CASE
        WHEN visit_date < registration_date THEN 'Visit occurs before patient registration'
        WHEN billing_date < visit_date THEN 'Billing date occurs before visit date'
        ELSE 'No temporal anomaly'
    END AS issue_description
FROM v_hospital_encounters
WHERE visit_date < registration_date
   OR billing_date < visit_date;

CREATE VIEW v_quality_summary AS
SELECT
    'Visits without billing record' AS quality_check,
    COUNT(*) AS issue_count,
    'Critical relationship integrity' AS severity
FROM v_quality_visits_without_billing
UNION ALL
SELECT
    'Billing records without visit record' AS quality_check,
    COUNT(*) AS issue_count,
    'Critical relationship integrity' AS severity
FROM v_quality_billing_without_visit
UNION ALL
SELECT
    'Duplicate patient_id values in raw source' AS quality_check,
    COUNT(*) AS issue_count,
    'Primary key integrity' AS severity
FROM v_quality_duplicate_patient_ids_raw
UNION ALL
SELECT
    'Missing or invalid length_of_stay_hours/payment_days' AS quality_check,
    COUNT(*) AS issue_count,
    'Operational data quality' AS severity
FROM v_quality_invalid_operational_values
UNION ALL
SELECT
    'Visits linked to missing insurance provider' AS quality_check,
    COUNT(*) AS issue_count,
    'Revenue analytics completeness' AS severity
FROM v_quality_missing_insurance_visits
UNION ALL
SELECT
    'Temporal anomalies: visit before registration or bill before visit' AS quality_check,
    COUNT(*) AS issue_count,
    'Business logic consistency' AS severity
FROM v_quality_temporal_anomalies;
