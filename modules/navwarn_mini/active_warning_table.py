from __future__ import annotations

import csv
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Optional


@dataclass
class ActiveWarningRecord:
    warning_id: str
    navarea: str
    state: str
    source_warning_id: str = ""
    cancel_targets: str = ""
    last_updated_utc: str = ""
    plotted: str = "NO"
    plot_ref: str = ""


FIELDNAMES = [
    "warning_id",
    "navarea",
    "state",
    "source_warning_id",
    "cancel_targets",
    "last_updated_utc",
    "plotted",
    "plot_ref",
]


def load_active_warning_table(path: Path) -> List[ActiveWarningRecord]:
    if not path.exists():
        return []

    rows: List[ActiveWarningRecord] = []

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(
                ActiveWarningRecord(
                    warning_id=row.get("warning_id", ""),
                    navarea=row.get("navarea", ""),
                    state=row.get("state", ""),
                    source_warning_id=row.get("source_warning_id", ""),
                    cancel_targets=row.get("cancel_targets", ""),
                    last_updated_utc=row.get("last_updated_utc", ""),
                    plotted=row.get("plotted", "NO"),
                    plot_ref=row.get("plot_ref", ""),
                )
            )

    return rows


def save_active_warning_table(path: Path, rows: List[ActiveWarningRecord]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def upsert_warning_record(path: Path, record: ActiveWarningRecord) -> None:
    rows = load_active_warning_table(path)

    replaced = False
    for i, row in enumerate(rows):
        if row.warning_id.strip().upper() == record.warning_id.strip().upper():
            rows[i] = record
            replaced = True
            break

    if not replaced:
        rows.append(record)

    save_active_warning_table(path, rows)


def mark_cancelled_targets(
    path: Path,
    cancel_targets: List[str],
    updated_utc: str,
) -> None:
    if not cancel_targets:
        return

    rows = load_active_warning_table(path)
    target_set = {x.strip().upper() for x in cancel_targets if x.strip()}

    changed = False
    for row in rows:
        if row.warning_id.strip().upper() in target_set:
            row.state = "CANCELLED"
            row.last_updated_utc = updated_utc
            row.plotted = "NO"
            changed = True

    if changed:
        save_active_warning_table(path, rows)


def get_active_warning_ids(path: Path, navarea: Optional[str] = None) -> List[str]:
    rows = load_active_warning_table(path)

    out: List[str] = []
    for row in rows:
        if row.state != "ACTIVE":
            continue
        if navarea and row.navarea.strip().upper() != navarea.strip().upper():
            continue
        out.append(row.warning_id)

    return out