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