from modules.navwarn_mini.warning_splitter_service import split_bulletin_to_envelopes

sample = """NAVAREA IV 204/26
GULF OF MEXICO.
MODU AGOSTO 12 19-23.0N 092-03.1W.
MODU ALULA 11-38.4N 070-21.8W.

NAVAREA IV 205/26
DRILLING OPERATIONS IN AREA BOUNDED BY
25 10.0N 090 20.0W
25 20.0N 090 30.0W
25 30.0N 090 10.0W.
"""

split_result = split_bulletin_to_envelopes(
    raw_text=sample,
    source="MANUAL",
)

print("split_count =", split_result.split_count)
for i, env in enumerate(split_result.envelopes, 1):
    print(f"\n--- envelope {i} ---")
    print("warning_id:", env.warning_id)
    print("navarea:", env.navarea)
    print("raw_text:")
    print(env.raw_text)

    
from modules.navwarn_mini.process_warning import process_warning_text

for i, env in enumerate(split_result.envelopes, 1):
    print(f"\n=== PROCESS ENVELOPE {i} ===")
    result = process_warning_text(
        raw_text=env.raw_text,
        navarea=env.navarea,
        warning_id=env.warning_id,
        ship_lat=None,
        ship_lon=None,
        output_root="tmp_bulletin_test_21",
        source_kind="MANUAL",
        title=env.warning_id,
    )
    
    print("ok:", result.get("ok"))
    print("geom_type:", result.get("geom_type"))
    print("vertex_count:", result.get("vertex_count"))
    print("band:", result.get("band"))
    print("plot_csv_path:", result.get("plot_csv_path"))
    print("errors:", result.get("errors"))