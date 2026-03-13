from __future__ import annotations

import csv
import math
from pathlib import Path
from typing import Optional

from .models import Geometry, LatLon, PlatformRegistryEntry


def _nm_between(a: LatLon, b: LatLon) -> float:
    # simple haversine, good enough for identity matching
    r_nm = 3440.065
    lat1 = math.radians(a.lat)
    lon1 = math.radians(a.lon)
    lat2 = math.radians(b.lat)
    lon2 = math.radians(b.lon)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * r_nm * math.asin(math.sqrt(h))


def _safe_upper(s: Optional[str]) -> str:
    return " ".join((s or "").upper().split())


def _normalize_name(s: Optional[str]) -> str:
    s = _safe_upper(s)
    s = s.replace("DS-", "DS")
    s = s.replace("-", " ")
    return " ".join(s.split())


def _first_vertex(geometry: Geometry) -> Optional[LatLon]:
    if not geometry.vertices:
        return None
    return geometry.vertices[0]


def _load_registry(csv_path: Path) -> list[PlatformRegistryEntry]:
    rows: list[PlatformRegistryEntry] = []
    if not csv_path.exists():
        return rows

    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            geom = Geometry(
                geom_type="POINT",
                vertices=[LatLon(lat=float(row["lat"]), lon=float(row["lon"]))],
                closed=False,
            )
            aliases = [x for x in row.get("aliases", "").split(";") if x]
            rows.append(
                PlatformRegistryEntry(
                    platform_id=row["platform_id"],
                    platform_name=row.get("platform_name") or None,
                    platform_type=row.get("platform_type") or None,
                    current_geometry=geom,
                    last_seen_utc=row["last_seen_utc"],
                    first_seen_utc=row["first_seen_utc"],
                    last_warning_id=row["last_warning_id"],
                    aliases=aliases,
                    state=row.get("state", "ACTIVE"),
                    tce_thread_id=row.get("tce_thread_id", f'TCE_{row["platform_id"]}'),
                )
            )
    return rows


def _write_registry(csv_path: Path, rows: list[PlatformRegistryEntry]) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "platform_id",
                "platform_name",
                "platform_type",
                "lat",
                "lon",
                "last_seen_utc",
                "first_seen_utc",
                "last_warning_id",
                "aliases",
                "state",
                "tce_thread_id",
            ],
        )
        writer.writeheader()
        for r in rows:
            pt = _first_vertex(r.current_geometry)
            writer.writerow(
                {
                    "platform_id": r.platform_id,
                    "platform_name": r.platform_name or "",
                    "platform_type": r.platform_type or "",
                    "lat": pt.lat if pt else "",
                    "lon": pt.lon if pt else "",
                    "last_seen_utc": r.last_seen_utc,
                    "first_seen_utc": r.first_seen_utc,
                    "last_warning_id": r.last_warning_id,
                    "aliases": ";".join(r.aliases),
                    "state": r.state,
                    "tce_thread_id": r.tce_thread_id,
                }
            )


def _next_platform_id(rows: list[PlatformRegistryEntry]) -> str:
    max_n = 0
    for r in rows:
        try:
            n = int(r.platform_id.split("-")[-1])
            max_n = max(max_n, n)
        except Exception:
            pass
    return f"OFFOBJ-{max_n + 1:06d}"


def resolve_platform_identity(
    *,
    registry_csv_path: str,
    platform_name: Optional[str],
    platform_type: Optional[str],
    geometry: Geometry,
    warning_id: str,
    observed_utc: str,
) -> dict:
    csv_path = Path(registry_csv_path)
    rows = _load_registry(csv_path)

    obs_pt = _first_vertex(geometry)
    obs_name = _normalize_name(platform_name)

    best_idx = None
    best_score = -1.0
    best_distance = None

    for i, row in enumerate(rows):
        row_pt = _first_vertex(row.current_geometry)
        if not row_pt or not obs_pt:
            continue

        score = 0.0

        row_name = _normalize_name(row.platform_name)
        alias_names = {_normalize_name(a) for a in row.aliases}
        if obs_name and (obs_name == row_name or obs_name in alias_names):
            score += 0.70

        if platform_type and row.platform_type and platform_type == row.platform_type:
            score += 0.10

        d_nm = _nm_between(obs_pt, row_pt)
        if d_nm <= 1.0:
            score += 0.25
        elif d_nm <= 5.0:
            score += 0.15
        elif d_nm <= 20.0:
            score += 0.05

        if score > best_score:
            best_score = score
            best_idx = i
            best_distance = d_nm

    if best_idx is None or best_score < 0.35:
        platform_id = _next_platform_id(rows)
        entry = PlatformRegistryEntry(
            platform_id=platform_id,
            platform_name=platform_name,
            platform_type=platform_type,
            current_geometry=geometry,
            last_seen_utc=observed_utc,
            first_seen_utc=observed_utc,
            last_warning_id=warning_id,
            aliases=[],
            state="ACTIVE",
            tce_thread_id=f"TCE_{platform_id}",
        )
        rows.append(entry)
        _write_registry(csv_path, rows)
        return {
            "platform_id": platform_id,
            "match_status": "NEW_OBJECT",
            "identity_confidence": 0.0,
            "tce_thread_id": entry.tce_thread_id,
            "moved_nm": None,
        }

    row = rows[best_idx]
    moved_nm = best_distance
    match_status = "MATCHED_EXISTING"
    if moved_nm is not None and moved_nm > 1.0:
        match_status = "POSITION_UPDATED"

    aliases = list(row.aliases)
    if platform_name:
        norm_in = _normalize_name(platform_name)
        norm_row = _normalize_name(row.platform_name)
        if norm_in and norm_in != norm_row and norm_in not in {_normalize_name(a) for a in aliases}:
            aliases.append(platform_name)
            match_status = "NAME_VARIANT"

    updated = PlatformRegistryEntry(
        platform_id=row.platform_id,
        platform_name=row.platform_name or platform_name,
        platform_type=row.platform_type or platform_type,
        current_geometry=geometry,
        last_seen_utc=observed_utc,
        first_seen_utc=row.first_seen_utc,
        last_warning_id=warning_id,
        aliases=aliases,
        state="ACTIVE",
        tce_thread_id=row.tce_thread_id,
    )
    rows[best_idx] = updated
    _write_registry(csv_path, rows)

    return {
        "platform_id": updated.platform_id,
        "match_status": match_status,
        "identity_confidence": round(best_score, 3),
        "tce_thread_id": updated.tce_thread_id,
        "moved_nm": round(moved_nm, 3) if moved_nm is not None else None,
    }