"""Create Phase 6 monitoring, drift, and governance documentation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PHASE6_DIR = PROJECT_ROOT / "data_outputs" / "phase6"
DOCS_DIR = PROJECT_ROOT / "docs"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def markdown_table(rows: list[dict[str, Any]], columns: list[str]) -> str:
    if not rows:
        return "No records."
    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join(["---"] * len(columns)) + " |"
    body = []
    for row in rows:
        values = [str(row.get(column, "")).replace("|", "/") for column in columns]
        body.append("| " + " | ".join(values) + " |")
    return "\n".join([header, separator, *body])


def pct(value: float | int | None) -> str:
    if value is None:
        return "N/A"
    return f"{float(value) * 100:.2f}%"


def count_text(counts: dict[str, Any]) -> str:
    if not counts:
        return "none"
    return ", ".join(f"{key}: {value}" for key, value in sorted(counts.items()))


def load_phase6_outputs() -> tuple[dict[str, Any], pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    summary = read_json(PHASE6_DIR / "drift_detection_summary.json")
    validation = pd.read_csv(PHASE6_DIR / "data_validation_report.csv")
    feature_drift = pd.read_csv(PHASE6_DIR / "feature_drift_report.csv")
    prediction_drift = pd.read_csv(PHASE6_DIR / "prediction_drift_report.csv")
    model_card = read_json(PROJECT_ROOT / "data_outputs" / "phase4" / "model_card.json")
    return summary, validation, feature_drift, prediction_drift, model_card


def create_drift_report() -> Path:
    summary, validation, feature_drift, prediction_drift, _ = load_phase6_outputs()
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    validation_issues = validation[validation["violation_count"] > 0].copy()
    validation_issues = validation_issues.sort_values(["severity", "violation_rate"], ascending=[True, False])
    validation_rows = validation_issues.head(12)[
        ["check_type", "field", "severity", "violation_count", "violation_rate", "observed"]
    ].to_dict("records")
    for row in validation_rows:
        row["violation_rate"] = pct(row["violation_rate"])

    top_feature_drift = feature_drift.sort_values("psi", ascending=False).head(12)[
        ["model_task", "feature", "feature_type", "psi", "severity", "current_missing_rate"]
    ].to_dict("records")
    for row in top_feature_drift:
        row["current_missing_rate"] = pct(row["current_missing_rate"])

    prediction_rows = []
    for row in prediction_drift.to_dict("records"):
        prediction_rows.append(
            {
                "task_name": row["task_name"],
                "business_class": row["business_class"],
                "prediction_psi": row["prediction_psi"],
                "severity": row["severity"],
                "reference_business_rate": pct(row["reference_business_class_rate"]),
                "current_business_rate": pct(row["current_business_class_rate"]),
            }
        )

    audit = summary["audit_log"]
    windows = summary["date_windows"]
    lines = [
        "# Phase 6 Drift Detection Report",
        "",
        f"Generated at UTC: {summary['generated_at_utc']}",
        "",
        "## Business Purpose",
        "",
        "This report monitors whether the deployed hospital risk and claim models remain reliable as operational patterns and payer behavior change. It focuses on incoming data validation, feature drift, prediction drift, and audit-log readiness.",
        "",
        "## Monitoring Design",
        "",
        f"- Source table: `{summary['source_model_table']}`",
        "- Reference window: earliest 80 percent of records, aligned to the Phase 3 time-based validation design.",
        "- Current window: latest 20 percent of records, used here as a simulated incoming monitoring period.",
        f"- Risk reference dates: {windows['risk_reference']['start']} to {windows['risk_reference']['end']}",
        f"- Risk current dates: {windows['risk_current']['start']} to {windows['risk_current']['end']}",
        f"- Claim reference dates: {windows['claim_reference']['start']} to {windows['claim_reference']['end']}",
        f"- Claim current dates: {windows['claim_current']['start']} to {windows['claim_current']['end']}",
        "- Drift metric: Population Stability Index (PSI).",
        "- PSI interpretation: stable below 0.10, watch from 0.10 to below 0.20, drift at or above 0.20.",
        "",
        "## Data Validation Results",
        "",
        f"- Total checks: {summary['data_validation']['checks']}",
        f"- Severity counts: {count_text(summary['data_validation']['severity_counts'])}",
        f"- Failed checks: {summary['data_validation']['failed_checks']}",
        f"- Warning checks: {summary['data_validation']['warning_checks']}",
        "",
        markdown_table(
            validation_rows,
            ["check_type", "field", "severity", "violation_count", "violation_rate", "observed"],
        ),
        "",
        "## Feature Drift Results",
        "",
        f"- Features evaluated: {summary['feature_drift']['features_evaluated']}",
        f"- Severity counts: {count_text(summary['feature_drift']['severity_counts'])}",
        "",
        markdown_table(
            top_feature_drift,
            ["model_task", "feature", "feature_type", "psi", "severity", "current_missing_rate"],
        ),
        "",
        "## Prediction Drift Results",
        "",
        f"- Tasks evaluated: {summary['prediction_drift']['tasks_evaluated']}",
        f"- Severity counts: {count_text(summary['prediction_drift']['severity_counts'])}",
        "",
        markdown_table(
            prediction_rows,
            [
                "task_name",
                "business_class",
                "prediction_psi",
                "severity",
                "reference_business_rate",
                "current_business_rate",
            ],
        ),
        "",
        "## Audit Log Monitoring",
        "",
        f"- Audit log available: {audit['available']}",
        f"- Record count: {audit['record_count']}",
        f"- Invalid JSON lines: {audit.get('invalid_line_count', 0)}",
        f"- Missing required metadata count: {audit.get('missing_required_metadata_count', 0)}",
        f"- Duplicate request ID count: {audit.get('duplicate_request_id_count', 0)}",
        f"- Model versions observed: {', '.join(audit.get('model_versions', [])) or 'N/A'}",
        "",
        "## Recommended Monitoring Actions",
        "",
        "- Treat any failed required-input check as a release blocker for automated scoring.",
        "- Treat failed critical-field quality checks as governance risks that require investigation before leadership reporting.",
        "- Investigate warning-level reference-range violations before using predictions in dashboards, because they indicate cases outside the original training envelope.",
        "- Escalate any PSI value at or above 0.20 for data science review before the next reporting cycle.",
        "- Compare monitored prediction drift with actual outcomes once labels are available; drift alone does not prove performance degradation.",
        "- Preserve audit summaries and model versions with each monitoring run so future investigations can reconstruct which model produced which prediction.",
        "",
        "## Output Artifacts",
        "",
        f"- `{summary['output_artifacts']['data_validation_report']}`",
        f"- `{summary['output_artifacts']['feature_drift_report']}`",
        f"- `{summary['output_artifacts']['prediction_drift_report']}`",
        f"- `{summary['output_artifacts']['audit_log_summary']}`",
        f"- `data_outputs/phase6/drift_detection_summary.json`",
        "",
        "## Reproduction Commands",
        "",
        "Run these commands from the project root using the same Python environment used for model training and API deployment:",
        "",
        "```bash",
        "python scripts/run_monitoring.py",
        "python scripts/create_phase6_reports.py",
        "```",
        "",
    ]
    path = DOCS_DIR / "Phase6_Drift_Detection_Report.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def create_governance_document() -> Path:
    summary, _, _, _, model_card = load_phase6_outputs()
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    model_overview = model_card.get("models", {})
    risk = model_overview.get("risk", {})
    claim = model_overview.get("claim", {})
    risk_artifact = risk.get("selected_model", {}).get("artifact", "models/risk_selected_model.joblib")
    claim_artifact = claim.get("selected_model", {}).get("artifact", "models/claim_selected_model.joblib")
    audit = summary["audit_log"]

    lines = [
        "# Phase 6 Governance and Compliance Document",
        "",
        f"Generated at UTC: {summary['generated_at_utc']}",
        "",
        "## Governance Objective",
        "",
        "The objective of Phase 6 is to keep the healthcare AI system reliable after deployment by validating incoming data, detecting feature and prediction drift, maintaining traceable audit metadata, and defining a controlled retraining strategy.",
        "",
        "## System Inventory",
        "",
        "| Component | Current Artifact or Version | Governance Purpose |",
        "| --- | --- | --- |",
        f"| Risk classification model | `{risk_artifact}` | Flags Low, Medium, or High visit risk for operational triage. |",
        f"| Claim outcome model | `{claim_artifact}` | Predicts Paid, Pending, or Rejected claim outcome for revenue-risk planning. |",
        "| API service | `src/healthcare_api/main.py` | Provides validated real-time scoring endpoints. |",
        "| Feature schema | `data_outputs/phase3/risk_feature_set.json`, `data_outputs/phase3/claim_feature_set.json` | Defines production model inputs and leakage exclusions. |",
        "| Monitoring runner | `scripts/run_monitoring.py` | Produces validation, drift, prediction, and audit summaries. |",
        "| Audit log | `logs/prediction_audit_log.jsonl` | Records prediction metadata with request ID, model version, prediction, probability payload, feature hash, and timestamp. |",
        "",
        "## Data Validation Controls",
        "",
        "- Required model inputs are checked for missing values before monitoring outputs are accepted.",
        "- Numeric features are checked against observed reference min/max values to identify records outside the original model envelope.",
        "- Business validity ranges are enforced for fields such as age, binary flags, billed amount, payment days, length of stay, months, weekdays, and rates.",
        "- Categorical features are compared against reference categories to detect unseen payer, city, department, visit type, gender, doctor, or age-band values.",
        "- Critical reliability fields from Phase 2, including approved amount, payment days, and length of stay, are monitored even when they are not all used as pre-submission model inputs.",
        "",
        "## Drift Monitoring Controls",
        "",
        f"- Feature drift status counts from the latest run: {count_text(summary['feature_drift']['severity_counts'])}.",
        f"- Prediction drift status counts from the latest run: {count_text(summary['prediction_drift']['severity_counts'])}.",
        "- PSI below 0.10 is stable, 0.10 to below 0.20 requires watch-list review, and 0.20 or higher requires drift investigation.",
        "- Risk predictions are monitored for shifts in High Risk prediction rate.",
        "- Claim predictions are monitored for shifts in Rejected claim prediction rate.",
        "- Drift alerts should be reviewed with hospital operations, billing leadership, and data science before changing model behavior.",
        "",
        "## Auditability and Traceability",
        "",
        f"- Latest audit-log availability: {audit['available']}.",
        f"- Latest audit-log record count: {audit['record_count']}.",
        f"- Model versions observed in audit log: {', '.join(audit.get('model_versions', [])) or 'N/A'}.",
        "- The API logs prediction metadata and a feature hash, not full raw payloads. This supports investigation while reducing exposure of sensitive input data in logs.",
        "- Audit logs should be retained according to the hospital's records policy and protected with access controls equivalent to other operational analytics logs.",
        "",
        "## Human Oversight Requirements",
        "",
        "- Predictions are decision-support signals, not autonomous clinical or billing decisions.",
        "- High Risk visit predictions should be reviewed by authorized operational or clinical staff before affecting prioritization.",
        "- Rejected claim predictions should be used to trigger finance review, not to deny or delay care.",
        "- Any model output challenged by staff should be logged, investigated, and reviewed during model governance meetings.",
        "",
        "## Known Limitations and Assumptions",
        "",
        "- The capstone data is historical and structured; it does not include free-text clinical notes, lab results, medication history, or real-time bed capacity.",
        "- Phase 4 found modest test performance, so the models should be treated as early decision-support prototypes.",
        "- Temporal anomalies such as visit-before-registration and billing-before-visit flags exist in the data and are explicitly monitored rather than silently discarded.",
        "- The current monitoring run uses the latest 20 percent of the historical data as a simulated current window. A production deployment should replace this with actual scored production records and delayed outcome labels.",
        "- Compliance readiness requires hospital security, privacy, legal, and clinical governance review before any real patient use.",
        "",
        "## Retraining Strategy",
        "",
        "- Run data validation daily for incoming scoring batches or API request aggregates.",
        "- Run feature and prediction drift checks weekly while volume is low, then daily when production volume is sufficient.",
        "- Recompute labeled performance monthly or whenever enough new outcomes arrive to create a statistically meaningful evaluation window.",
        "- Trigger retraining review if any core feature or prediction PSI is at or above 0.20 for two consecutive monitoring runs.",
        "- Trigger urgent review if High Risk recall or Rejected claim recall falls materially below the Phase 4 baseline after labels are available.",
        "- Retrain using the same leakage-safe feature policy from Phase 3, perform the Phase 4 evaluation and fairness review again, and publish a refreshed model card before promotion.",
        "- Promote a new model only after documented approval from data science, hospital operations, finance, and governance stakeholders.",
        "",
        "## Incident Response",
        "",
        "- Stop automated dashboard consumption if validation failures affect required fields or if an audit log is unavailable during production scoring.",
        "- Freeze model promotion if unseen categories indicate an upstream integration change that has not been mapped.",
        "- Notify stakeholders when drift status reaches the drift threshold, document root cause, and decide whether to recalibrate, retrain, or temporarily fall back to rules-based review.",
        "- Preserve the model artifact, feature schema, monitoring outputs, and audit summaries for every incident review.",
        "",
        "## Phase 6 Submission Artifacts",
        "",
        "- `scripts/run_monitoring.py`",
        "- `scripts/create_phase6_reports.py`",
        "- `data_outputs/phase6/data_validation_report.csv`",
        "- `data_outputs/phase6/feature_drift_report.csv`",
        "- `data_outputs/phase6/prediction_drift_report.csv`",
        "- `data_outputs/phase6/audit_log_summary.json`",
        "- `data_outputs/phase6/drift_detection_summary.json`",
        "- `docs/Phase6_Drift_Detection_Report.md`",
        "- `docs/Phase6_Governance_Compliance.md`",
        "",
        "## Reproduction Commands",
        "",
        "Run these commands from the project root using the same Python environment used for model training and API deployment:",
        "",
        "```bash",
        "python scripts/run_monitoring.py",
        "python scripts/create_phase6_reports.py",
        "```",
        "",
    ]
    path = DOCS_DIR / "Phase6_Governance_Compliance.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def main() -> None:
    drift_report = create_drift_report()
    governance_doc = create_governance_document()
    print(f"Created {drift_report.relative_to(PROJECT_ROOT)}")
    print(f"Created {governance_doc.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
