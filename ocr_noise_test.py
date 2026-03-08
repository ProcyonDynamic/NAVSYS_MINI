from navwarn_mini.coords import extract_vertices_from_text

txt = """
AREA BOUND BY:
24-21.874N O94-57.956VV
24-21.170N 093-55.212W
NNNN
"""

print(extract_vertices_from_text(txt))