from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .uchm_footer import write_tail

POINT_OBJECT_RECORD_START = 0x0D0


@dataclass
class BasicPointWriteResult:
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


def _scale_offsets_from_descriptor(descriptor: dict[str, object]) -> dict[str, int]:
    raw = descriptor["scale_offsets"]
    return {
        "min": int(raw["min"]),
        "max": int(raw["max"]),
    }


def _geometry_offsets_from_descriptor(descriptor: dict[str, object]) -> dict[str, int]:
    raw = descriptor["geometry_offsets"]
    return {
        "lat": int(raw["lat"]),
        "lon": int(raw["lon"]),
    }


def _symbol_control_offset_from_descriptor(descriptor: dict[str, object]) -> int:
    return int(descriptor["symbol_control_offset"])


def _allowed_symbol_controls_from_descriptor(descriptor: dict[str, object]) -> set[int]:
    return {int(value) & 0xFF for value in descriptor["allowed_symbol_controls"]}


def _encode_degree(value: float, descriptor: dict[str, object]) -> int:
    degree_scale = int(descriptor["degree_scale"])
    return int(round(float(value) * degree_scale))


def load_donor_point_packet(
    descriptor: dict[str, object],
    donor_path: str | Path | None = None,
) -> bytearray:
    path = _donor_path_from_descriptor(descriptor, donor_path)
    if not path.exists():
        raise FileNotFoundError(f"Donor point packet not found: {path}")
    return bytearray(path.read_bytes())


def mutate_point_symbol_control(
    packet: bytearray,
    *,
    descriptor: dict[str, object],
    symbol_control: int | None = None,
) -> bytearray:
    offset = _symbol_control_offset_from_descriptor(descriptor)
    value = int(
        descriptor["default_symbol_control"] if symbol_control is None else symbol_control
    ) & 0xFF
    allowed_symbol_controls = _allowed_symbol_controls_from_descriptor(descriptor)
    if value not in allowed_symbol_controls:
        raise ValueError(
            "Unsupported native point symbol control "
            f"{value:#04x}; allowed values are {sorted(allowed_symbol_controls)}"
        )
    packet[offset] = value
    return packet


def mutate_point_scale_fields(
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


def mutate_point_geometry_fields(
    packet: bytearray,
    *,
    descriptor: dict[str, object],
    lat: float,
    lon: float,
) -> bytearray:
    geometry_offsets = _geometry_offsets_from_descriptor(descriptor)
    _write_i32_le(packet, geometry_offsets["lat"], _encode_degree(lat, descriptor))
    _write_i32_le(packet, geometry_offsets["lon"], _encode_degree(lon, descriptor))
    return packet


def finalize_point_tail(packet: bytearray, *, descriptor: dict[str, object]) -> int:
    return write_tail(packet, family_constant=int(descriptor["family_constant"]))


def build_basic_point_packet_from_donor(
    *,
    descriptor: dict[str, object],
    lat: float,
    lon: float,
    donor_path: str | Path | None = None,
    symbol_control: int | None = None,
    scamin: int | None = 100_000_000,
    scamax: int | None = 1_000,
) -> tuple[bytearray, str]:
    donor = _donor_path_from_descriptor(descriptor, donor_path)
    packet = load_donor_point_packet(descriptor, donor)

    mutate_point_symbol_control(
        packet,
        descriptor=descriptor,
        symbol_control=symbol_control,
    )
    mutate_point_scale_fields(
        packet,
        descriptor=descriptor,
        scamin=scamin,
        scamax=scamax,
    )
    mutate_point_geometry_fields(
        packet,
        descriptor=descriptor,
        lat=lat,
        lon=lon,
    )
    finalize_point_tail(packet, descriptor=descriptor)
    return packet, str(donor)


def write_basic_point_from_donor(
    *,
    descriptor: dict[str, object],
    plot_path: str | Path,
    lat: float,
    lon: float,
    donor_path: str | Path | None = None,
    symbol_control: int | None = None,
    scamin: int | None = 100_000_000,
    scamax: int | None = 1_000,
) -> BasicPointWriteResult:
    packet, donor = build_basic_point_packet_from_donor(
        descriptor=descriptor,
        lat=lat,
        lon=lon,
        donor_path=donor_path,
        symbol_control=symbol_control,
        scamin=scamin,
        scamax=scamax,
    )

    out_path = Path(plot_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(packet)

    return BasicPointWriteResult(
        ok=True,
        output_path=str(out_path),
        object_kind_handled=str(descriptor["object_kind"]),
        donor_path=str(donor),
        unsupported_reason="",
        mutated_fields=[
            "symbol_control",
            "scale_scamin",
            "scale_scamax",
            "point_lat",
            "point_lon",
            "tail_crc32_xor_family",
        ],
    )
