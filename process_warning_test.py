from modules.navwarn_mini.process_warning import process_warning_text


def test_reference_bulletin_returns_reference_status(tmp_path):
    result = process_warning_text(
        raw_text="""
NAVAREA IV 300/26 101200 UTC MAR 26
1. IN FORCE WARNINGS AT 101200 UTC MAR 26:
NAVAREA IV 210/26
NAVAREA IV 211/26
NAVAREA IV 250/26
2. CANCEL THIS MSG 111200 UTC MAR 26.
""".strip(),
        navarea="IV",
        ship_lat=None,
        ship_lon=None,
        output_root=str(tmp_path),
        warning_id="NAVAREA IV 300/26",
        title="NAVAREA IV 300/26 101200 UTC MAR 26",
    )

    assert result["ok"] is True
    assert result["status"] == "REFERENCE_BULLETIN"


def test_cancellation_warning_returns_cancellation_status(tmp_path):
    result = process_warning_text(
        raw_text="CANCEL NAVAREA IV 144/26.",
        navarea="IV",
        ship_lat=None,
        ship_lon=None,
        output_root=str(tmp_path),
        warning_id="NAVAREA IV 145/26",
        title="NAVAREA IV 145/26 081530 UTC MAR 26",
    )

    assert result["ok"] is True
    assert result["status"] == "CANCELLATION_WARNING"
    assert "NAVAREA IV 144/26" in result["cancel_targets"]


def test_duplicate_warning_returns_duplicate_status(tmp_path):
    first = process_warning_text(
        raw_text="""
DRILLING OPERATIONS IN AREA BOUNDED BY
25 10.0N 090 20.0W
25 20.0N 090 30.0W
25 30.0N 090 10.0W
""".strip(),
        navarea="IV",
        ship_lat=None,
        ship_lon=None,
        output_root=str(tmp_path),
        warning_id="NAVAREA IV 146/26",
        title="NAVAREA IV 146/26 081700 UTC MAR 26",
    )

    second = process_warning_text(
        raw_text="""
DRILLING OPERATIONS IN AREA BOUNDED BY
25 10.0N 090 20.0W
25 20.0N 090 30.0W
25 30.0N 090 10.0W
""".strip(),
        navarea="IV",
        ship_lat=None,
        ship_lon=None,
        output_root=str(tmp_path),
        warning_id="NAVAREA IV 146/26",
        title="NAVAREA IV 146/26 081700 UTC MAR 26",
    )

    assert first["ok"] is True
    assert second["ok"] is True
    assert second["status"] == "DUPLICATE_WARNING"
    
    
from pathlib import Path
from navwarn_mini.process_warning import process_warning_text


def test_process_single_modu_forces_point(tmp_path: Path):
    result = process_warning_text(
        raw_text="MODU OCEAN TITAN DRILLING AT 24 10.2N 092 33.1W",
        navarea="IV",
        ship_lat=None,
        ship_lon=None,
        output_root=str(tmp_path),
        warning_id="NAVAREA IV 123/26",
        title="MODU OCEAN TITAN",
        source_kind="MANUAL",
        operator_name="TEST",
    )

    assert result["ok"] is True
    assert result["geom_type"] == "POINT"
    assert result["vertex_count"] == 1
    assert result["plot_csv_path"] is not None