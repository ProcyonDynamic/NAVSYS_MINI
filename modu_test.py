from pathlib import Path
import shutil

from modules.navwarn_mini.process_warning import process_warning_text

TEST_ROOT = Path("tmp_modu_test")

if TEST_ROOT.exists():
     shutil.rmtree(TEST_ROOT)

sample = """NAVAREA IV 204/26
GULF OF MEXICO.
MODU AGOSTO 12 19-23.0N 092-03.1W.
MODU ALULA 11-38.4N 070-21.8W.
PLATFORM ARGOS 27-10.4N 090-22.0W.
PLATFORM ATLANTIS 27-10.0N 090-20.0W.
"""

result = process_warning_text(
     raw_text=sample,
     navarea="IV",
     ship_lat=None,
     ship_lon=None,
     output_root="tmp_modu_test",
     warning_id="NAVAREA IV 204/26",
)


print("Expected bulletin ID: NAVAREA IV 204/26")
print(result)