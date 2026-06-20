# Healthcare Business AI/ML Capstone Submission

This package contains the evaluator-facing deliverables for all six phases plus the final executive business report. Codex screenshot PNGs, `.git`, local virtual libraries, and transient API server logs are intentionally excluded from the submission zip.

## Final Executive Deliverable

- `Healthcare_Insights_Report.docx` - 2-3 page executive business report covering operational findings, financial findings, model impact, deployment architecture, governance, and leadership recommendations.
- `scripts/create_executive_report.py` - reproducible generator for the final executive report.

## Source Inputs

- `Capstone Project.docx`
- `Capstone Project Phase Details.docx`
- `patients.csv`
- `visits.csv`
- `billing.csv`

## Phase 1 - SQL Analytics Foundation

- `sql/phase1_schema.sql`
- `sql/phase1_views.sql`
- `sql/phase1_analysis_queries.sql`
- `database/hospital_operations.db`
- `notebooks/Phase1_SQL.ipynb`
- `scripts/build_phase1_database.py`
- `scripts/run_phase1_queries.py`
- `docs/Phase1_SQL_Analytics_Layer.md`
- `data_outputs/phase1/`

## Phase 2 - EDA and Data Quality

- `notebooks/01_eda.ipynb`
- `scripts/build_features.py`
- `scripts/create_phase2_notebook.py`
- `scripts/create_phase2_report.py`
- `docs/Phase2_EDA_Data_Quality_Report.md`
- `data_outputs/model_table.csv`
- `data_outputs/feature_schema.json`
- `data_outputs/phase2/`

## Phase 3 - Model Development

- `notebooks/02_risk_model.ipynb`
- `notebooks/03_claim_model.ipynb`
- `scripts/train_models.py`
- `scripts/create_phase3_notebooks.py`
- `scripts/create_phase3_report.py`
- `models/`
- `docs/Phase3_Model_Development_Report.md`
- `data_outputs/phase3/`

## Phase 4 - Model Evaluation and Explainability

- `scripts/evaluate_models.py`
- `scripts/create_phase4_reports.py`
- `docs/Phase4_Risk_Model_Evaluation_Report.md`
- `docs/Phase4_Claim_Model_Evaluation_Report.md`
- `docs/Phase4_Explainability_Summary.md`
- `docs/Phase4_Model_Card.md`
- `data_outputs/phase4/`

## Phase 5 - Model Deployment and API Integration

- `src/healthcare_api/`
- `scripts/run_api.py`
- `scripts/smoke_test_api.py`
- `docs/Phase5_Deployment_Runbook.md`
- `docs/Phase5_API_Sample_Requests.md`
- `docs/sample_payload_risk.json`
- `docs/sample_payload_claim.json`
- `data_outputs/phase5/`
- `logs/prediction_audit_log.jsonl` - sample prediction audit log only; transient server stdout/stderr logs are excluded.

## Phase 6 - Monitoring, Drift Detection, and Governance

- `scripts/run_monitoring.py`
- `scripts/create_phase6_reports.py`
- `docs/Phase6_Drift_Detection_Report.md`
- `docs/Phase6_Governance_Compliance.md`
- `data_outputs/phase6/`

## Environment and Reproduction

- `requirements.txt` lists the Python dependencies used by the project.
- The API can be started with `python scripts/run_api.py`.
- Phase 6 monitoring can be regenerated with:

```bash
python scripts/run_monitoring.py
python scripts/create_phase6_reports.py
```

Note: model artifacts were trained with scikit-learn-compatible Python 3.12 in this environment. If model loading fails in another interpreter, use a Python 3.12 environment with the versions in `requirements.txt`.
