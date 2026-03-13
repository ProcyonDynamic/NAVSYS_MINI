from modules.navwarn_mini.interpreter import interpret_warning


def test_cumulative_warning_builds_reference_structure():
    draft, result = interpret_warning(
        warning_id="NAVAREA IV 300/26",
        navarea="IV",
        source_kind="NAVAREA",
        title="NAVAREA IV 300/26 101200 UTC MAR 26",
        body="""
1. IN FORCE WARNINGS AT 101200 UTC MAR 26:
NAVAREA IV 210/26
NAVAREA IV 211/26
NAVAREA IV 250/26
2. CANCEL THIS MSG 111200 UTC MAR 26.
""",
        run_id="TEST",
        created_utc="2026-03-11T12:00:00Z",
    )

    assert result.warning_type == "CUMULATIVE"
    assert result.is_reference_message is True
    assert len(result.structure.reference_blocks) >= 1
    assert result.structure.cancellation_blocks


def test_cancellation_warning_extracts_targets():
    draft, result = interpret_warning(
        warning_id="NAVAREA IV 145/26",
        navarea="IV",
        source_kind="NAVAREA",
        title="NAVAREA IV 145/26 081530 UTC MAR 26",
        body="CANCEL NAVAREA IV 144/26.",
        run_id="TEST",
        created_utc="2026-03-11T12:00:00Z",
    )

    assert result.is_cancellation is True
    assert "NAVAREA IV 144/26" in result.cancellation_targets


def test_geometry_warning_builds_geometry_block():
    draft, result = interpret_warning(
        warning_id="NAVAREA IV 146/26",
        navarea="IV",
        source_kind="NAVAREA",
        title="NAVAREA IV 146/26 081700 UTC MAR 26",
        body="""
DRILLING OPERATIONS IN AREA BOUNDED BY
25 10.0N 090 20.0W
25 20.0N 090 30.0W
25 30.0N 090 10.0W
""",
        run_id="TEST",
        created_utc="2026-03-11T12:00:00Z",
    )

    assert result.warning_type == "DRILLING"
    assert len(result.structure.geometry_blocks) >= 1
    assert result.geometry.geom_type == "AREA"
    assert len(result.geometry.vertices) >= 3
    
from navwarn_mini.interpreter import interpret_warning


def test_interpret_modu_classification():
    draft, result = interpret_warning(
        warning_id="NAVAREA IV 123/26",
        navarea="IV",
        source_kind="MANUAL",
        title="",
        body="MODU OCEAN TITAN DRILLING AT 24 10.2N 092 33.1W",
        run_id="TESTRUN",
        created_utc="2026-03-13T00:00:00Z",
    )

    assert result.warning_type == "MODU"
    assert len(result.geometry.vertices) >= 1


def test_interpret_drilling_classification():
    draft, result = interpret_warning(
        warning_id="NAVAREA IV 124/26",
        navarea="IV",
        source_kind="MANUAL",
        title="",
        body="DRILLING RIG VALARIS DS-10 AT 24 18.0N 092 40.5W",
        run_id="TESTRUN",
        created_utc="2026-03-13T00:00:00Z",
    )

    assert result.warning_type in ("MODU", "DRILLING")
    assert len(result.geometry.vertices) >= 1