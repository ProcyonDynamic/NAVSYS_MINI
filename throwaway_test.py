from modules.navwarn_mini.extract_warning import extract_vertices_and_geom

tests = [
    "PLATFORM ARGOS 27-10.4N 090-22.0W.",
    "PLATFORM ATLANTIS 27-10.0N 090-20.0W.",
    "MODU AGOSTO 12 19-23.0N 092-03.1W.",
    "MODU ALULA 11-38.4N 070-21.8W.",
]

for t in tests:
    verts, geom = extract_vertices_and_geom(t)
    print(t)
    print("verts:", verts, "geom:", geom)
    print()