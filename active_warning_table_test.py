from modules.navwarn_mini.active_warning_table import (
    ActiveWarningRecord,
    get_active_warning_ids,
    load_active_warning_table,
    mark_cancelled_targets,
    upsert_warning_record,
)


def test_upsert_and_load(tmp_path):
    path = tmp_path / "active_warning_table.csv"

    upsert_warning_record(
        path,
        ActiveWarningRecord(
            warning_id="NAVAREA IV 145/26",
            navarea="IV",
            state="ACTIVE",
            last_updated_utc="2026-03-11T12:00:00Z",
            plotted="YES",
        ),
    )

    rows = load_active_warning_table(path)
    assert len(rows) == 1
    assert rows[0].warning_id == "NAVAREA IV 145/26"
    assert rows[0].state == "ACTIVE"


def test_mark_cancelled_targets(tmp_path):
    path = tmp_path / "active_warning_table.csv"

    upsert_warning_record(
        path,
        ActiveWarningRecord(
            warning_id="NAVAREA IV 144/26",
            navarea="IV",
            state="ACTIVE",
            last_updated_utc="2026-03-11T12:00:00Z",
            plotted="YES",
        ),
    )

    mark_cancelled_targets(
        path,
        ["NAVAREA IV 144/26"],
        "2026-03-11T13:00:00Z",
    )

    rows = load_active_warning_table(path)
    assert len(rows) == 1
    assert rows[0].state == "CANCELLED"
    assert rows[0].plotted == "NO"


def test_get_active_warning_ids(tmp_path):
    path = tmp_path / "active_warning_table.csv"

    upsert_warning_record(
        path,
        ActiveWarningRecord(
            warning_id="NAVAREA IV 145/26",
            navarea="IV",
            state="ACTIVE",
        ),
    )
    upsert_warning_record(
        path,
        ActiveWarningRecord(
            warning_id="NAVAREA IV 144/26",
            navarea="IV",
            state="CANCELLED",
        ),
    )

    ids = get_active_warning_ids(path, navarea="IV")
    assert ids == ["NAVAREA IV 145/26"]