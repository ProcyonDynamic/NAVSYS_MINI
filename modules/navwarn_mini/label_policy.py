# modules/navwarn_mini/label_policy.py

LABEL_POLICY = {
    "POINT": 2,
    "LINE": 3,
    "AREA": 4,

    "DISTRESS": 5,
    "SAR": 4,
    "ICE": 3,
    "DEFAULT": 3,
}


def get_label_limit(geom_type: str | None, warning_type: str | None) -> int:
    if warning_type in LABEL_POLICY:
        return LABEL_POLICY[warning_type]

    if geom_type in LABEL_POLICY:
        return LABEL_POLICY[geom_type]

    return LABEL_POLICY["DEFAULT"]