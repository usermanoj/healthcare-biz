# Phase 5 - Deployment and Operations Runbook

## Purpose

Phase 5 operationalizes the Healthcare Operations & Revenue Risk Intelligence
Platform as a FastAPI service. The API exposes the trained visit-risk and
claim-outcome classifiers to hospital dashboards and internal systems in real
time while validating requests and logging audit-ready prediction metadata.

## Service Components

| Component | Location | Purpose |
|---|---|---|
| FastAPI app | `src/healthcare_api/main.py` | API endpoints |
| Pydantic schemas | `src/healthcare_api/schemas.py` | Request and response validation |
| Model service | `src/healthcare_api/model_service.py` | Model loading, prediction, probabilities |
| Audit logging | `src/healthcare_api/logging_utils.py` | JSONL prediction audit trail |
| API runner | `scripts/run_api.py` | Starts Uvicorn with local paths configured |
| Smoke test | `scripts/smoke_test_api.py` | Validates endpoints without a network server |
| Requirements | `requirements.txt` | Reproducible dependencies |

## Models Served

| Model | Artifact | Version | Endpoint |
|---|---|---|---|
| Visit Risk Classification | `models/risk_selected_model.joblib` | `risk-v1.0.0-phase3` | `POST /predict/risk` |
| Claim Outcome Classification | `models/claim_selected_model.joblib` | `claim-v1.0.0-phase3` | `POST /predict/claim` |

## Local Setup

From the project root:

```powershell
$py = 'C:\Users\Admin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
& $py -m pip install --target .pythonlibs -r requirements.txt
```

The `.pythonlibs` folder is intentionally ignored by git. It is a local runtime
dependency cache only.

## Run the API

```powershell
$py = 'C:\Users\Admin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
& $py scripts\run_api.py
```

Default local URL:

```text
http://127.0.0.1:8000
```

Interactive OpenAPI docs:

```text
http://127.0.0.1:8000/docs
```

## Health Checks

```powershell
Invoke-RestMethod -Method GET -Uri http://127.0.0.1:8000/health
```

Expected behavior:

- `status` is `ok`
- both models show as loaded
- log path is returned
- timestamp is returned in UTC

## Prediction Logging

Every prediction call appends one JSON line to:

```text
logs/prediction_audit_log.jsonl
```

Each log record contains:

- request ID
- model name
- model version
- prediction
- class probabilities
- SHA-256 feature hash
- API version
- UTC log timestamp

The API does not store raw patient-identifying fields in the audit log. It logs
a feature hash and prediction metadata for traceability while reducing exposure.

## Operational Checks

Before deployment:

1. Confirm `GET /health` returns `ok`.
2. Confirm `GET /version` returns expected model versions.
3. Run `python scripts/smoke_test_api.py`.
4. Confirm `logs/prediction_audit_log.jsonl` is created after prediction calls.
5. Confirm dashboards use the `/metadata` endpoint to align with current model
   features and labels.

## Production Readiness Notes

- Use HTTPS and authentication before exposing the service outside a trusted
  internal network.
- Keep predictions advisory. The models support triage and review workflows;
  they should not make autonomous clinical or claim decisions.
- Rotate and retain prediction logs according to hospital governance policy.
- Monitor feature drift, prediction drift, data validation failures, and
  business-critical recall in Phase 6.
- Retrain only after validating source-data quality and temporal anomalies.

