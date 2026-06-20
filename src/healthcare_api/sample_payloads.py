"""Sample request payloads used by docs and smoke tests."""

from __future__ import annotations


RISK_SAMPLE = {
    "request_id": "risk-demo-001",
    "age": 56,
    "gender": "F",
    "city": "Hyderabad",
    "insurance_provider": "HealthPlus",
    "chronic_flag": 1,
    "department": "ICU",
    "visit_type": "ER",
    "doctor_id": 174,
    "length_of_stay_hours": 22.5,
    "patient_prior_visit_count": 3,
    "patient_prior_avg_los_hours": 18.2,
    "patient_prior_avg_los_missing_flag": 0,
    "registration_date": "2025-01-20T00:00:00Z",
    "visit_date": "2025-11-15T00:00:00Z",
}


CLAIM_SAMPLE = {
    **RISK_SAMPLE,
    "request_id": "claim-demo-001",
    "bill_id": 900001,
    "billed_amount": 48500.0,
    "billing_date": "2025-11-17T00:00:00Z",
    "provider_prior_claim_count": 3200,
    "provider_prior_rejection_rate": 0.151,
    "provider_prior_rejection_missing_flag": 0,
    "high_billed_amount_flag": 1,
    "billed_amount_outlier_flag": 0,
    "length_of_stay_hours_outlier_flag": 0,
}

