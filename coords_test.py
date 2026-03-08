from navwarn_mini.coords import extract_vertices_from_text

txt = """
OPERATIONS IN AREA BOUND BY:
24-21.874N 094-57.956W --- 24-21.170N 093-55.212W
24-34.648N 093-43.047W
NNNN
"""

print(extract_vertices_from_text(txt))