"""Create the Phase 2 EDA notebook artifact."""

from __future__ import annotations

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_PATH = PROJECT_ROOT / "notebooks" / "01_eda.ipynb"


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
            # Phase 2 - Exploratory Data Analysis & Data Quality

            **Project:** Hospital Operations & Revenue Risk Intelligence Platform

            **Business goal:** Understand hospital operations, financial
            performance, and data reliability before deploying AI models.

            This notebook starts from the Phase 1 SQL database and the
            modeling-ready table created by `scripts/build_features.py`.
            """
        ),
        code_cell(
            """
            from pathlib import Path
            import json
            import sqlite3
            import pandas as pd
            import numpy as np
            import matplotlib.pyplot as plt

            PROJECT_ROOT = Path.cwd()
            if PROJECT_ROOT.name == "notebooks":
                PROJECT_ROOT = PROJECT_ROOT.parent

            DB_PATH = PROJECT_ROOT / "database" / "hospital_operations.db"
            PHASE2_DIR = PROJECT_ROOT / "data_outputs" / "phase2"
            MODEL_TABLE_PATH = PROJECT_ROOT / "data_outputs" / "model_table.csv"
            FEATURE_SCHEMA_PATH = PROJECT_ROOT / "data_outputs" / "feature_schema.json"
            """
        ),
        markdown_cell(
            """
            ## 1. Load Combined Data

            The combined encounter table is loaded from the Phase 1 SQL view
            `v_hospital_encounters`. The modeling table is the engineered Phase 2
            output.
            """
        ),
        code_cell(
            """
            conn = sqlite3.connect(DB_PATH)
            encounters = pd.read_sql_query("SELECT * FROM v_hospital_encounters", conn)
            conn.close()

            model_table = pd.read_csv(MODEL_TABLE_PATH)
            print(encounters.shape)
            print(model_table.shape)
            model_table.head()
            """
        ),
        markdown_cell(
            """
            ## 2. Missing Value Analysis

            Required fields: `approved_amount`, `payment_days`, and
            `length_of_stay_hours`.
            """
        ),
        code_cell(
            """
            missing_summary = pd.read_csv(PHASE2_DIR / "missing_values_summary.csv")
            missing_summary
            """
        ),
        code_cell(
            """
            missing_summary.plot(
                x="field_name",
                y="missing_pct",
                kind="bar",
                legend=False,
                title="Missing Value Percentage by Critical Field",
                ylabel="Missing %",
                xlabel="Field",
            )
            plt.xticks(rotation=0)
            plt.tight_layout()
            """
        ),
        markdown_cell(
            """
            ## 3. Distribution Analysis

            Distribution summaries are produced for department, visit type,
            insurance provider, and city. Each table includes volume, patient
            count, average LOS, high-risk rate, rejection rate, payment delay, and
            realization ratio.
            """
        ),
        code_cell(
            """
            distribution_files = {
                "department": PHASE2_DIR / "distribution_by_department.csv",
                "visit_type": PHASE2_DIR / "distribution_by_visit_type.csv",
                "insurance_provider": PHASE2_DIR / "distribution_by_insurance_provider.csv",
                "city": PHASE2_DIR / "distribution_by_city.csv",
            }
            distributions = {name: pd.read_csv(path) for name, path in distribution_files.items()}
            distributions["department"]
            """
        ),
        code_cell(
            """
            distributions["insurance_provider"]
            """
        ),
        code_cell(
            """
            distributions["city"]
            """
        ),
        code_cell(
            """
            ax = distributions["department"].sort_values("visit_count").plot(
                x="department",
                y="visit_count",
                kind="barh",
                legend=False,
                title="Visit Volume by Department",
                xlabel="Visit Count",
                ylabel="Department",
            )
            plt.tight_layout()
            """
        ),
        markdown_cell(
            """
            ## 4. Outlier Detection

            Outliers are classified using IQR thresholds:

            - mild outlier: beyond 1.5 x IQR
            - extreme outlier: beyond 3.0 x IQR
            - missing: field is null

            Required fields: `billed_amount`, `payment_days`, and
            `length_of_stay_hours`.
            """
        ),
        code_cell(
            """
            outlier_summary = pd.read_csv(PHASE2_DIR / "outlier_summary.csv")
            outlier_summary
            """
        ),
        code_cell(
            """
            pd.read_csv(PHASE2_DIR / "outlier_records_sample.csv").head(20)
            """
        ),
        markdown_cell(
            """
            ## 5. Engineered Features

            The modeling table includes:

            - patient visit frequency
            - patient average LOS
            - prior visit count and prior average LOS
            - provider rejection rate and prior rejection rate
            - days since registration
            - billing lag days
            - date parts for visit and billing dates
            - missingness, temporal anomaly, and outlier flags
            """
        ),
        code_cell(
            """
            with FEATURE_SCHEMA_PATH.open("r", encoding="utf-8") as handle:
                feature_schema = json.load(handle)

            feature_schema["row_count"], feature_schema["column_count"], feature_schema["targets"]
            """
        ),
        code_cell(
            """
            model_table[
                [
                    "visit_id",
                    "patient_total_visits",
                    "patient_prior_visit_count",
                    "patient_avg_los_hours",
                    "provider_rejection_rate",
                    "provider_prior_rejection_rate",
                    "days_since_registration",
                    "billing_lag_days",
                    "visit_month",
                    "visit_day_of_week",
                ]
            ].head()
            """
        ),
        markdown_cell(
            """
            ## 6. Target Readiness

            Phase 3 will use `risk_score` as the visit-risk classification target
            and `claim_status` as the claim-outcome classification target. The
            feature schema marks leakage-sensitive fields so the modeling phase can
            exclude post-outcome fields correctly.
            """
        ),
        code_cell(
            """
            print("Risk target distribution")
            display(model_table["risk_score"].value_counts(normalize=True).mul(100).round(2))

            print("Claim target distribution")
            display(model_table["claim_status"].value_counts(normalize=True).mul(100).round(2))
            """
        ),
        code_cell(
            """
            feature_schema["leakage_sensitive_columns"]
            """
        ),
        markdown_cell(
            """
            ## 7. Data Quality Summary

            Temporal anomalies are retained as flags. They should be interpreted as
            data reliability risks rather than silently corrected.
            """
        ),
        code_cell(
            """
            pd.read_csv(PHASE2_DIR / "temporal_quality_summary.csv")
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
    NOTEBOOK_PATH.write_text(json.dumps(build_notebook(), indent=2), encoding="utf-8")
    print(f"Wrote notebook: {NOTEBOOK_PATH}")


if __name__ == "__main__":
    main()
