"""Create the Phase 1 SQL notebook as a reproducible JSON artifact."""

from __future__ import annotations

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_PATH = PROJECT_ROOT / "notebooks" / "Phase1_SQL.ipynb"


def markdown_cell(source: str) -> dict:
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": source.strip().splitlines(keepends=True),
    }


def code_cell(source: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": source.strip().splitlines(keepends=True),
    }


def build_notebook() -> dict:
    cells = [
        markdown_cell(
            """
            # Phase 1 - SQL Analytics Layer

            **Project:** Hospital Operations & Revenue Risk Intelligence Platform

            **Business goal:** Create a reliable, queryable hospital data layer that
            leadership can trust for operational and financial decision-making.

            This notebook uses the Phase 1 SQLite database created by
            `scripts/build_phase1_database.py`. It verifies the schema, joins,
            indexes, reusable KPI views, business queries, and data-quality checks.
            """
        ),
        code_cell(
            """
            from pathlib import Path
            import sqlite3
            import pandas as pd

            PROJECT_ROOT = Path.cwd()
            if PROJECT_ROOT.name == "notebooks":
                PROJECT_ROOT = PROJECT_ROOT.parent

            DB_PATH = PROJECT_ROOT / "database" / "hospital_operations.db"
            SQL_QUERY_PATH = PROJECT_ROOT / "sql" / "phase1_analysis_queries.sql"
            DB_PATH
            """
        ),
        code_cell(
            """
            conn = sqlite3.connect(DB_PATH)
            conn.execute("PRAGMA foreign_keys = ON")

            def sql(query: str) -> pd.DataFrame:
                return pd.read_sql_query(query, conn)
            """
        ),
        markdown_cell(
            """
            ## 1. Database Load Audit

            The raw source files are loaded into staging tables first, then inserted
            into typed relational tables with primary keys, foreign keys, constraints,
            and indexes.
            """
        ),
        code_cell(
            """
            sql("SELECT * FROM load_audit ORDER BY table_name")
            """
        ),
        code_cell(
            """
            sql(\"\"\"
            SELECT 'patients' AS table_name, COUNT(*) AS row_count FROM patients
            UNION ALL
            SELECT 'visits', COUNT(*) FROM visits
            UNION ALL
            SELECT 'billing', COUNT(*) FROM billing
            \"\"\")
            """
        ),
        markdown_cell(
            """
            ## 2. Relational Integrity

            These checks verify that visits link to valid patients and billing rows
            link to valid visits.
            """
        ),
        code_cell(
            """
            sql("PRAGMA foreign_key_check")
            """
        ),
        code_cell(
            """
            sql(\"\"\"
            SELECT
                'visits_without_patient' AS check_name,
                COUNT(*) AS issue_count
            FROM visits v
            LEFT JOIN patients p ON p.patient_id = v.patient_id
            WHERE p.patient_id IS NULL
            UNION ALL
            SELECT
                'billing_without_visit',
                COUNT(*)
            FROM billing b
            LEFT JOIN visits v ON v.visit_id = b.visit_id
            WHERE v.visit_id IS NULL
            UNION ALL
            SELECT
                'visits_without_billing',
                COUNT(*)
            FROM visits v
            LEFT JOIN billing b ON b.visit_id = v.visit_id
            WHERE b.visit_id IS NULL
            \"\"\")
            """
        ),
        markdown_cell(
            """
            ## 3. Operational Analysis

            These queries support patient flow and departmental efficiency decisions.
            """
        ),
        code_cell(
            """
            sql(\"\"\"
            SELECT * FROM v_department_kpis
            ORDER BY total_visits DESC
            \"\"\")
            """
        ),
        code_cell(
            """
            sql(\"\"\"
            SELECT
                doctor_id,
                COUNT(*) AS high_risk_visits
            FROM visits
            WHERE risk_score = 'High'
            GROUP BY doctor_id
            ORDER BY high_risk_visits DESC
            LIMIT 10
            \"\"\")
            """
        ),
        code_cell(
            """
            sql(\"\"\"
            SELECT * FROM v_city_patient_flow_kpis
            ORDER BY avg_visits_per_patient DESC
            \"\"\")
            """
        ),
        markdown_cell(
            """
            ## 4. Financial Analysis

            These queries support revenue leakage monitoring, insurer behavior
            analysis, payment delay tracking, and realization-ratio reporting.
            """
        ),
        code_cell(
            """
            sql(\"\"\"
            SELECT * FROM v_insurance_kpis
            ORDER BY total_billed_amount DESC
            \"\"\")
            """
        ),
        code_cell(
            """
            sql(\"\"\"
            SELECT
                department,
                total_billed_amount,
                total_approved_amount,
                revenue_realization_ratio
            FROM v_department_kpis
            ORDER BY revenue_realization_ratio DESC
            \"\"\")
            """
        ),
        code_cell(
            """
            sql(\"\"\"
            WITH ranked_claims AS (
                SELECT
                    b.bill_id,
                    b.visit_id,
                    v.department,
                    p.insurance_provider,
                    b.billed_amount,
                    b.approved_amount,
                    b.claim_status,
                    NTILE(20) OVER (ORDER BY b.billed_amount) AS billed_amount_twentieth
                FROM billing b
                JOIN visits v ON v.visit_id = b.visit_id
                JOIN patients p ON p.patient_id = v.patient_id
            )
            SELECT *
            FROM ranked_claims
            WHERE billed_amount_twentieth = 20
              AND (approved_amount IS NULL OR approved_amount = 0)
            ORDER BY billed_amount DESC
            LIMIT 20
            \"\"\")
            """
        ),
        markdown_cell(
            """
            ## 5. Data Quality and Integrity Checks

            These checks are intentionally preserved as reusable SQL views so the same
            logic can be reused in Phase 2 EDA and Phase 6 monitoring.
            """
        ),
        code_cell(
            """
            sql("SELECT * FROM v_quality_summary")
            """
        ),
        code_cell(
            """
            sql(\"\"\"
            SELECT *
            FROM v_quality_temporal_anomalies
            LIMIT 20
            \"\"\")
            """
        ),
        markdown_cell(
            """
            ## 6. Index Strategy

            The main indexes support:

            - Department volume, average LOS, and high-risk rate:
              `idx_visits_department`, `idx_visits_department_risk`
            - High-risk doctor workload:
              `idx_visits_doctor_risk`
            - Patient flow by city and provider:
              `idx_patients_city`, `idx_patients_insurance_provider`,
              `idx_visits_patient_id`
            - Claim status, payment delay, and billing amount queries:
              `idx_billing_claim_status`, `idx_billing_payment_days`,
              `idx_billing_billed_amount`, `idx_billing_claim_payment`
            - Time-based downstream modeling and audits:
              `idx_visits_visit_date`, `idx_billing_billing_date`,
              `idx_patients_registration_date`
            """
        ),
        code_cell(
            """
            sql(\"\"\"
            SELECT
                name AS index_name,
                tbl_name AS table_name,
                sql AS index_sql
            FROM sqlite_master
            WHERE type = 'index'
              AND sql IS NOT NULL
            ORDER BY table_name, index_name
            \"\"\")
            """
        ),
    ]

    return {
        "cells": cells,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {
                "name": "python",
                "version": "3.11",
            },
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def main() -> None:
    NOTEBOOK_PATH.parent.mkdir(parents=True, exist_ok=True)
    notebook = build_notebook()
    NOTEBOOK_PATH.write_text(json.dumps(notebook, indent=2), encoding="utf-8")
    print(f"Wrote notebook: {NOTEBOOK_PATH}")


if __name__ == "__main__":
    main()
