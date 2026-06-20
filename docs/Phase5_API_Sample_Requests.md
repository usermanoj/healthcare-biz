# Phase 5 - Sample API Requests and Responses

## Base URL

```text
http://127.0.0.1:8000
```

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Health check and model-load status |
| GET | `/version` | API and model version metadata |
| GET | `/metadata` | Feature sets, selected model metadata, and labels |
| POST | `/predict/risk` | Predict Low/Medium/High visit risk |
| POST | `/predict/claim` | Predict Paid/Pending/Rejected claim outcome |
| POST | `/predict/batch` | Score multiple risk and claim requests |

## Risk Prediction Request

```json
{
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
  "visit_date": "2025-11-15T00:00:00Z"
}
```

Example command:

```powershell
$body = Get-Content docs\sample_payload_risk.json -Raw
Invoke-RestMethod -Method POST -Uri http://127.0.0.1:8000/predict/risk -ContentType 'application/json' -Body $body
```

Example response:

```json
{
  "request_id": "risk-demo-001",
  "model_name": "risk",
  "model_version": "risk-v1.0.0-phase3",
  "prediction": "High",
  "probabilities": {
    "High": 0.424304,
    "Low": 0.276604,
    "Medium": 0.299092
  },
  "feature_hash": "26939e0f6a20b99dd04e13e11307931939f158774f38214fb57f825a65fb9aa7",
  "logged": true,
  "generated_at_utc": "2026-06-20T07:06:58.237005Z"
}
```

## Claim Prediction Request

```json
{
  "request_id": "claim-demo-001",
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
  "bill_id": 900001,
  "billed_amount": 48500.0,
  "billing_date": "2025-11-17T00:00:00Z",
  "provider_prior_claim_count": 3200,
  "provider_prior_rejection_rate": 0.151,
  "provider_prior_rejection_missing_flag": 0,
  "high_billed_amount_flag": 1,
  "billed_amount_outlier_flag": 0,
  "length_of_stay_hours_outlier_flag": 0
}
```

Example command:

```powershell
$body = Get-Content docs\sample_payload_claim.json -Raw
Invoke-RestMethod -Method POST -Uri http://127.0.0.1:8000/predict/claim -ContentType 'application/json' -Body $body
```

Example response:

```json
{
  "request_id": "claim-demo-001",
  "model_name": "claim",
  "model_version": "claim-v1.0.0-phase3",
  "prediction": "Paid",
  "probabilities": {
    "Paid": 0.553112,
    "Pending": 0.332504,
    "Rejected": 0.114384
  },
  "feature_hash": "d41df45eafdeb57baf432819617ed95ed92300dfc3b48850ab433deafd111eb6",
  "logged": true,
  "generated_at_utc": "2026-06-20T07:06:58.282464Z"
}
```

## Validation Behavior

The API rejects:

- unsupported categorical values,
- negative numeric fields,
- missing required model features,
- unexpected fields in request bodies,
- empty batch requests.

FastAPI returns HTTP `422` with validation details when a request fails schema
validation.

