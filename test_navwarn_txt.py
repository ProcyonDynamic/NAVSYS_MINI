from pathlib import Path
from modules.navwarn_mini.process_warning import process_warning_text


txt = Path("test.txt").read_text(encoding="utf-8")

result = process_warning_text(
    raw_text=txt,
    navarea="IV",
    ship_lat=12.8100,
    ship_lon=65.5000,
    output_root="output",
    warning_id="TEST001",
    title="Bridge TXT Test"
)

print(result)
