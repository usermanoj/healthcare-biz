-- Phase 1 named analysis queries.
-- Scripts parse each query using the "-- name:" marker.

-- name: operational_top10_departments_by_visit_volume
SELECT
    department,
    COUNT(*) AS total_visits
FROM visits
GROUP BY department
ORDER BY total_visits DESC, department
LIMIT 10;

-- name: operational_top5_departments_by_avg_los
SELECT
    department,
    COUNT(*) AS total_visits,
    ROUND(AVG(length_of_stay_hours), 2) AS avg_length_of_stay_hours
FROM visits
GROUP BY department
ORDER BY avg_length_of_stay_hours DESC, total_visits DESC
LIMIT 5;

-- name: operational_high_risk_pct_by_department
SELECT
    department,
    COUNT(*) AS total_visits,
    SUM(CASE WHEN risk_score = 'High' THEN 1 ELSE 0 END) AS high_risk_visits,
    ROUND(
        100.0 * SUM(CASE WHEN risk_score = 'High' THEN 1 ELSE 0 END) / COUNT(*),
        2
    ) AS high_risk_visit_pct
FROM visits
GROUP BY department
ORDER BY high_risk_visit_pct DESC, total_visits DESC;

-- name: operational_avg_visits_per_patient_by_city
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
GROUP BY city
ORDER BY avg_visits_per_patient DESC, total_visits DESC;

-- name: operational_top_doctors_by_high_risk_visits
SELECT
    doctor_id,
    COUNT(*) AS high_risk_visits
FROM visits
WHERE risk_score = 'High'
GROUP BY doctor_id
ORDER BY high_risk_visits DESC, doctor_id
LIMIT 10;

-- name: financial_top10_insurance_providers_by_total_billed
SELECT
    p.insurance_provider,
    COUNT(DISTINCT p.patient_id) AS covered_patients,
    COUNT(v.visit_id) AS total_visits,
    ROUND(SUM(b.billed_amount), 2) AS total_billed_amount
FROM patients p
JOIN visits v
    ON v.patient_id = p.patient_id
JOIN billing b
    ON b.visit_id = v.visit_id
GROUP BY p.insurance_provider
ORDER BY total_billed_amount DESC
LIMIT 10;

-- name: financial_top5_insurance_providers_by_rejection_rate
SELECT
    p.insurance_provider,
    COUNT(*) AS total_claims,
    SUM(CASE WHEN b.claim_status = 'Rejected' THEN 1 ELSE 0 END) AS rejected_claims,
    ROUND(
        100.0 * SUM(CASE WHEN b.claim_status = 'Rejected' THEN 1 ELSE 0 END) / COUNT(*),
        2
    ) AS claim_rejection_rate_pct
FROM patients p
JOIN visits v
    ON v.patient_id = p.patient_id
JOIN billing b
    ON b.visit_id = v.visit_id
GROUP BY p.insurance_provider
ORDER BY claim_rejection_rate_pct DESC, rejected_claims DESC
LIMIT 5;

-- name: financial_avg_payment_delay_by_insurance_provider
SELECT
    p.insurance_provider,
    COUNT(*) AS total_claims,
    COUNT(b.payment_days) AS claims_with_payment_days,
    ROUND(AVG(b.payment_days), 2) AS avg_payment_days
FROM patients p
JOIN visits v
    ON v.patient_id = p.patient_id
JOIN billing b
    ON b.visit_id = v.visit_id
GROUP BY p.insurance_provider
ORDER BY avg_payment_days DESC;

-- name: financial_revenue_realization_ratio_by_department
SELECT
    v.department,
    COUNT(*) AS total_claims,
    ROUND(SUM(b.billed_amount), 2) AS total_billed_amount,
    ROUND(SUM(COALESCE(b.approved_amount, 0)), 2) AS total_approved_amount,
    ROUND(SUM(COALESCE(b.approved_amount, 0)) / NULLIF(SUM(b.billed_amount), 0), 4)
        AS revenue_realization_ratio
FROM visits v
JOIN billing b
    ON b.visit_id = v.visit_id
GROUP BY v.department
ORDER BY revenue_realization_ratio DESC;

-- name: financial_high_billed_zero_or_missing_approved
WITH ranked_claims AS (
    SELECT
        b.bill_id,
        b.visit_id,
        v.patient_id,
        v.department,
        p.insurance_provider,
        b.billed_amount,
        b.approved_amount,
        b.claim_status,
        b.payment_days,
        b.billing_date,
        NTILE(20) OVER (ORDER BY b.billed_amount) AS billed_amount_twentieth
    FROM billing b
    JOIN visits v
        ON v.visit_id = b.visit_id
    JOIN patients p
        ON p.patient_id = v.patient_id
)
SELECT
    bill_id,
    visit_id,
    patient_id,
    department,
    insurance_provider,
    billed_amount,
    approved_amount,
    claim_status,
    payment_days,
    billing_date
FROM ranked_claims
WHERE billed_amount_twentieth = 20
  AND (approved_amount IS NULL OR approved_amount = 0)
ORDER BY billed_amount DESC, bill_id;

-- name: dq_visits_without_billing
SELECT *
FROM v_quality_visits_without_billing
ORDER BY visit_id;

-- name: dq_billing_without_visit
SELECT *
FROM v_quality_billing_without_visit
ORDER BY bill_id;

-- name: dq_duplicate_patient_ids
SELECT *
FROM v_quality_duplicate_patient_ids_raw
ORDER BY duplicate_count DESC, patient_id;

-- name: dq_missing_or_invalid_los_or_payment_days
SELECT *
FROM v_quality_invalid_operational_values
ORDER BY source_table, record_id;

-- name: dq_visits_with_missing_insurance_provider
SELECT *
FROM v_quality_missing_insurance_visits
ORDER BY visit_id;

-- name: dq_temporal_anomalies_additional_check
SELECT *
FROM v_quality_temporal_anomalies
ORDER BY visit_id;

-- name: dq_summary_counts
SELECT *
FROM v_quality_summary
ORDER BY
    CASE severity
        WHEN 'Critical relationship integrity' THEN 1
        WHEN 'Primary key integrity' THEN 2
        WHEN 'Operational data quality' THEN 3
        WHEN 'Revenue analytics completeness' THEN 4
        ELSE 5
    END,
    quality_check;
