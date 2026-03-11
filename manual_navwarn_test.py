from pathlib import Path
from modules.navwarn_mini.process_warning import process_warning_text

root = Path("tmp_navwarn_test")

print("=== ACTIVE WARNING ===")
r1 = process_warning_text(
    raw_text="""
DRILLING OPERATIONS IN AREA BOUNDED BY
25 10.0N 090 20.0W
25 20.0N 090 30.0W
25 30.0N 090 10.0W
""".strip(),
    navarea="IV",
    ship_lat=None,
    ship_lon=None,
    output_root=str(root),
    warning_id="NAVAREA IV 144/26",
    title="NAVAREA IV 144/26 081700 UTC MAR 26",
)
print(r1)

print("=== DUPLICATE WARNING ===")
r2 = process_warning_text(
    raw_text="""
DRILLING OPERATIONS IN AREA BOUNDED BY
25 10.0N 090 20.0W
25 20.0N 090 30.0W
25 30.0N 090 10.0W
""".strip(),
    navarea="IV",
    ship_lat=None,
    ship_lon=None,
    output_root=str(root),
    warning_id="NAVAREA IV 144/26",
    title="NAVAREA IV 144/26 081700 UTC MAR 26",
)
print(r2)

print("=== CANCELLATION WARNING ===")
r3 = process_warning_text(
    raw_text="CANCEL NAVAREA IV 144/26.",
    navarea="IV",
    ship_lat=None,
    ship_lon=None,
    output_root=str(root),
    warning_id="NAVAREA IV 145/26",
    title="NAVAREA IV 145/26 081530 UTC MAR 26",
)
print(r3)

print("Check file:")
print(root / "NAVWARN" / "active_warning_table.csv")