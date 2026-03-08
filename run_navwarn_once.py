from __future__ import annotations

from navwarn_mini.process_warning import process_warning_text


def _prompt_float(label: str) -> float | None:
    raw = input(label).strip()
    if raw == "":
        return None
    return float(raw)


def main() -> None:
    print("NAVSYS MINI – NAVWARN ONCE")
    print("-" * 32)

    navarea = input("NAVAREA (e.g. IV, V, VI): ").strip().upper() or "IV"
    warning_id = input("Warning ID: ").strip()
    title = input("Title: ").strip()
    source_kind = input("Source kind [MANUAL/WEB/NAVAREA/NAVTEX]: ").strip().upper() or "MANUAL"

    print("\nEnter ship position (blank to skip distance classification):")
    ship_lat = _prompt_float("Ship lat (decimal, N positive / S negative): ")
    ship_lon = _prompt_float("Ship lon (decimal, E positive / W negative): ")

    print("\nPaste raw warning text. End with a single line containing only ENDTEXT")
    lines = []
    while True:
        line = input()
        if line.strip() == "ENDTEXT":
            break
        lines.append(line)
    raw_text = "\n".join(lines).strip()

    if not raw_text:
        print("No warning text entered.")
        return

    res = process_warning_text(
        raw_text=raw_text,
        navarea=navarea,
        ship_lat=ship_lat,
        ship_lon=ship_lon,
        output_root=r"D:\NAVSYS_USB",
        warning_id=warning_id,
        title=title,
        source_kind=source_kind,
        operator_name="",
        vessel_name="",
    )

    print("\nRESULT")
    print("-" * 32)
    for k, v in res.items():
        print(f"{k}: {v}")


if __name__ == "__main__":
    main()