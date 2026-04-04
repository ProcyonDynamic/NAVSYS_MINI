from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .uchm_footer import compute_crc32_payload, read_stored_tail, write_tail
from .uchm_donor_registry import get_line_basic_descriptor
from .uchm_line_writer import build_basic_line_packet_from_donor

TWO_LINE_PACKAGE_DONOR = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "jrc_usercharts" / "L07_two_lines.uchm"
FIRST_RECORD_STATE_OFFSET = 0x0CC
FIRST_RECORD_STATE_SIZE = 4

FIRST_LINE_STYLE_OFFSETS = (0x170, 0x1C4)
FIRST_LINE_SCALE_OFFSETS = {"min": 0x0D4, "max": 0x0D8}
FIRST_LINE_GEOMETRY_OFFSETS = {"a_lat": 0x174, "a_lon": 0x178, "b_lat": 0x1C8, "b_lon": 0x1CC}

SECOND_LINE_STYLE_OFFSETS = (0x270, 0x2C4)
SECOND_LINE_SCALE_OFFSETS = {"min": 0x1D4, "max": 0x1D8}
SECOND_LINE_GEOMETRY_OFFSETS = {"a_lat": 0x274, "a_lon": 0x278, "b_lat": 0x2C8, "b_lon": 0x2CC}

PRESERVED_PACKAGE_RANGES = (
    (0x44, 0x47),
    (0xCC, 0xCF),
)


@dataclass
class TwoLinePackageWriteResult:
    ok: bool
    output_path: str
    object_kind_handled: str
    donor_path: str
    package_family_constant: int
    unsupported_reason: str = ""


def _write_i32_le(data: bytearray, offset: int, value: int) -> None:
    end = offset + 4
    if offset < 0 or end > len(data):
        raise ValueError(f"Need 4 writable bytes at offset {offset}, buffer size is {len(data)}")
    data[offset:end] = int(value).to_bytes(4, byteorder="little", signed=True)


def _write_u32_le(data: bytearray, offset: int, value: int) -> None:
    end = offset + 4
    if offset < 0 or end > len(data):
        raise ValueError(f"Need 4 writable bytes at offset {offset}, buffer size is {len(data)}")
    data[offset:end] = int(value & 0xFFFFFFFF).to_bytes(4, byteorder="little", signed=False)


def _encode_degree(value: float, degree_scale: int = 1_536_000) -> int:
    return int(round(float(value) * degree_scale))


def _style_bytes(*, line_type: int, width: int, color_no: int) -> bytes:
    return bytes((
        int(line_type) & 0xFF,
        int(width) & 0xFF,
        int(color_no) & 0xFF,
        0x00,
    ))


def _donor_family_constant(donor_packet: bytes | bytearray) -> int:
    return compute_crc32_payload(donor_packet) ^ read_stored_tail(donor_packet)


def _mutate_line_body(
    packet: bytearray,
    *,
    style_offsets: tuple[int, int],
    scale_offsets: dict[str, int],
    geometry_offsets: dict[str, int],
    start_lat: float,
    start_lon: float,
    end_lat: float,
    end_lon: float,
    line_type: int,
    width: int,
    color_no: int,
    scamin: int,
    scamax: int,
) -> None:
    style = _style_bytes(line_type=line_type, width=width, color_no=color_no)
    for offset in style_offsets:
        packet[offset:offset + 4] = style

    _write_u32_le(packet, scale_offsets["min"], scamin)
    _write_u32_le(packet, scale_offsets["max"], scamax)

    _write_i32_le(packet, geometry_offsets["a_lat"], _encode_degree(start_lat))
    _write_i32_le(packet, geometry_offsets["a_lon"], _encode_degree(start_lon))
    _write_i32_le(packet, geometry_offsets["b_lat"], _encode_degree(end_lat))
    _write_i32_le(packet, geometry_offsets["b_lon"], _encode_degree(end_lon))


def load_two_line_package_donor() -> tuple[bytearray, int]:
    if not TWO_LINE_PACKAGE_DONOR.exists():
        raise FileNotFoundError(f"Two-line package donor not found: {TWO_LINE_PACKAGE_DONOR}")
    packet = bytearray(TWO_LINE_PACKAGE_DONOR.read_bytes())
    return packet, _donor_family_constant(packet)


def mutate_first_line_body(
    packet: bytearray,
    *,
    start_lat: float,
    start_lon: float,
    end_lat: float,
    end_lon: float,
    line_type: int,
    width: int,
    color_no: int,
    scamin: int = 100_000_000,
    scamax: int = 1_000,
) -> None:
    _mutate_line_body(
        packet,
        style_offsets=FIRST_LINE_STYLE_OFFSETS,
        scale_offsets=FIRST_LINE_SCALE_OFFSETS,
        geometry_offsets=FIRST_LINE_GEOMETRY_OFFSETS,
        start_lat=start_lat,
        start_lon=start_lon,
        end_lat=end_lat,
        end_lon=end_lon,
        line_type=line_type,
        width=width,
        color_no=color_no,
        scamin=scamin,
        scamax=scamax,
    )


