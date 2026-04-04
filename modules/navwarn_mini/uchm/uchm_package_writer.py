from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..warning_plot_builder_service import PlotObject
from .uchm_family_constant_registry import LINE_REPEATED
from .uchm_footer import write_tail
from .uchm_line_writer import LINE_OBJECT_RECORD_START, build_basic_line_packet_from_donor
from .uchm_point_writer import POINT_OBJECT_RECORD_START, build_basic_point_packet_from_donor

FIRST_PACKET_TAIL_SIZE = 4


@dataclass
class UchmObjectPacket:
    object_kind: str
    descriptor: dict[str, object]
    donor_path: str
    packet: bytearray
    record_start_offset: int


@dataclass
class PackageWriteResult:
    ok: bool
    output_path: str
    object_kind_handled: str
    donor_paths: list[str]
    package_family_constant: int
    unsupported_reason: str = ""
    exported_object_count: int = 0


def _write_u32_le(data: bytearray, offset: int, value: int) -> None:
    end = offset + 4
    if offset < 0 or end > len(data):
        raise ValueError(f"Need 4 writable bytes at offset {offset}, buffer size is {len(data)}")
    data[offset:end] = int(value & 0xFFFFFFFF).to_bytes(4, byteorder="little", signed=False)


def assemble_object_packets(
    *,
    object_requests: list[dict[str, object]],
) -> list[UchmObjectPacket]:
    packets: list[UchmObjectPacket] = []
    for request in object_requests:
        object_kind = str(request["object_kind"]).upper()
        descriptor = request["descriptor"]
        if object_kind == "LINE":
            packet, donor_path = build_basic_line_packet_from_donor(
                descriptor=descriptor,
                start_lat=float(request["start_lat"]),
                start_lon=float(request["start_lon"]),
                end_lat=float(request["end_lat"]),
                end_lon=float(request["end_lon"]),
                line_type=int(request["line_type"]),
                width=int(request["width"]),
                color_no=int(request["color_no"]),
            )
            packets.append(
                UchmObjectPacket(
                    object_kind="LINE",
                    descriptor=descriptor,
                    donor_path=donor_path,
                    packet=packet,
                    record_start_offset=LINE_OBJECT_RECORD_START,
                )
            )
            continue

        if object_kind == "POINT":
            packet, donor_path = build_basic_point_packet_from_donor(
                descriptor=descriptor,
                lat=float(request["lat"]),
                lon=float(request["lon"]),
                symbol_control=int(request["symbol_control"]),
            )
            packets.append(
                UchmObjectPacket(
                    object_kind="POINT",
                    descriptor=descriptor,
                    donor_path=donor_path,
                    packet=packet,
                    record_start_offset=POINT_OBJECT_RECORD_START,
                )
            )
            continue

        raise ValueError(f"Unsupported object_kind for package assembly: {object_kind}")

    return packets


def build_multi_object_payload(
    *,
    object_packets: list[UchmObjectPacket],
) -> bytearray:
    if not object_packets:
        raise ValueError("Need at least one object packet to build package payload")

    payload = bytearray(object_packets[0].packet[:-FIRST_PACKET_TAIL_SIZE])

    for idx, packet_info in enumerate(object_packets[1:], start=1):
        chunk = packet_info.packet[packet_info.record_start_offset:]
        if idx < len(object_packets) - 1:
            chunk = chunk[:-FIRST_PACKET_TAIL_SIZE]
        payload.extend(chunk)

    return payload


def finalize_package_tail(
    packet: bytearray,
    *,
    package_family_constant: int,
) -> int:
    logical_end = len(packet) - 4
    _write_u32_le(packet, 0x40, logical_end)
    return write_tail(packet, family_constant=package_family_constant, logical_end=logical_end)


def write_multi_object_package(
    *,
    plot_objects: list[PlotObject],
    object_requests: list[dict[str, object]],
    plot_path: str | Path,
) -> PackageWriteResult:
    if not plot_objects:
        raise ValueError("No plot objects supplied for multi-object package write")
    if len(plot_objects) > 2:
        raise ValueError(f"Native package writer currently supports at most 2 objects, got {len(plot_objects)}")

    packets = assemble_object_packets(object_requests=object_requests)
    payload = build_multi_object_payload(object_packets=packets)

    kinds = [packet.object_kind for packet in packets]
    if all(kind == "LINE" for kind in kinds):
        package_family_constant = LINE_REPEATED
    else:
        # Mixed LINE/POINT and POINT/POINT package family derivation is not proven yet,
        # so keep the existing first object family constant as a narrow provisional lane.
        package_family_constant = int(packets[0].descriptor["family_constant"])

    finalize_package_tail(payload, package_family_constant=package_family_constant)

    out_path = Path(plot_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(payload)

    object_kind_handled = "+".join(kinds)
    return PackageWriteResult(
        ok=True,
        output_path=str(out_path),
        object_kind_handled=object_kind_handled,
        donor_paths=[packet.donor_path for packet in packets],
        package_family_constant=package_family_constant,
        unsupported_reason="",
        exported_object_count=len(packets),
    )
