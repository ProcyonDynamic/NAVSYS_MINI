from modules.navwarn_mini.process_warning import process_warning_text

sample = """NAVAREA IV 201/26
GULF OF MEXICO.
MODU TRANSOCEAN BLAZER IN POSITION 27-45.2N 091-12.8W.
500 METER SAFETY ZONE AROUND UNIT.
"""
result = process_warning_text(
    raw_text=sample,
    navarea="IV",
    ship_lat=None,
    ship_lon=None,
    output_root="tmp_modu_test",
    warning_id="NAVAREA IV 201/26",
)

print(result)