from navwarn_mini.coords import extract_vertices_from_text
from navwarn_mini.coord_repair import repair_split_coords


def test_repair_lat_lon_split_across_lines():
    raw = "25 26.8N\n091 36.6W"
    fixed = repair_split_coords(raw)
    assert "25 26.8N 091 36.6W" in fixed


def test_repair_lon_deg_min_split():
    raw = "25 26.8N 091\n36.6W"
    fixed = repair_split_coords(raw)
    assert "25 26.8N 091 36.6W" in fixed


def test_repair_hemisphere_split():
    raw = "25 26.8\nN 091 36.6 W"
    fixed = repair_split_coords(raw)
    assert "25 26.8 N 091 36.6 W" in fixed or "25 26.8N 091 36.6W" in fixed


def test_repair_compact_ocr_coords():
    raw = "2526.8N\n09136.6W"
    fixed = repair_split_coords(raw)
    assert "25 26.8 N" in fixed or "25 26.8N" in fixed
    assert "091 36.6 W" in fixed or "091 36.6W" in fixed


def test_repair_multiple_points_bounded_area():
    raw = (
        "IN AREA BOUNDED BY\n"
        "25 26.8N 091 36.6W\n"
        "25 20.1N\n"
        "091 10.3W\n"
        "24 58.0N 091 25.0W"
    )
    fixed = repair_split_coords(raw)
    assert "25 20.1N 091 10.3W" in fixed

def test_extract_vertices_from_multiline_area():
    txt = """
    OPERATIONS IN AREA BOUND BY:
    24-21.874N 094-57.956W --- 24-21.170N 093-55.212W
    24-34.648N 093-43.047W
    NNNN
    """

def test_extract_vertices_from_split_lines():
    txt = """
    IN AREA BOUNDED BY
    25 26.8N 091 36.6W
    25 20.1N
    091 10.3W
    24 58.0N 091 25.0W
    """

    vertices = extract_vertices_from_text(txt)
    assert vertices is not None
    assert len(vertices) >= 3

    vertices = extract_vertices_from_text(txt)
    assert vertices is not None
    assert len(vertices) >= 3