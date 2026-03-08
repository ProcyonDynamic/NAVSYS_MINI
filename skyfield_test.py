from datetime import datetime, timezone

from astranav_mini.models import SightInput
from astranav_mini.skyfield_engine import compute_zn_hc_skyfield


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


s = SightInput(
    run_id="TEST",
    time_utc=utc_now_iso(),
    lat=24.0,
    lon=-94.0,
    body_kind="SUN",
    body_name="Sun",
    instrument="TEST",
)

res = compute_zn_hc_skyfield(s)
print(res)