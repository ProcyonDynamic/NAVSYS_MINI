from __future__ import annotations

import csv
from pathlib import Path


def _read_csv_rows(csv_path: Path) -> list[list[str]]:
    if not csv_path.exists():
        return []
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.reader(f))


def rebuild_active_session_csv(
    *,
    active_table_csv_path: str,
    output_csv_path: str,
) -> dict:

    active_path = Path(active_table_csv_path)
    out_path = Path(output_csv_path)

    if not active_path.exists():
        return {
            "ok": False,
            "mode": "rebuild",
            "errors": [f"active table not found: {active_path}"],
        }

    rows = _read_csv_rows(active_path)

    if not rows:
        return {
            "ok": False,
            "mode": "rebuild",
            "errors": ["active warning table empty"],
        }

    header = rows[0]
    body = rows[1:]

    out_rows = []
    errors = []

    for row in body:

        try:
            state = row[2]     # assuming state column index
            plotted = row[3]   # assuming plotted column index
            plot_ref = row[4]  # assuming csv path column index
        except Exception:
            continue

        if state != "ACTIVE":
            continue

        if plotted != "True":
            continue

        plot_path = Path(plot_ref)

        if not plot_path.exists():
            errors.append(f"missing plot csv: {plot_path}")
            continue

        plot_rows = _read_csv_rows(plot_path)

        if not plot_rows:
            continue

        if not out_rows:
            out_rows.append(plot_rows[0])  # header

        out_rows.extend(plot_rows[1:])

    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(out_rows)

    return {
        "ok": True,
        "mode": "rebuild",
        "rows_written": len(out_rows),
        "errors": errors,
    }

def append_warning_csv_to_active_session(
    *,
    warning_plot_csv_path: str,
    output_csv_path: str,
) -> dict:
    src = Path(warning_plot_csv_path)
    out = Path(output_csv_path)

    if not src.exists():
        return {
            "ok": False,
            "mode": "append",
            "errors": [f"warning plot csv not found: {src}"],
        }

    src_rows = _read_csv_rows(src)
    if not src_rows:
        return {
            "ok": False,
            "mode": "append",
            "errors": [f"warning plot csv empty: {src}"],
        }

    src_header = src_rows[0]
    src_body = src_rows[1:]

    out.parent.mkdir(parents=True, exist_ok=True)

    if not out.exists():
        with out.open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(src_header)
            writer.writerows(src_body)
        return {
            "ok": True,
            "mode": "append",
            "rows_added": len(src_body),
            "errors": [],
        }

    out_rows = _read_csv_rows(out)
    if not out_rows:
        with out.open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(src_header)
            writer.writerows(src_body)
        return {
            "ok": True,
            "mode": "append",
            "rows_added": len(src_body),
            "errors": [],
        }

    out_header = out_rows[0]

    # conservative safety check
    if out_header != src_header:
        return {
            "ok": False,
            "mode": "append",
            "errors": ["header mismatch between active session csv and warning plot csv"],
        }

    with out.open("a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(src_body)

    return {
        "ok": True,
        "mode": "append",
        "rows_added": len(src_body),
        "errors": [],
    }

def update_active_session_for_warning(
    *,
    active_table_csv_path: str,
    output_csv_path: str,
    warning_plot_csv_path: str | None,
    warning_state: str,
    is_replacement: bool = False,
) -> dict:
    if warning_state != "ACTIVE":
        result = rebuild_active_session_csv(
            active_table_csv_path=active_table_csv_path,
            output_csv_path=output_csv_path,
        )
        result["mode"] = "rebuild"
        return result

    if is_replacement:
        result = rebuild_active_session_csv(
            active_table_csv_path=active_table_csv_path,
            output_csv_path=output_csv_path,
        )
        result["mode"] = "rebuild"
        return result

    if not warning_plot_csv_path:
        result = rebuild_active_session_csv(
            active_table_csv_path=active_table_csv_path,
            output_csv_path=output_csv_path,
        )
        result["mode"] = "rebuild"
        return result

    append_result = append_warning_csv_to_active_session(
        warning_plot_csv_path=warning_plot_csv_path,
        output_csv_path=output_csv_path,
    )

    if append_result["ok"]:
        return append_result

    rebuild_result = rebuild_active_session_csv(
        active_table_csv_path=active_table_csv_path,
        output_csv_path=output_csv_path,
    )
    rebuild_result["mode"] = "rebuild_after_append_fail"
    rebuild_result["append_errors"] = append_result.get("errors", [])
    return rebuild_result