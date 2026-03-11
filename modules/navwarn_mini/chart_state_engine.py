from __future__ import annotations

import csv
from pathlib import Path
from typing import List, Dict


def load_active_rows(active_table_csv: str) -> List[Dict[str, str]]:
    path = Path(active_table_csv)
    if not path.exists():
        return []

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def get_active_rows(active_table_csv: str) -> List[Dict[str, str]]:
    rows = load_active_rows(active_table_csv)
    return [row for row in rows if row.get("state", "").strip().upper() == "ACTIVE"]

def rebuild_active_chart_session(
    *,
    active_table_csv: str,
    output_csv_path: str,
) -> dict:
    active_rows = get_active_rows(active_table_csv)

    output_path = Path(output_csv_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["warning_id", "navarea", "plot_ref"])

        for row in active_rows:
            writer.writerow([
                row.get("warning_id", ""),
                row.get("navarea", ""),
                row.get("plot_ref", ""),
            ])

    return {
        "ok": True,
        "active_count": len(active_rows),
        "output_csv_path": str(output_path),
    }