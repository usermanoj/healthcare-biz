"""Build Phase 2 EDA outputs and a modeling-ready feature table.

Inputs:
    database/hospital_operations.db

Outputs:
    data_outputs/model_table.csv
    data_outputs/feature_schema.json
    data_outputs/phase2/*.csv and *.json

The script intentionally starts from the Phase 1 SQL view
`v_hospital_encounters` so Phase 2 remains connected to the validated SQL layer.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATABASE_PATH = PROJECT_ROOT / "database" / "hospital_operations.db"
OUTPUT_ROOT = PROJECT_ROOT / "data_outputs"
PHASE2_OUTPUT_DIR = OUTPUT_ROOT / "phase2"
MODEL_TABLE_PATH = OUTPUT_ROOT / "model_table.csv"
FEATURE_SCHEMA_PATH = OUTPUT_ROOT / "feature_schema.json"


DATE_COLUMNS = ["registration_date", "visit_date", "billing_date"]
OUTLIER_COLUMNS = ["billed_amount", "payment_days", "length_of_stay_hours"]
DISTRIBUTION_COLUMNS = ["department", "visit_type", "insurance_provider", "city"]


def load_encounters() -> pd.DataFrame:
    if not DATABASE_PATH.exists():
        raise FileNotFoundError(
            f"Phase 1 database not found: {DATABASE_PATH}. "
            "Run scripts/build_phase1_database.py first."
        )

    conn = sqlite3.connect(DATABASE_PATH)
    try:
        df = pd.read_sql_query("SELECT * FROM v_hospital_encounters", conn)
    finally:
        conn.close()

    for col in DATE_COLUMNS:
        df[col] = pd.to_datetime(df[col], errors="coerce")

    return df


def outlier_category(series: pd.Series) -> tuple[pd.Series, dict[str, float | int]]:
    numeric = pd.to_numeric(series, errors="coerce")
    q1 = numeric.quantile(0.25)
    q3 = numeric.quantile(0.75)
    iqr = q3 - q1
    mild_low = q1 - 1.5 * iqr
    mild_high = q3 + 1.5 * iqr
    extreme_low = q1 - 3.0 * iqr
    extreme_high = q3 + 3.0 * iqr

    categories = pd.Series("normal", index=series.index, dtype="object")
    categories[numeric.isna()] = "missing"
    categories[(numeric < mild_low) & (numeric >= extreme_low)] = "mild_low"
    categories[(numeric > mild_high) & (numeric <= extreme_high)] = "mild_high"
    categories[numeric < extreme_low] = "extreme_low"
    categories[numeric > extreme_high] = "extreme_high"

    metadata = {
        "q1": round(float(q1), 6) if pd.notna(q1) else None,
        "q3": round(float(q3), 6) if pd.notna(q3) else None,
        "iqr": round(float(iqr), 6) if pd.notna(iqr) else None,
        "mild_low_threshold": round(float(mild_low), 6) if pd.notna(mild_low) else None,
        "mild_high_threshold": round(float(mild_high), 6) if pd.notna(mild_high) else None,
        "extreme_low_threshold": round(float(extreme_low), 6) if pd.notna(extreme_low) else None,
        "extreme_high_threshold": round(float(extreme_high), 6) if pd.notna(extreme_high) else None,
    }
    return categories, metadata


def add_patient_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values(["patient_id", "visit_date", "visit_id"]).copy()

    patient_group = df.groupby("patient_id", dropna=False)
    df["patient_total_visits"] = patient_group["visit_id"].transform("count")
    df["patient_avg_los_hours"] = patient_group["length_of_stay_hours"].transform("mean")

    # Time-aware historical features. These are safer candidates for Phase 3 than
    # all-history patient aggregates because they only use earlier visits.
    df["patient_prior_visit_count"] = patient_group.cumcount()
    prior_los_sum = patient_group["length_of_stay_hours"].cumsum() - df["length_of_stay_hours"]
    df["patient_prior_avg_los_hours"] = np.where(
        df["patient_prior_visit_count"] > 0,
        prior_los_sum / df["patient_prior_visit_count"],
        np.nan,
    )
    df["patient_prior_avg_los_missing_flag"] = (
        df["patient_prior_avg_los_hours"].isna().astype(int)
    )
    df["patient_prior_avg_los_hours"] = df["patient_prior_avg_los_hours"].fillna(
        df["length_of_stay_hours"].median()
    )

    return df


def add_provider_features(df: pd.DataFrame) -> pd.DataFrame:
    provider_group = df.groupby("insurance_provider", dropna=False)
    df["provider_total_claims"] = provider_group["visit_id"].transform("count")
    df["provider_rejected_claims"] = provider_group["claim_status"].transform(
        lambda s: s.eq("Rejected").sum()
    )
    df["provider_rejection_rate"] = (
        df["provider_rejected_claims"] / df["provider_total_claims"]
    )

    ordered = df.sort_values(["insurance_provider", "billing_date", "bill_id"]).copy()
    g = ordered.groupby("insurance_provider", dropna=False)
    ordered["provider_prior_claim_count"] = g.cumcount()
    prior_rejected = g["claim_status"].transform(lambda s: s.eq("Rejected").cumsum())
    ordered["provider_prior_rejected_count"] = prior_rejected - ordered["claim_status"].eq(
        "Rejected"
    ).astype(int)
    ordered["provider_prior_rejection_rate"] = np.where(
        ordered["provider_prior_claim_count"] > 0,
        ordered["provider_prior_rejected_count"] / ordered["provider_prior_claim_count"],
        np.nan,
    )
    overall_rejection_rate = df["claim_status"].eq("Rejected").mean()
    ordered["provider_prior_rejection_missing_flag"] = (
        ordered["provider_prior_rejection_rate"].isna().astype(int)
    )
    ordered["provider_prior_rejection_rate"] = ordered[
        "provider_prior_rejection_rate"
    ].fillna(overall_rejection_rate)

    return ordered.sort_values("visit_id")


def add_department_features(df: pd.DataFrame) -> pd.DataFrame:
    department_group = df.groupby("department", dropna=False)
    df["department_avg_los_hours"] = department_group["length_of_stay_hours"].transform(
        "mean"
    )
    df["department_high_risk_rate"] = department_group["risk_score"].transform(
        lambda s: s.eq("High").mean()
    )
    df["department_revenue_realization_ratio"] = department_group.apply(
        lambda g: g["approved_amount"].fillna(0).sum() / g["billed_amount"].sum()
    ).reindex(df["department"]).to_numpy()
    return df


def add_date_features(df: pd.DataFrame) -> pd.DataFrame:
    df["days_since_registration"] = (
        df["visit_date"] - df["registration_date"]
    ).dt.days
    df["billing_lag_days"] = (df["billing_date"] - df["visit_date"]).dt.days

    df["visit_before_registration_flag"] = (
        df["days_since_registration"] < 0
    ).astype(int)
    df["billing_before_visit_flag"] = (df["billing_lag_days"] < 0).astype(int)
    df["same_day_billing_flag"] = (df["billing_lag_days"] == 0).astype(int)

    df["visit_year"] = df["visit_date"].dt.year
    df["visit_month"] = df["visit_date"].dt.month
    df["visit_quarter"] = df["visit_date"].dt.quarter
    df["visit_day_of_week"] = df["visit_date"].dt.dayofweek
    df["visit_week_of_year"] = df["visit_date"].dt.isocalendar().week.astype(int)
    df["visit_is_weekend"] = df["visit_day_of_week"].isin([5, 6]).astype(int)

    df["billing_year"] = df["billing_date"].dt.year
    df["billing_month"] = df["billing_date"].dt.month
    df["billing_day_of_week"] = df["billing_date"].dt.dayofweek
    return df


def add_financial_features(df: pd.DataFrame) -> pd.DataFrame:
    df["approved_amount_missing_flag"] = df["approved_amount"].isna().astype(int)
    df["payment_days_missing_flag"] = df["payment_days"].isna().astype(int)
    df["length_of_stay_missing_flag"] = df["length_of_stay_hours"].isna().astype(int)
    df["approved_amount_zero_flag"] = df["approved_amount"].fillna(0).eq(0).astype(int)
    df["approved_amount_zero_or_missing_flag"] = (
        df["approved_amount"].isna() | df["approved_amount"].eq(0)
    ).astype(int)

    df["approved_to_billed_ratio"] = np.where(
        df["billed_amount"] > 0,
        df["approved_amount"].fillna(0) / df["billed_amount"],
        np.nan,
    )
    df["revenue_gap_amount"] = df["billed_amount"] - df["approved_amount"].fillna(0)
    df["claim_rejected_flag"] = df["claim_status"].eq("Rejected").astype(int)
    df["claim_pending_flag"] = df["claim_status"].eq("Pending").astype(int)
    df["high_risk_flag"] = df["risk_score"].eq("High").astype(int)
    df["chronic_flag"] = df["chronic_flag"].astype(int)

    high_bill_threshold = df["billed_amount"].quantile(0.95)
    df["high_billed_amount_flag"] = (df["billed_amount"] >= high_bill_threshold).astype(int)
    df["high_billed_zero_or_missing_approved_flag"] = (
        df["high_billed_amount_flag"].eq(1)
        & df["approved_amount_zero_or_missing_flag"].eq(1)
    ).astype(int)
    return df


def add_outlier_features(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    summary_rows = []
    for col in OUTLIER_COLUMNS:
        categories, metadata = outlier_category(df[col])
        category_col = f"{col}_outlier_category"
        flag_col = f"{col}_outlier_flag"
        df[category_col] = categories
        df[flag_col] = categories.isin(
            ["mild_low", "mild_high", "extreme_low", "extreme_high"]
        ).astype(int)

        counts = categories.value_counts(dropna=False).to_dict()
        summary_row = {"field_name": col, **metadata}
        for category in [
            "normal",
            "missing",
            "mild_low",
            "mild_high",
            "extreme_low",
            "extreme_high",
        ]:
            summary_row[f"{category}_count"] = int(counts.get(category, 0))
        summary_row["outlier_count"] = int(summary_row["mild_low_count"] + summary_row["mild_high_count"] + summary_row["extreme_low_count"] + summary_row["extreme_high_count"])
        summary_row["outlier_pct"] = round(100 * summary_row["outlier_count"] / len(df), 2)
        summary_rows.append(summary_row)

    return df, pd.DataFrame(summary_rows)


def build_feature_table(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = add_patient_features(df)
    df = add_provider_features(df)
    df = add_department_features(df)
    df = add_date_features(df)
    df = add_financial_features(df)
    df, outlier_summary = add_outlier_features(df)

    df["age_band"] = pd.cut(
        df["age"],
        bins=[0, 17, 35, 50, 65, 120],
        labels=["0-17", "18-35", "36-50", "51-65", "66+"],
        include_lowest=True,
    ).astype(str)

    # Stable output ordering helps future model training and reviews.
    ordered_columns = [
        "visit_id",
        "patient_id",
        "bill_id",
        "doctor_id",
        "age",
        "age_band",
        "gender",
        "city",
        "insurance_provider",
        "chronic_flag",
        "registration_date",
        "visit_date",
        "billing_date",
        "department",
        "visit_type",
        "length_of_stay_hours",
        "billed_amount",
        "approved_amount",
        "payment_days",
        "risk_score",
        "claim_status",
        "patient_total_visits",
        "patient_avg_los_hours",
        "patient_prior_visit_count",
        "patient_prior_avg_los_hours",
        "patient_prior_avg_los_missing_flag",
        "provider_total_claims",
        "provider_rejected_claims",
        "provider_rejection_rate",
        "provider_prior_claim_count",
        "provider_prior_rejected_count",
        "provider_prior_rejection_rate",
        "provider_prior_rejection_missing_flag",
        "department_avg_los_hours",
        "department_high_risk_rate",
        "department_revenue_realization_ratio",
        "days_since_registration",
        "billing_lag_days",
        "visit_before_registration_flag",
        "billing_before_visit_flag",
        "same_day_billing_flag",
        "visit_year",
        "visit_month",
        "visit_quarter",
        "visit_day_of_week",
        "visit_week_of_year",
        "visit_is_weekend",
        "billing_year",
        "billing_month",
        "billing_day_of_week",
        "approved_amount_missing_flag",
        "payment_days_missing_flag",
        "length_of_stay_missing_flag",
        "approved_amount_zero_flag",
        "approved_amount_zero_or_missing_flag",
        "approved_to_billed_ratio",
        "revenue_gap_amount",
        "claim_rejected_flag",
        "claim_pending_flag",
        "high_risk_flag",
        "high_billed_amount_flag",
        "high_billed_zero_or_missing_approved_flag",
        "billed_amount_outlier_category",
        "billed_amount_outlier_flag",
        "payment_days_outlier_category",
        "payment_days_outlier_flag",
        "length_of_stay_hours_outlier_category",
        "length_of_stay_hours_outlier_flag",
        "visit_realization_ratio",
    ]
    return df[ordered_columns].sort_values("visit_id"), outlier_summary


def missing_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for col in ["approved_amount", "payment_days", "length_of_stay_hours"]:
        rows.append(
            {
                "field_name": col,
                "missing_count": int(df[col].isna().sum()),
                "missing_pct": round(float(df[col].isna().mean() * 100), 2),
                "zero_count": int(df[col].fillna(np.nan).eq(0).sum()),
                "non_missing_count": int(df[col].notna().sum()),
            }
        )
    return pd.DataFrame(rows)


def numeric_summary(df: pd.DataFrame, columns: Iterable[str]) -> pd.DataFrame:
    rows = []
    for col in columns:
        s = pd.to_numeric(df[col], errors="coerce")
        rows.append(
            {
                "field_name": col,
                "count": int(s.count()),
                "missing_count": int(s.isna().sum()),
                "mean": round(float(s.mean()), 4) if s.count() else None,
                "std": round(float(s.std()), 4) if s.count() else None,
                "min": round(float(s.min()), 4) if s.count() else None,
                "p25": round(float(s.quantile(0.25)), 4) if s.count() else None,
                "median": round(float(s.median()), 4) if s.count() else None,
                "p75": round(float(s.quantile(0.75)), 4) if s.count() else None,
                "p95": round(float(s.quantile(0.95)), 4) if s.count() else None,
                "p99": round(float(s.quantile(0.99)), 4) if s.count() else None,
                "max": round(float(s.max()), 4) if s.count() else None,
            }
        )
    return pd.DataFrame(rows)


def distribution_table(df: pd.DataFrame, column: str) -> pd.DataFrame:
    grouped = (
        df.groupby(column, dropna=False)
        .agg(
            visit_count=("visit_id", "count"),
            patient_count=("patient_id", "nunique"),
            avg_los_hours=("length_of_stay_hours", "mean"),
            high_risk_rate=("risk_score", lambda s: s.eq("High").mean()),
            rejected_claim_rate=("claim_status", lambda s: s.eq("Rejected").mean()),
            avg_payment_days=("payment_days", "mean"),
            total_billed_amount=("billed_amount", "sum"),
            total_approved_amount=("approved_amount", lambda s: s.fillna(0).sum()),
        )
        .reset_index()
    )
    grouped["visit_pct"] = grouped["visit_count"] / len(df)
    grouped["revenue_realization_ratio"] = (
        grouped["total_approved_amount"] / grouped["total_billed_amount"]
    )

    numeric_cols = grouped.select_dtypes(include=["float", "float64"]).columns
    grouped[numeric_cols] = grouped[numeric_cols].round(4)
    return grouped.sort_values("visit_count", ascending=False)


def temporal_quality_summary(model_table: pd.DataFrame) -> pd.DataFrame:
    checks = [
        {
            "quality_check": "visit_before_registration",
            "issue_count": int(model_table["visit_before_registration_flag"].sum()),
            "issue_pct": round(float(model_table["visit_before_registration_flag"].mean() * 100), 2),
        },
        {
            "quality_check": "billing_before_visit",
            "issue_count": int(model_table["billing_before_visit_flag"].sum()),
            "issue_pct": round(float(model_table["billing_before_visit_flag"].mean() * 100), 2),
        },
        {
            "quality_check": "same_day_billing",
            "issue_count": int(model_table["same_day_billing_flag"].sum()),
            "issue_pct": round(float(model_table["same_day_billing_flag"].mean() * 100), 2),
        },
        {
            "quality_check": "high_billed_zero_or_missing_approved",
            "issue_count": int(model_table["high_billed_zero_or_missing_approved_flag"].sum()),
            "issue_pct": round(float(model_table["high_billed_zero_or_missing_approved_flag"].mean() * 100), 2),
        },
    ]
    return pd.DataFrame(checks)


def write_feature_schema(model_table: pd.DataFrame, profile: dict[str, object]) -> None:
    schema = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_database": str(DATABASE_PATH),
        "source_view": "v_hospital_encounters",
        "model_table": str(MODEL_TABLE_PATH),
        "row_count": int(len(model_table)),
        "column_count": int(model_table.shape[1]),
        "targets": {
            "risk_model_target": "risk_score",
            "claim_model_target": "claim_status",
        },
        "identifier_columns": ["visit_id", "patient_id", "bill_id", "doctor_id"],
        "raw_date_columns": ["registration_date", "visit_date", "billing_date"],
        "raw_categorical_columns": [
            "gender",
            "city",
            "insurance_provider",
            "department",
            "visit_type",
            "age_band",
        ],
        "raw_numeric_columns": [
            "age",
            "chronic_flag",
            "length_of_stay_hours",
            "billed_amount",
            "approved_amount",
            "payment_days",
        ],
        "engineered_feature_columns": [
            "patient_total_visits",
            "patient_avg_los_hours",
            "patient_prior_visit_count",
            "patient_prior_avg_los_hours",
            "provider_total_claims",
            "provider_rejected_claims",
            "provider_rejection_rate",
            "provider_prior_claim_count",
            "provider_prior_rejected_count",
            "provider_prior_rejection_rate",
            "department_avg_los_hours",
            "department_high_risk_rate",
            "department_revenue_realization_ratio",
            "days_since_registration",
            "billing_lag_days",
            "visit_year",
            "visit_month",
            "visit_quarter",
            "visit_day_of_week",
            "visit_week_of_year",
            "visit_is_weekend",
            "billing_year",
            "billing_month",
            "billing_day_of_week",
            "approved_to_billed_ratio",
            "revenue_gap_amount",
        ],
        "data_quality_flag_columns": [
            "patient_prior_avg_los_missing_flag",
            "provider_prior_rejection_missing_flag",
            "visit_before_registration_flag",
            "billing_before_visit_flag",
            "same_day_billing_flag",
            "approved_amount_missing_flag",
            "payment_days_missing_flag",
            "length_of_stay_missing_flag",
            "approved_amount_zero_flag",
            "approved_amount_zero_or_missing_flag",
            "high_billed_amount_flag",
            "high_billed_zero_or_missing_approved_flag",
            "billed_amount_outlier_flag",
            "payment_days_outlier_flag",
            "length_of_stay_hours_outlier_flag",
        ],
        "leakage_sensitive_columns": {
            "for_risk_model": [
                "risk_score",
                "high_risk_flag",
                "claim_status",
                "claim_rejected_flag",
                "claim_pending_flag",
                "approved_amount",
                "payment_days",
                "approved_to_billed_ratio",
                "revenue_gap_amount",
                "visit_realization_ratio",
            ],
            "for_claim_model": [
                "claim_status",
                "claim_rejected_flag",
                "claim_pending_flag",
                "approved_amount",
                "payment_days",
                "approved_to_billed_ratio",
                "revenue_gap_amount",
                "visit_realization_ratio",
                "provider_rejection_rate",
                "provider_rejected_claims",
            ],
        },
        "notes": [
            "provider_rejection_rate and provider_rejected_claims are useful EDA features but must be recomputed using training data only before claim-outcome modeling.",
            "approved_amount and payment_days are post-outcome fields for claim prediction and should not be predictors for a pre-submission claim model.",
            "Temporal anomaly flags are retained because Phase 1 found visit-before-registration and billing-before-visit records.",
        ],
        "profile": profile,
        "columns": {
            col: {
                "dtype": str(model_table[col].dtype),
                "missing_count": int(model_table[col].isna().sum()),
            }
            for col in model_table.columns
        },
    }
    FEATURE_SCHEMA_PATH.write_text(json.dumps(schema, indent=2), encoding="utf-8")


def main() -> None:
    PHASE2_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    encounters = load_encounters()
    model_table, outlier_summary = build_feature_table(encounters)

    missing = missing_summary(model_table)
    numeric = numeric_summary(
        model_table,
        [
            "age",
            "length_of_stay_hours",
            "billed_amount",
            "approved_amount",
            "payment_days",
            "days_since_registration",
            "billing_lag_days",
            "patient_total_visits",
            "patient_prior_visit_count",
            "provider_rejection_rate",
            "provider_prior_rejection_rate",
        ],
    )
    temporal_quality = temporal_quality_summary(model_table)

    MODEL_TABLE_PATH.parent.mkdir(parents=True, exist_ok=True)
    model_table.to_csv(MODEL_TABLE_PATH, index=False)
    model_table.to_csv(PHASE2_OUTPUT_DIR / "model_table.csv", index=False)

    missing.to_csv(PHASE2_OUTPUT_DIR / "missing_values_summary.csv", index=False)
    numeric.to_csv(PHASE2_OUTPUT_DIR / "numeric_summary.csv", index=False)
    outlier_summary.to_csv(PHASE2_OUTPUT_DIR / "outlier_summary.csv", index=False)
    temporal_quality.to_csv(PHASE2_OUTPUT_DIR / "temporal_quality_summary.csv", index=False)

    outlier_cols = [
        "visit_id",
        "patient_id",
        "department",
        "insurance_provider",
        "billed_amount",
        "payment_days",
        "length_of_stay_hours",
        "billed_amount_outlier_category",
        "payment_days_outlier_category",
        "length_of_stay_hours_outlier_category",
    ]
    outlier_mask = (
        model_table["billed_amount_outlier_flag"].eq(1)
        | model_table["payment_days_outlier_flag"].eq(1)
        | model_table["length_of_stay_hours_outlier_flag"].eq(1)
    )
    model_table.loc[outlier_mask, outlier_cols].head(500).to_csv(
        PHASE2_OUTPUT_DIR / "outlier_records_sample.csv", index=False
    )

    for column in DISTRIBUTION_COLUMNS:
        distribution_table(model_table, column).to_csv(
            PHASE2_OUTPUT_DIR / f"distribution_by_{column}.csv", index=False
        )

    profile = {
        "encounter_rows": int(len(encounters)),
        "model_table_rows": int(len(model_table)),
        "model_table_columns": int(model_table.shape[1]),
        "risk_score_distribution": {
            str(k): int(v)
            for k, v in model_table["risk_score"].value_counts().sort_index().items()
        },
        "claim_status_distribution": {
            str(k): int(v)
            for k, v in model_table["claim_status"].value_counts().sort_index().items()
        },
        "missing_approved_amount_count": int(model_table["approved_amount"].isna().sum()),
        "missing_payment_days_count": int(model_table["payment_days"].isna().sum()),
        "missing_length_of_stay_count": int(model_table["length_of_stay_hours"].isna().sum()),
        "visit_before_registration_count": int(
            model_table["visit_before_registration_flag"].sum()
        ),
        "billing_before_visit_count": int(model_table["billing_before_visit_flag"].sum()),
        "high_billed_zero_or_missing_approved_count": int(
            model_table["high_billed_zero_or_missing_approved_flag"].sum()
        ),
        "total_billed_amount": round(float(model_table["billed_amount"].sum()), 2),
        "total_approved_amount": round(float(model_table["approved_amount"].fillna(0).sum()), 2),
        "overall_revenue_realization_ratio": round(
            float(model_table["approved_amount"].fillna(0).sum() / model_table["billed_amount"].sum()),
            6,
        ),
    }
    (PHASE2_OUTPUT_DIR / "phase2_eda_profile.json").write_text(
        json.dumps(profile, indent=2), encoding="utf-8"
    )
    write_feature_schema(model_table, profile)

    print(f"Wrote model table: {MODEL_TABLE_PATH}")
    print(f"Wrote feature schema: {FEATURE_SCHEMA_PATH}")
    print(f"Wrote Phase 2 outputs: {PHASE2_OUTPUT_DIR}")
    print(json.dumps(profile, indent=2))


if __name__ == "__main__":
    main()
