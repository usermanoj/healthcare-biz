"""Run named Phase 1 SQL queries and export auditable CSV outputs."""

from __future__ import annotations

import csv
import sqlite3
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATABASE_PATH = PROJECT_ROOT / "database" / "hospital_operations.db"
QUERY_PATH = PROJECT_ROOT / "sql" / "phase1_analysis_queries.sql"
OUTPUT_DIR = PROJECT_ROOT / "data_outputs" / "phase1"


@dataclass(frozen=True)
class NamedQuery:
    name: str
    sql: str


def parse_named_queries(path: Path) -> list[NamedQuery]:
    queries: list[NamedQuery] = []
    current_name: str | None = None
    current_lines: list[str] = []

    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("-- name:"):
            if current_name is not None:
                queries.append(NamedQuery(current_name, "\n".join(current_lines).strip()))
            current_name = line.split(":", 1)[1].strip()
            current_lines = []
        elif current_name is not None:
            current_lines.append(line)

    if current_name is not None:
        queries.append(NamedQuery(current_name, "\n".join(current_lines).strip()))

    if not queries:
        raise ValueError(f"No named queries found in {path}")
    return queries


def export_query(conn: sqlite3.Connection, query: NamedQuery) -> tuple[int, Path]:
    cursor = conn.execute(query.sql)
    headers = [description[0] for description in cursor.description]
    rows = cursor.fetchall()

    output_path = OUTPUT_DIR / f"{query.name}.csv"
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        writer.writerows(rows)

    return len(rows), output_path


def main() -> None:
    if not DATABASE_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DATABASE_PATH}. Run scripts/build_phase1_database.py first."
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    queries = parse_named_queries(QUERY_PATH)

    manifest_rows: list[tuple[str, int, str]] = []
    conn = sqlite3.connect(DATABASE_PATH)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        for query in queries:
            row_count, output_path = export_query(conn, query)
            manifest_rows.append((query.name, row_count, str(output_path)))
            print(f"{query.name}: {row_count} rows -> {output_path}")
    finally:
        conn.close()

    manifest_path = OUTPUT_DIR / "phase1_query_manifest.csv"
    with manifest_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["query_name", "row_count", "output_path"])
        writer.writerows(manifest_rows)

    print(f"Wrote query manifest: {manifest_path}")


if __name__ == "__main__":
    main()