def mutate_second_line_body(
    packet: bytearray,
    *,
    start_lat: float,
    start_lon: float,
    end_lat: float,
    end_lon: float,
    line_type: int,
    width: int,
    color_no: int,
    scamin: int = 100_000_000,
    scamax: int = 1_000,
) -> None:
    _mutate_line_body(
        packet,
        style_offsets=SECOND_LINE_STYLE_OFFSETS,
        scale_offsets=SECOND_LINE_SCALE_OFFSETS,
        geometry_offsets=SECOND_LINE_GEOMETRY_OFFSETS,
        start_lat=start_lat,
        start_lon=start_lon,
        end_lat=end_lat,
        end_lon=end_lon,
        line_type=line_type,
        width=width,
        color_no=color_no,
        scamin=scamin,
        scamax=scamax,
    )


def finalize_tail_only(packet: bytearray, *, family_constant: int) -> int:
    return write_tail(packet, family_constant=family_constant)


def write_two_line_package_probe_cccf(
    *,
    plot_path: str | Path,
    first_line: dict[str, object],
) -> tuple[TwoLinePackageWriteResult, str]:
    packet, family_constant = load_two_line_package_donor()

    mutate_first_line_body(
        packet,
        start_lat=float(first_line["start_lat"]),
        start_lon=float(first_line["start_lon"]),
        end_lat=float(first_line["end_lat"]),
        end_lon=float(first_line["end_lon"]),
        line_type=int(first_line["line_type"]),
        width=int(first_line["width"]),
        color_no=int(first_line["color_no"]),
        scamin=int(first_line.get("scamin", 100_000_000)),
        scamax=int(first_line.get("scamax", 1_000)),
    )

    standalone_descriptor = get_line_basic_descriptor()
    standalone_packet, _ = build_basic_line_packet_from_donor(
        descriptor=standalone_descriptor,
        start_lat=float(first_line["start_lat"]),
        start_lon=float(first_line["start_lon"]),
        end_lat=float(first_line["end_lat"]),
        end_lon=float(first_line["end_lon"]),
        line_type=int(first_line["line_type"]),
        width=int(first_line["width"]),
        color_no=int(first_line["color_no"]),
        scamin=int(first_line.get("scamin", 100_000_000)),
        scamax=int(first_line.get("scamax", 1_000)),
    )
    copied_state = bytes(
        standalone_packet[FIRST_RECORD_STATE_OFFSET:FIRST_RECORD_STATE_OFFSET + FIRST_RECORD_STATE_SIZE]
    )
    packet[FIRST_RECORD_STATE_OFFSET:FIRST_RECORD_STATE_OFFSET + FIRST_RECORD_STATE_SIZE] = copied_state

    finalize_tail_only(packet, family_constant=family_constant)

    out_path = Path(plot_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(packet)

    return (
        TwoLinePackageWriteResult(
            ok=True,
            output_path=str(out_path),
            object_kind_handled="LINE+LINE",
            donor_path=str(TWO_LINE_PACKAGE_DONOR),
            package_family_constant=family_constant,
            unsupported_reason="",
        ),
        copied_state.hex(),
    )


def write_two_line_package_from_donor(
    *,
    plot_path: str | Path,
    first_line: dict[str, object],
    second_line: dict[str, object],
) -> TwoLinePackageWriteResult:
    packet, family_constant = load_two_line_package_donor()

    mutate_first_line_body(
        packet,
        start_lat=float(first_line["start_lat"]),
        start_lon=float(first_line["start_lon"]),
        end_lat=float(first_line["end_lat"]),
        end_lon=float(first_line["end_lon"]),
        line_type=int(first_line["line_type"]),
        width=int(first_line["width"]),
        color_no=int(first_line["color_no"]),
        scamin=int(first_line.get("scamin", 100_000_000)),
        scamax=int(first_line.get("scamax", 1_000)),
    )
    mutate_second_line_body(
        packet,
        start_lat=float(second_line["start_lat"]),
        start_lon=float(second_line["start_lon"]),
        end_lat=float(second_line["end_lat"]),
        end_lon=float(second_line["end_lon"]),
        line_type=int(second_line["line_type"]),
        width=int(second_line["width"]),
        color_no=int(second_line["color_no"]),
        scamin=int(second_line.get("scamin", 100_000_000)),
        scamax=int(second_line.get("scamax", 1_000)),
    )
    finalize_tail_only(packet, family_constant=family_constant)

    out_path = Path(plot_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(packet)

    return TwoLinePackageWriteResult(
        ok=True,
        output_path=str(out_path),
        object_kind_handled="LINE+LINE",
        donor_path=str(TWO_LINE_PACKAGE_DONOR),
        package_family_constant=family_constant,
        unsupported_reason="",
    )
