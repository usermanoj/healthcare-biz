"""Build the Phase 1 SQLite analytics database from the source CSV files.

The script creates a raw staging layer, loads the source CSV files unchanged,
then inserts typed records into constrained business tables. This gives Phase 1
both a trustworthy analytics schema and a raw layer for duplicate/source checks.
"""

from __future__ import annotations

import csv
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SQL_DIR = PROJECT_ROOT / "sql"
DATABASE_DIR = PROJECT_ROOT / "database"
OUTPUT_DIR = PROJECT_ROOT / "data_outputs" / "phase1"

DATABASE_PATH = DATABASE_DIR / "hospital_operations.db"

SOURCE_FILES = {
    "raw_patients": PROJECT_ROOT / "patients.csv",
    "raw_visits": PROJECT_ROOT / "visits.csv",
    "raw_billing": PROJECT_ROOT / "billing.csv",
}


def execute_sql_file(conn: sqlite3.Connection, sql_path: Path) -> None:
    conn.executescript(sql_path.read_text(encoding="utf-8"))


def load_csv(conn: sqlite3.Connection, table_name: str, csv_path: Path) -> int:
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"{csv_path} has no header row")
        columns = reader.fieldnames
        placeholders = ", ".join(["?"] * len(columns))
        quoted_columns = ", ".join(columns)
        sql = f"INSERT INTO {table_name} ({quoted_columns}) VALUES ({placeholders})"
        rows = [[row[col] for col in columns] for row in reader]

    conn.executemany(sql, rows)
    return len(rows)


def insert_typed_tables(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        INSERT INTO patients (
            patient_id,
            age,
            gender,
            city,
            insurance_provider,
            chronic_flag,
            registration_date
        )
        SELECT
            CAST(patient_id AS INTEGER),
            CAST(age AS INTEGER),
            TRIM(gender),
            TRIM(city),
            NULLIF(TRIM(insurance_provider), ''),
            CAST(chronic_flag AS INTEGER),
            TRIM(registration_date)
        FROM raw_patients;

        INSERT INTO visits (
            visit_id,
            patient_id,
            visit_date,
            department,
            visit_type,
            length_of_stay_hours,
            risk_score,
            doctor_id
        )
        SELECT
            CAST(visit_id AS INTEGER),
            CAST(patient_id AS INTEGER),
            TRIM(visit_date),
            TRIM(department),
            TRIM(visit_type),
            CAST(length_of_stay_hours AS REAL),
            TRIM(risk_score),
            CAST(doctor_id AS INTEGER)
        FROM raw_visits;

        INSERT INTO billing (
            bill_id,
            visit_id,
            billed_amount,
            approved_amount,
            claim_status,
            payment_days,
            billing_date
        )
        SELECT
            CAST(bill_id AS INTEGER),
            CAST(visit_id AS INTEGER),
            CAST(billed_amount AS REAL),
            CASE
                WHEN TRIM(COALESCE(approved_amount, '')) = '' THEN NULL
                ELSE CAST(approved_amount AS REAL)
            END,
            TRIM(claim_status),
            CASE
                WHEN TRIM(COALESCE(payment_days, '')) = '' THEN NULL
                ELSE CAST(payment_days AS INTEGER)
            END,
            TRIM(billing_date)
        FROM raw_billing;
        """
    )


def record_load_audit(conn: sqlite3.Connection, loaded_counts: dict[str, int]) -> None:
    loaded_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows = [
        (table_name, str(SOURCE_FILES[table_name].name), row_count, loaded_at)
        for table_name, row_count in loaded_counts.items()
    ]
    conn.executemany(
        """
        INSERT INTO load_audit (table_name, source_file, row_count, loaded_at_utc)
        VALUES (?, ?, ?, ?)
        """,
        rows,
    )


def fetch_scalar(conn: sqlite3.Connection, sql: str) -> int | float | str | None:
    return conn.execute(sql).fetchone()[0]


def build_summary(conn: sqlite3.Connection, loaded_counts: dict[str, int]) -> dict[str, object]:
    foreign_key_violations = conn.execute("PRAGMA foreign_key_check").fetchall()
    return {
        "database_path": str(DATABASE_PATH),
        "loaded_counts": loaded_counts,
        "typed_table_counts": {
            "patients": fetch_scalar(conn, "SELECT COUNT(*) FROM patients"),
            "visits": fetch_scalar(conn, "SELECT COUNT(*) FROM visits"),
            "billing": fetch_scalar(conn, "SELECT COUNT(*) FROM billing"),
        },
        "foreign_key_violation_count": len(foreign_key_violations),
        "quality_summary": [
            {
                "quality_check": row[0],
                "issue_count": row[1],
                "severity": row[2],
            }
            for row in conn.execute(
                "SELECT quality_check, issue_count, severity FROM v_quality_summary"
            ).fetchall()
        ],
    }


def main() -> None:
    DATABASE_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if DATABASE_PATH.exists():
        DATABASE_PATH.unlink()

    conn = sqlite3.connect(DATABASE_PATH)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        execute_sql_file(conn, SQL_DIR / "phase1_schema.sql")

        loaded_counts = {
            table_name: load_csv(conn, table_name, csv_path)
            for table_name, csv_path in SOURCE_FILES.items()
        }
        insert_typed_tables(conn)
        record_load_audit(conn, loaded_counts)
        execute_sql_file(conn, SQL_DIR / "phase1_views.sql")
        conn.commit()

        summary = build_summary(conn, loaded_counts)
        summary_path = OUTPUT_DIR / "phase1_load_audit.json"
        summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

        print(f"Created database: {DATABASE_PATH}")
        print(f"Wrote load audit: {summary_path}")
        print(json.dumps(summary, indent=2))
    finally:
        conn.close()


if __name__ == "__main__":
    main()
