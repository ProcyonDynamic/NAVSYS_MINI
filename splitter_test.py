from modules.navwarn_mini.bulletin_splitter import split_navarea_bulletin


def test_does_not_split_on_cancel_reference_line():
    text = """
NAVAREA IV 145/26 081530 UTC MAR 26
DRILLING OPERATION IN POSITION 25-10N 090-20W.
CANCEL NAVAREA IV 144/26.

NAVAREA IV 146/26 081700 UTC MAR 26
BUOY ADRIFT IN POSITION 26-10N 091-20W.
""".strip()

    parts = split_navarea_bulletin(text)
    assert len(parts) == 2
    assert parts[0]["warning_id"] == "NAVAREA IV 145/26"
    assert "CANCEL NAVAREA IV 144/26" in parts[0]["raw_text"]
    assert parts[1]["warning_id"] == "NAVAREA IV 146/26"


def test_does_not_split_on_body_reference():
    text = """
NAVAREA IV 200/26 091200 UTC MAR 26
THIS WARNING REFERS TO NAVAREA IV 155/26 AND NAVAREA IV 156/26.
HAZARD IN POSITION 20-00N 060-00W.
""".strip()

    parts = split_navarea_bulletin(text)
    assert len(parts) == 1
    assert parts[0]["warning_id"] == "NAVAREA IV 200/26"


def test_repeated_warning_id_is_not_resplit():
    text = """
NAVAREA IV 210/26 091500 UTC MAR 26
INITIAL TEXT.

NAVAREA IV 210/26
REFERENCE ONLY FROM BAD OCR ECHO.

NAVAREA IV 211/26 091700 UTC MAR 26
SECOND WARNING.
""".strip()

    parts = split_navarea_bulletin(text)
    assert len(parts) == 2
    assert parts[0]["warning_id"] == "NAVAREA IV 210/26"
    assert parts[1]["warning_id"] == "NAVAREA IV 211/26"
    
from modules.navwarn_mini.bulletin_splitter import split_navarea_bulletin

def test_in_force_list_does_not_create_false_splits():
    text = """
NAVAREA IV 300/26 101200 UTC MAR 26
1. IN FORCE WARNINGS AT 101200 UTC MAR 26:
NAVAREA IV 210/26
NAVAREA IV 211/26
NAVAREA IV 250/26
2. CANCEL THIS MSG 111200 UTC MAR 26.
""".strip()

    parts = split_navarea_bulletin(text)
    assert len(parts) == 1
    assert parts[0]["warning_id"] == "NAVAREA IV 300/26"
    
def test_bare_id_inside_in_force_block_is_not_header():
    text = """
NAVAREA IV 300/26 101200 UTC MAR 26
1. IN FORCE WARNINGS AT 101200 UTC MAR 26:
NAVAREA IV 210/26
NAVAREA IV 211/26
NAVAREA IV 250/26
2. CANCEL THIS MSG 111200 UTC MAR 26.
""".strip()

    parts = split_navarea_bulletin(text)
    assert len(parts) == 1
    assert parts[0]["warning_id"] == "NAVAREA IV 300/26"


def test_bare_id_can_start_real_warning_when_followed_by_body():
    text = """
NAVAREA IV 320/26
DRILLING OPERATIONS IN POSITION 25-10N 090-20W.

NAVAREA IV 321/26 101500 UTC MAR 26
BUOY ADRIFT IN POSITION 26-10N 091-20W.
""".strip()

    parts = split_navarea_bulletin(text)
    assert len(parts) == 2
    assert parts[0]["warning_id"] == "NAVAREA IV 320/26"
    assert parts[1]["warning_id"] == "NAVAREA IV 321/26"