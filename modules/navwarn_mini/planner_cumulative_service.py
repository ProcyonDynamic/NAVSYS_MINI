from __future__ import annotations

from pathlib import Path

from .active_warning_table import load_active_warning_table


def _norm(text: str) -> str:
    return " ".join((text or "").split()).upper()


def _decorate(ids: list[str], status: str) -> list[dict]:
    rows = []
    status = (status or "").strip().upper()

    for wid in ids:
        norm_wid = " ".join((wid or "").split())
        if not norm_wid:
            continue

        if status == "ACTIVE":
            css_class = "status-active"
            label = "ACTIVE"
        elif status == "NEW":
            css_class = "status-new"
            label = "NEW"
        elif status == "DROPPED":
            css_class = "status-dropped"
            label = "DROPPED"
        elif status == "CANCELLED":
            css_class = "status-cancelled"
            label = "CANCELLED"
        else:
            css_class = "status-neutral"
            label = status or "INFO"

        rows.append({
            "warning_id": norm_wid,
            "status": status,
            "css_class": css_class,
            "label": label,
        })

    return rows


def build_planner_cumulative_snapshot(
    *,
    output_root: str,
    navarea: str,
) -> dict:
    active_table_csv = Path(output_root) / "NAVWARN" / "active_warning_table.csv"

    if not active_table_csv.exists():
        return {
            "ok": True,
            "navarea": navarea,
            "listed_ids": [],
            "newer_preserved_ids": [],
            "omitted_ids": [],
            "cancelled_ids": [],
            "effective_active_ids": [],
            "listed_rows": [],
            "new_rows": [],
            "dropped_rows": [],
            "cancelled_rows": [],
            "effective_active_rows": [],
            "errors": [],
        }

    rows = load_active_warning_table(active_table_csv)

    nav = _norm(navarea)

    listed_ids: list[str] = []
    newer_preserved_ids: list[str] = []
    omitted_ids: list[str] = []
    cancelled_ids: list[str] = []

    for row in rows:
        row_nav = _norm(getattr(row, "navarea", ""))
        if row_nav != nav:
            continue

        state = _norm(getattr(row, "state", ""))
        warning_id = " ".join((getattr(row, "warning_id", "") or "").split())

        if not warning_id:
            continue

        if state == "ACTIVE":
            if warning_id not in listed_ids:
                listed_ids.append(warning_id)

        elif state == "OMITTED_BY_CUMULATIVE":
            if warning_id not in omitted_ids:
                omitted_ids.append(warning_id)

        elif state == "CANCELLED_EXPLICIT":
            if warning_id not in cancelled_ids:
                cancelled_ids.append(warning_id)

    # newer_preserved_ids v0.1:
    # ACTIVE rows that were not seen in the latest cumulative snapshot markers
    for row in rows:
        row_nav = _norm(getattr(row, "navarea", ""))
        if row_nav != nav:
            continue

        state = _norm(getattr(row, "state", ""))
        warning_id = " ".join((getattr(row, "warning_id", "") or "").split())

        if state != "ACTIVE":
            continue

        last_seen_in_cumulative_id = _norm(getattr(row, "last_seen_in_cumulative_id", ""))
        if not last_seen_in_cumulative_id:
            if warning_id not in newer_preserved_ids:
                newer_preserved_ids.append(warning_id)

    cancelled_set = {_norm(x) for x in cancelled_ids}

    effective_active_ids: list[str] = []
    seen_effective = set()

    for wid in listed_ids + newer_preserved_ids:
        nwid = _norm(wid)
        if not nwid:
            continue
        if nwid in cancelled_set:
            continue
        if nwid not in seen_effective:
            seen_effective.add(nwid)
            effective_active_ids.append(wid)

    return {
        "ok": True,
        "navarea": navarea,
        "listed_ids": listed_ids,
        "newer_preserved_ids": newer_preserved_ids,
        "omitted_ids": omitted_ids,
        "cancelled_ids": cancelled_ids,
        "effective_active_ids": effective_active_ids,
        "listed_rows": _decorate(listed_ids, "ACTIVE"),
        "new_rows": _decorate(newer_preserved_ids, "NEW"),
        "dropped_rows": _decorate(omitted_ids, "DROPPED"),
        "cancelled_rows": _decorate(cancelled_ids, "CANCELLED"),
        "effective_active_rows": _decorate(effective_active_ids, "ACTIVE"),
        "errors": [],
    }