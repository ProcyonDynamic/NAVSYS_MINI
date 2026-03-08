from datetime import datetime, timezone

from navwarn_mini.models import WarningDraft, Geometry, LatLon, Validity, ShipPosition
from navwarn_mini.distance import classify_warning
from navwarn_mini.build_line_aggregate import build_line_aggregate
from navwarn_mini.export_jrc_csv import export_jrc_userchart_csv

from navwarn_mini.register_ns01 import (
    next_seq_for_register,
    make_ns01_row,
    append_ns01_row,
)
from navwarn_mini.ns01_daily import regenerate_daily_ns01_txt


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def utc_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%SZ")


run_id = utc_run_id()
generated_utc = utc_now_iso()
yyyymmdd = datetime.now(timezone.utc).strftime("%Y%m%d")

daily_csv = fr"D:\NAVSYS_USB\NAVWARN\reports\NS-01_navwarn_register_{yyyymmdd}.csv"
daily_txt = fr"D:\NAVSYS_USB\NAVWARN\reports\NS-01_navwarn_register_{yyyymmdd}.txt"

plot_csv = fr"D:\NAVSYS_USB\NAVWARN\plots\jrc_userchart_{run_id}.csv"

# --- Draft warning ---
draft = WarningDraft(
    run_id=run_id,
    created_utc=generated_utc,
    navarea="V",
    source_kind="MANUAL",
    source_ref=None,
    warning_id="NAVAREA V TEST",
    title="TEST WARNING",
    body="DRILLING OPERATIONS IN POSITION",
    validity=Validity(start_utc=None, end_utc=None, ufn=True),
    geometry=Geometry(
        geom_type="POINT",
        vertices=[LatLon(24.3545, -94.9720)],
        closed=False
    ),
)

# --- Ship position ---
ship = ShipPosition(lat=24.0, lon=-94.0, time_utc=generated_utc)

# --- Classify ---
w = classify_warning(draft=draft, processed_utc=generated_utc, ship_position=ship)

# --- Plot ---
obj = build_line_aggregate(w)
export_jrc_userchart_csv(objects=[obj], output_csv_path=plot_csv)

# --- Daily register append with automatic Seq ---
seq = next_seq_for_register(daily_csv)
row = make_ns01_row(seq, w, plotted="NO")
append_ns01_row(daily_csv, row)

# --- Regenerate daily printable TXT from CSV ---
regenerate_daily_ns01_txt(
    daily_ns01_csv_path=daily_csv,
    out_txt_path=daily_txt,
    run_id=run_id,
    generated_utc=generated_utc,
    operator_name="",
    vessel_name="",
)

print("OK")
print("Plot:", plot_csv)
print("NS-01:", daily_csv)
print("NS-01 TXT:", daily_txt)