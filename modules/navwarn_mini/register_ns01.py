from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from .models import WarningClassified, LatLon


@dataclass(frozen=True)
class NS01Row:
    seq: int
    form: str  # "NS-01"
    time_utc: str
    run_id: str
    navarea: str
    warning_id: str
    type: str
    psn_lat: float
    psn_lon: float
    dist_nm: Optional[float]
    band: str
    plotted: str  # "YES" | "NO"
    source_kind: str
    source_url: str
    status: str
    notes: str


def _primary_position(w: WarningClassified) -> LatLon:
    """
    v0.1 PSN rule:
    - Use the first vertex for POINT/LINE/AREA.
    (Simple, deterministic; centroid can be added later.)
    """
    return w.geometry.vertices[0]


def make_ns01_row(seq: int, w: WarningClassified, plotted: str = "NO") -> NS01Row:
    psn = _primary_position(w)
    source_url = ""
    if w.source_ref is not None:
        source_url = w.source_ref.url or ""

    return NS01Row(
        seq=seq,
        form="NS-01",
        time_utc=w.processed_utc,
        run_id=w.run_id,
        navarea=w.navarea,
        warning_id=w.warning_id,
        type=w.geometry.geom_type,
        psn_lat=float(psn.lat),
        psn_lon=float(psn.lon),
        dist_nm=None if w.distance_nm is None else float(w.distance_nm),
        band=w.band,
        plotted=plotted,
        source_kind=w.source_kind,
        source_url=source_url,
        status=w.status,
        notes="; ".join(w.errors) if w.errors else "",
    )


_NS01_HEADERS = [
    "Seq",
    "Form",
    "Time_UTC",
    "Run_ID",
    "NAVAREA",
    "Warning_ID",
    "Type",
    "PSN_Lat",
    "PSN_Lon",
    "Dist_NM",
    "Band",
    "Plotted",
    "Source_Kind",
    "Source_URL",
    "Status",
    "Notes",
]


def write_ns01_csv(rows: List[NS01Row], csv_path: str) -> None:
    """
    Writes NS-01 CSV with locked headers:
    Seq,Form,Time_UTC,Run_ID,NAVAREA,Warning_ID,Type,PSN_Lat,PSN_Lon,Dist_NM,Band,Plotted,Source_Kind,Source_URL,Status,Notes
    """
    p = Path(csv_path)
    p.parent.mkdir(parents=True, exist_ok=True)

    with p.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(_NS01_HEADERS)

        for r in rows:
            w.writerow([
                r.seq,
                r.form,
                r.time_utc,
                r.run_id,
                r.navarea,
                r.warning_id,
                r.type,
                f"{r.psn_lat:.6f}",
                f"{r.psn_lon:.6f}",
                "" if r.dist_nm is None else f"{r.dist_nm:.1f}",
                r.band,
                r.plotted,
                r.source_kind,
                r.source_url,
                r.status,
                r.notes,
            ])


def read_ns01_csv(csv_path: str) -> List[dict]:
    """
    Simple reader used by update_plotted_flag.
    Returns list of dict rows keyed by the locked headers.
    """
    p = Path(csv_path)
    if not p.exists():
        return []

    with p.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = []
        for row in reader:
            rows.append(row)
        return rows


def update_plotted_flag(
    *,
    ns01_csv_path: str,
    warning_id: str,
    plotted: str
) -> None:
    """
    Edits an existing NS-01 CSV and sets Plotted YES/NO for the matching warning_id.
    """
    plotted = plotted.strip().upper()
    if plotted not in ("YES", "NO"):
        raise ValueError("plotted must be YES or NO")

    rows = read_ns01_csv(ns01_csv_path)
    if not rows:
        raise FileNotFoundError(f"NS-01 CSV not found or empty: {ns01_csv_path}")

    updated = False
    for r in rows:
        if (r.get("Warning_ID") or "").strip() == warning_id.strip():
            r["Plotted"] = plotted
            updated = True

    if not updated:
        raise ValueError(f"Warning_ID not found in register: {warning_id}")

    # Rewrite the file with the same locked headers
    p = Path(ns01_csv_path)
    with p.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=_NS01_HEADERS)
        writer.writeheader()
        for r in rows:
            # DictWriter writes in header order
            writer.writerow({h: r.get(h, "") for h in _NS01_HEADERS})
            
            
def next_seq_for_register(ns01_csv_path: str) -> int:
    """
    Returns next Seq value for an existing NS-01 register CSV.
    If file doesn't exist or is empty -> 1
    """
    rows = read_ns01_csv(ns01_csv_path)
    if not rows:
        return 1

    best = 0
    for r in rows:
        s = (r.get("Seq") or "").strip()
        try:
            n = int(s)
            if n > best:
                best = n
        except ValueError:
            continue
    return best + 1

def append_ns01_row(csv_path: str, row: NS01Row) -> None:
    """
    Appends a single row to an NS-01 CSV.
    Creates file with headers if missing.
    """
    p = Path(csv_path)
    p.parent.mkdir(parents=True, exist_ok=True)

    file_exists = p.exists()

    with p.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if not file_exists:
            w.writerow(_NS01_HEADERS)

        w.writerow([
            row.seq,
            row.form,
            row.time_utc,
            row.run_id,
            row.navarea,
            row.warning_id,
            row.type,
            f"{row.psn_lat:.6f}",
            f"{row.psn_lon:.6f}",
            "" if row.dist_nm is None else f"{row.dist_nm:.1f}",
            row.band,
            row.plotted,
            row.source_kind,
            row.source_url,
            row.status,
            row.notes,
        ])
        
        
