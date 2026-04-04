from __future__ import annotations

import binascii


def read_u32_le(data: bytes | bytearray | memoryview, offset: int) -> int:
    chunk = bytes(data[offset : offset + 4])
    if len(chunk) != 4:
        raise ValueError(f"Need 4 bytes at offset {offset}, got {len(chunk)}")
    return int.from_bytes(chunk, byteorder="little", signed=False)


def write_u32_le(data: bytearray, offset: int, value: int) -> None:
    if offset < 0:
        raise ValueError(f"Offset must be non-negative, got {offset}")
    end = offset + 4
    if end > len(data):
        raise ValueError(f"Need 4 writable bytes at offset {offset}, buffer size is {len(data)}")
    data[offset:end] = int(value & 0xFFFFFFFF).to_bytes(4, byteorder="little", signed=False)


def read_logical_end(data: bytes | bytearray | memoryview) -> int:
    logical_end = len(data) - 4
    if logical_end < 0x40:
        raise ValueError("UCHM payload is too small to contain header and tail")
    return logical_end


def compute_crc32_payload(data: bytes | bytearray | memoryview, logical_end: int | None = None) -> int:
    end = read_logical_end(data) if logical_end is None else logical_end
    if end < 0x40:
        raise ValueError(f"Logical end before payload start: {end}")
    payload = bytes(data[0x40:end])
    return binascii.crc32(payload) & 0xFFFFFFFF


def compute_tail(
    data: bytes | bytearray | memoryview,
    family_constant: int,
    logical_end: int | None = None,
) -> int:
    crc = compute_crc32_payload(data, logical_end=logical_end)
    return (crc ^ int(family_constant)) & 0xFFFFFFFF


def read_stored_tail(data: bytes | bytearray | memoryview, logical_end: int | None = None) -> int:
    end = read_logical_end(data) if logical_end is None else logical_end
    return read_u32_le(data, end)


def verify_tail(
    data: bytes | bytearray | memoryview,
    family_constant: int,
    logical_end: int | None = None,
) -> bool:
    end = read_logical_end(data) if logical_end is None else logical_end
    expected = compute_tail(data, family_constant=family_constant, logical_end=end)
    stored = read_stored_tail(data, logical_end=end)
    return stored == expected


def write_tail(
    data: bytearray,
    family_constant: int,
    logical_end: int | None = None,
) -> int:
    end = read_logical_end(data) if logical_end is None else logical_end
    tail = compute_tail(data, family_constant=family_constant, logical_end=end)
    write_u32_le(data, end, tail)
    return tail
