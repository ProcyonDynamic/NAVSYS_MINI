from datetime import datetime, timezone

from astranav_mini.models import SightInput
from astranav_mini.skyfield_engine import compute_zn_hc_skyfield
from astranav_mini.compass_error import compute_compass_or_gyro_error
from astranav_mini.report_nsc01 import render_nsc01_compass_error_txt


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


print("=== GYRO 1 ===")
s1 = SightInput(
    run_id="TEST",
    time_utc=utc_now_iso(),
    lat=24.0,
    lon=-94.0,
    body_kind="SUN",
    body_name="Sun",
    instrument_mode="GYRO_1",
    instrument_label="Gyro 1",
    observed_bearing_deg=230.0,
)

sky1 = compute_zn_hc_skyfield(s1)
res1 = compute_compass_or_gyro_error(s1, sky1)
print(render_nsc01_compass_error_txt(
    form="NSC-01",
    generated_utc=utc_now_iso(),
    s=s1,
    sky=sky1,
    res=res1,
))

print("=== GYRO 2 ===")
s2 = SightInput(
    run_id="TEST",
    time_utc=utc_now_iso(),
    lat=24.0,
    lon=-94.0,
    body_kind="SUN",
    body_name="Sun",
    instrument_mode="GYRO_2",
    instrument_label="Gyro 2",
    observed_bearing_deg=231.0,
)

sky2 = compute_zn_hc_skyfield(s2)
res2 = compute_compass_or_gyro_error(s2, sky2)
print(render_nsc01_compass_error_txt(
    form="NSC-01",
    generated_utc=utc_now_iso(),
    s=s2,
    sky=sky2,
    res=res2,
))

print("=== MAGNETIC ===")
s3 = SightInput(
    run_id="TEST",
    time_utc=utc_now_iso(),
    lat=24.0,
    lon=-94.0,
    body_kind="SUN",
    body_name="Sun",
    instrument_mode="MAGNETIC",
    instrument_label="Magnetic Compass",
    observed_bearing_deg=232.0,
    variation_deg=1.5,   # 1.5 E
)

sky3 = compute_zn_hc_skyfield(s3)
res3 = compute_compass_or_gyro_error(
    s3,
    sky3,
    deviation_card_csv_path=r"D:\NAVSYS_USB\ASTRANAV\deviation_card.csv",
)
print(render_nsc01_compass_error_txt(
    form="NSC-01",
    generated_utc=utc_now_iso(),
    s=s3,
    sky=sky3,
    res=res3,
))