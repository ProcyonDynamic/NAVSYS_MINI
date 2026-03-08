from navwarn_mini.extract_warning import extract_vertices_and_geom
from navwarn_mini.coord_preview import preview_vertices_dm

txt = """
OPERATIONS IN AREA BOUND BY:
24-21.874N 094-57.956W
24-34.648N 093-43.047W
"""

verts, geom = extract_vertices_and_geom(txt)

print("Geom:", geom)
print(preview_vertices_dm(verts))