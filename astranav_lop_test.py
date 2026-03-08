from datetime import datetime, timezone

from astranav_mini.models import SightInput
from astranav_mini.skyfield_engine import compute_zn_hc_skyfield
from astranav_mini.lop import compute_lop
from astranav_mini.report_nsc02 import render_nsc02_lop_txt


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


s = SightInput(
    run_id="TEST",
    time_utc=utc_now_iso(),
    lat=24.0,
    lon=-94.0,
    body_kind="SUN",
    body_name="Sun",
    instrument_mode="GYRO_1",   # not used here, but model requires it
    observed_ho_deg=26.80,      # test value near Hc
    instrument_label="LOP TEST",
)

sky = compute_zn_hc_skyfield(s)
res = compute_lop(s, sky)

print(sky)
print(res)

txt = render_nsc02_lop_txt(
    form="NSC-02",
    generated_utc=utc_now_iso(),
    s=s,
    sky=sky,
    res=res,
)

print("\n--- REPORT ---\n")
print(txt)