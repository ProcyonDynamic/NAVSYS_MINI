from modules.navwarn_mini.extract_warning import extract_vertices_and_geom

sample1 = """NAVAREA IV 204/26
GULF OF MEXICO.
MODU AGOSTO 12 19-23.0N 092-03.1W.
MODU ALULA 11-38.4N 070-21.8W.
"""

sample2 = """NAVAREA IV 205/26
DRILLING OPERATIONS IN AREA BOUNDED BY
25 10.0N 090 20.0W
25 20.0N 090 30.0W
25 30.0N 090 10.0W.
"""

print("TEST 1:", extract_vertices_and_geom(sample1))
print("TEST 2:", extract_vertices_and_geom(sample2))