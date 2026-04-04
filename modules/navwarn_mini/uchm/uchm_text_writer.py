from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .uchm_footer import write_tail


@dataclass
class BasicTextWriteResult:
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


def _text_offsets_from_descriptor(descriptor: dict[str, object]) -> dict[str, int]:
    raw = descriptor["text_offsets"]
    return {
        "metadata_word": int(raw["metadata_word"]),
        "text_start": int(raw["text_start"]),
        "text_capacity": int(raw["text_capacity"]),
    }


def _scale_offsets_from_descriptor(descriptor: dict[str, object]) -> dict[str, int]:
    raw = descriptor["scale_offsets"]
    return {
        "min": int(raw["min"]),
        "max": int(raw["max"]),
    }


def _anchor_offsets_from_descriptor(descriptor: dict[str, object]) -> dict[str, int]:
    raw = descriptor["anchor_offsets"]
    return {
        "lat": int(raw["lat"]),
        "lon": int(raw["lon"]),
    }


def _encode_degree(value: float, descriptor: dict[str, object]) -> int:
    degree_scale = int(descriptor["degree_scale"])
    return int(round(float(value) * degree_scale))


def load_donor_text_packet(
    descriptor: dict[str, object],
    donor_path: str | Path | None = None,
) -> bytearray:
    path = _donor_path_from_descriptor(descriptor, donor_path)
    if not path.exists():
        raise FileNotFoundError(f"Donor text packet not found: {path}")
    return bytearray(path.read_bytes())


def mutate_text_content(
    packet: bytearray,
    *,
    descriptor: dict[str, object],
    text: str,
) -> bytearray:
    text_offsets = _text_offsets_from_descriptor(descriptor)
    normalized = (text or "").strip().upper()
    if not normalized:
        raise ValueError("Native donor text path requires non-empty text content")
    try:
        encoded = normalized.encode("ascii")
    except UnicodeEncodeError as exc:
        raise ValueError("Native donor text path currently supports ASCII text only") from exc

    capacity = text_offsets["text_capacity"]
    if len(encoded) > capacity:
        raise ValueError(
            f"Native donor text path currently supports at most {capacity} ASCII bytes, got {len(encoded)}"
        )

    start = text_offsets["text_start"]
    end = start + capacity
    packet[start:end] = b"\x00" * capacity
    packet[start:start + len(encoded)] = encoded
    return packet


def mutate_text_metadata(
    packet: bytearray,
    *,
    descriptor: dict[str, object],
    anchor_lat: float,
    anchor_lon: float,
    metadata_word: int | None = None,
    scamin: int | None = None,
    scamax: int | None = None,
) -> bytearray:
    text_offsets = _text_offsets_from_descriptor(descriptor)
    expected_metadata_word = int(descriptor["default_metadata_word"])
    if metadata_word is not None and int(metadata_word) != expected_metadata_word:
        raise ValueError(
            "Native donor text path currently supports only the donor-compatible metadata word "
            f"{expected_metadata_word:#010x}"
        )

    _write_u32_le(packet, text_offsets["metadata_word"], expected_metadata_word)

    scale_offsets = _scale_offsets_from_descriptor(descriptor)
    if scamin is not None:
        _write_u32_le(packet, scale_offsets["min"], scamin)
    if scamax is not None:
        _write_u32_le(packet, scale_offsets["max"], scamax)

    anchor_offsets = _anchor_offsets_from_descriptor(descriptor)
    _write_i32_le(packet, anchor_offsets["lat"], _encode_degree(anchor_lat, descriptor))
    _write_i32_le(packet, anchor_offsets["lon"], _encode_degree(anchor_lon, descriptor))
    return packet


def finalize_text_tail(packet: bytearray, *, descriptor: dict[str, object]) -> int:
    return write_tail(packet, family_constant=int(descriptor["family_constant"]))


def write_basic_text_from_donor(
    *,
    descriptor: dict[str, object],
    plot_path: str | Path,
    text: str,
    anchor_lat: float,
    anchor_lon: float,
    donor_path: str | Path | None = None,
    metadata_word: int | None = None,
    scamin: int | None = None,
    scamax: int | None = None,
) -> BasicTextWriteResult:
    donor = _donor_path_from_descriptor(descriptor, donor_path)
    packet = load_donor_text_packet(descriptor, donor)

    mutate_text_content(
        packet,
        descriptor=descriptor,
        text=text,
    )
    mutate_text_metadata(
        packet,
        descriptor=descriptor,
        anchor_lat=anchor_lat,
        anchor_lon=anchor_lon,
        metadata_word=metadata_word,
        scamin=int(descriptor["default_scamin"]) if scamin is None else scamin,
        scamax=int(descriptor["default_scamax"]) if scamax is None else scamax,
    )
    finalize_text_tail(packet, descriptor=descriptor)

    out_path = Path(plot_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(packet)

    return BasicTextWriteResult(
        ok=True,
        output_path=str(out_path),
        object_kind_handled=str(descriptor["object_kind"]),
        donor_path=str(donor),
        unsupported_reason="",
        mutated_fields=[
            "text_content_ascii",
            "text_metadata_word",
            "scale_scamin",
            "scale_scamax",
            "anchor_lat",
            "anchor_lon",
            "tail_crc32_xor_family",
        ],
    )
