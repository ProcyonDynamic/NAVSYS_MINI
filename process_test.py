from navwarn_mini.process_warning import process_warning_text

txt = """
OPERATIONS IN AREA BOUND BY:
24-21.874N 094-57.956W
24-34.648N 093-43.047W
24-50.439N 092-59.767W
"""

res = process_warning_text(
    raw_text=txt,
    navarea="IV",
    ship_lat=24.0,
    ship_lon=-94.0,
    output_root=r"D:\NAVSYS_USB",
    warning_id="NAVAREA IV TEST",
    title="OPERATIONS AREA",
    source_kind="MANUAL",
    operator_name="Eddie",
    vessel_name="",
    route_csv_path=r"D:\NAVSYS_USB\ROUTE\route.csv",
)

print(res)