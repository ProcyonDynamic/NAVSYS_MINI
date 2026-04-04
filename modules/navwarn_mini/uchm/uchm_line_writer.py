from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .uchm_footer import write_tail

LINE_OBJECT_RECORD_START = 0x0D0


@dataclass
class BasicLineWriteResult:
    ok: bool
    output_path: str
    object_kind_handled: str
    donor_path: str
    unsupported_reason: str = ""
    mutated_fields: list[str] | None = None


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


def _donor_path_from_descriptor(descriptor: dict[str, object], donor_path: str | Path | None = None) -> Path:
    if donor_path is not None:
        return Path(donor_path)
    return Path(descriptor["donor_file"])


def _style_offsets_from_descriptor(descriptor: dict[str, object]) -> list[int]:
    return [int(x) for x in descriptor["style_offsets"]]


def _scale_offsets_from_descriptor(descriptor: dict[str, object]) -> dict[str, int]:
    raw = descriptor["scale_offsets"]
    return {
        "min": int(raw["min"]),
        "max": int(raw["max"]),
    }


def _geometry_offsets_from_descriptor(descriptor: dict[str, object]) -> dict[str, int]:
    raw = descriptor["geometry_offsets"]
    return {
        "a_lat": int(raw["a_lat"]),
        "a_lon": int(raw["a_lon"]),
        "b_lat": int(raw["b_lat"]),
        "b_lon": int(raw["b_lon"]),
    }


def _encode_degree(value: float, descriptor: dict[str, object]) -> int:
    degree_scale = int(descriptor["degree_scale"])
    return int(round(float(value) * degree_scale))


def load_donor_line_packet(
    descriptor: dict[str, object],
    donor_path: str | Path | None = None,
) -> bytearray:
    path = _donor_path_from_descriptor(descriptor, donor_path)
    if not path.exists():
        raise FileNotFoundError(f"Donor line packet not found: {path}")
    return bytearray(path.read_bytes())


def mutate_line_style_tuple(
    packet: bytearray,
    *,
    descriptor: dict[str, object],
    line_type: int,
    width: int,
    color_no: int,
) -> bytearray:
    style_offsets = _style_offsets_from_descriptor(descriptor)
    style = bytes((
        int(line_type) & 0xFF,
        int(width) & 0xFF,
        int(color_no) & 0xFF,
        0x00,
    ))
    for offset in style_offsets:
        packet[offset:offset + 4] = style
    return packet


def mutate_line_scale_fields(
    packet: bytearray,
    *,
    descriptor: dict[str, object],
    scamin: int | None = None,
    scamax: int | None = None,
) -> bytearray:
    scale_offsets = _scale_offsets_from_descriptor(descriptor)
    if scamin is not None:
        _write_u32_le(packet, scale_offsets["min"], scamin)
    if scamax is not None:
        _write_u32_le(packet, scale_offsets["max"], scamax)
    return packet


def mutate_line_geometry_fields(
    packet: bytearray,
    *,
    descriptor: dict[str, object],
    start_lat: float,
    start_lon: float,
    end_lat: float,
    end_lon: float,
) -> bytearray:
    geometry_offsets = _geometry_offsets_from_descriptor(descriptor)
    _write_i32_le(packet, geometry_offsets["a_lat"], _encode_degree(start_lat, descriptor))
    _write_i32_le(packet, geometry_offsets["a_lon"], _encode_degree(start_lon, descriptor))
    _write_i32_le(packet, geometry_offsets["b_lat"], _encode_degree(end_lat, descriptor))
    _write_i32_le(packet, geometry_offsets["b_lon"], _encode_degree(end_lon, descriptor))
    return packet


def finalize_line_tail(packet: bytearray, *, descriptor: dict[str, object]) -> int:
    return write_tail(packet, family_constant=int(descriptor["family_constant"]))


def build_basic_line_packet_from_donor(
    *,
    descriptor: dict[str, object],
    start_lat: float,
    start_lon: float,
    end_lat: float,
    end_lon: float,
    line_type: int,
    width: int,
    color_no: int,
    donor_path: str | Path | None = None,
    scamin: int | None = 100_000_000,
    scamax: int | None = 1_000,
) -> tuple[bytearray, str]:
    donor = _donor_path_from_descriptor(descriptor, donor_path)
    packet = load_donor_line_packet(descriptor, donor)

    mutate_line_style_tuple(
        packet,
        descriptor=descriptor,
        line_type=line_type,
        width=width,
        color_no=color_no,
    )
    mutate_line_scale_fields(
        packet,
        descriptor=descriptor,
        scamin=scamin,
        scamax=scamax,
    )
    mutate_line_geometry_fields(
        packet,
        descriptor=descriptor,
        start_lat=start_lat,
        start_lon=start_lon,
        end_lat=end_lat,
        end_lon=end_lon,
    )
    finalize_line_tail(packet, descriptor=descriptor)
    return packet, str(donor)


def write_basic_line_from_donor(
    *,
    descriptor: dict[str, object],
    plot_path: str | Path,
    start_lat: float,
    start_lon: float,
    end_lat: float,
    end_lon: float,
    line_type: int,
    width: int,
    color_no: int,
    donor_path: str | Path | None = None,
    scamin: int | None = 100_000_000,
    scamax: int | None = 1_000,
) -> BasicLineWriteResult:
    packet, donor = build_basic_line_packet_from_donor(
        descriptor=descriptor,
        start_lat=start_lat,
        start_lon=start_lon,
        end_lat=end_lat,
        end_lon=end_lon,
        line_type=line_type,
        width=width,
        color_no=color_no,
        donor_path=donor_path,
        scamin=scamin,
        scamax=scamax,
    )

    out_path = Path(plot_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(packet)

    return BasicLineWriteResult(
        ok=True,
        output_path=str(out_path),
        object_kind_handled=str(descriptor["object_kind"]),
        donor_path=str(donor),
        unsupported_reason="",
        mutated_fields=[
            "style_tuple_primary",
            "style_tuple_mirrored",
            "scale_scamin",
            "scale_scamax",
            "point_a_lat",
            "point_a_lon",
            "point_b_lat",
            "point_b_lon",
            "tail_crc32_xor_family",
        ],
    )
