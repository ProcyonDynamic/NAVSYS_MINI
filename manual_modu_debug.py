from pathlib import Path
from modules.navwarn_mini.process_warning import (
    split_platform_sections,
    split_platform_sections_fallback,
    detect_platform_list_lines,
    extract_platform_name,
    extract_platform_name_fallback,
    process_warning_text,
)
from modules.navwarn_mini.extract_warning import extract_vertices_and_geom
from modules.navwarn_mini.interpreter import interpret_warning

RAW = """
PASTE YOUR FAILING MODU BULLETIN HERE
""".strip()

print("=== RAW ===")
print(RAW)
print()

print("=== split_platform_sections ===")
s1 = split_platform_sections(RAW)
print(s1)
print("count:", len(s1))
print()

print("=== split_platform_sections_fallback ===")
s2 = split_platform_sections_fallback(RAW)
print(s2)
print("count:", len(s2))
print()

print("=== detect_platform_list_lines ===")
s3 = detect_platform_list_lines(RAW)
print(s3)
print("count:", len(s3))
print()

print("=== per-section names and vertices ===")
for i, sec in enumerate((s1 if len(s1) > 1 else s2 if len(s2) > 1 else s3), start=1):
    print(f"[{i}] SECTION:", sec)
    print("name(main):", extract_platform_name(sec))
    print("name(fallback):", extract_platform_name_fallback(sec))
    verts, geom = extract_vertices_and_geom(sec)
    print("geom:", geom)
    print("verts:", verts)
    print()

print("=== interpreter ===")
draft, interp = interpret_warning(
    warning_id="NAVAREA IV TEST/26",
    navarea="IV",
    source_kind="MANUAL",
    title="MODU DEBUG",
    body=RAW,
    run_id="DEBUGRUN",
    created_utc="2026-03-13T00:00:00Z",
)
print("warning_type:", interp.warning_type)
print("is_reference_message:", interp.is_reference_message)
print("is_cancellation:", interp.is_cancellation)
print("geometry_blocks:", len(interp.structure.geometry_blocks))
for idx, block in enumerate(interp.structure.geometry_blocks, start=1):
    print("block", idx, "type:", block.block_type, "extracted:", block.extracted)
print()

print("=== process_warning_text ===")
out = process_warning_text(
    raw_text=RAW,
    navarea="IV",
    ship_lat=None,
    ship_lon=None,
    output_root=str(Path("tmp_modu_debug")),
    warning_id="NAVAREA IV TEST/26",
    title="MODU DEBUG",
    source_kind="MANUAL",
    operator_name="TEST",
)
print(out)