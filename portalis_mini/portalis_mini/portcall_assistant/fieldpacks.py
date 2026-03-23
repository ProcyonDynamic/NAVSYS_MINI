from __future__ import annotations

from typing import Any, Dict, List

from .models import PortCallContext


class FieldPackMapper:
    def build_common_field_pack(self, context: PortCallContext) -> Dict[str, Any]:
        vessel = {k: v.value for k, v in context.vessel_profile.items()}
        voyage = {k: v.value for k, v in context.voyage_profile.items()}

        return {
            "vessel_name": vessel.get("vessel_name"),
            "imo_number": vessel.get("imo_number"),
            "call_sign": vessel.get("call_sign"),
            "flag_state": vessel.get("flag_state"),
            "gross_tonnage": vessel.get("gross_tonnage"),
            "net_tonnage": vessel.get("net_tonnage"),
            "deadweight": vessel.get("deadweight"),
            "loa_m": vessel.get("loa_m"),
            "beam_m": vessel.get("beam_m"),
            "current_port": voyage.get("current_port"),
            "last_port": voyage.get("last_port"),
            "next_port": voyage.get("next_port"),
            "eta": voyage.get("eta"),
            "etd": voyage.get("etd"),
            "berth": voyage.get("berth"),
            "terminal": voyage.get("terminal"),
            "agent": voyage.get("agent"),
            "voyage_number": voyage.get("voyage_number"),
            "reason_of_call": voyage.get("reason_of_call"),
            "cargo_summary": voyage.get("cargo_summary"),
            "persons_on_board": voyage.get("persons_on_board"),
            "crew_count": len(context.crew_registry),
        }

    def build_crew_rows(self, context: PortCallContext) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for member in context.crew_registry:
            rows.append(
                {
                    "full_name": member.get("full_name"),
                    "rank": member.get("rank"),
                    "nationality": member.get("nationality"),
                    "date_of_birth": member.get("date_of_birth"),
                    "place_of_birth": member.get("place_of_birth"),
                    "passport_number": member.get("passport_number"),
                    "passport_expiry": member.get("passport_expiry"),
                    "us_visa_number": member.get("us_visa_number"),
                    "us_visa_expiry": member.get("us_visa_expiry"),
                    "height_cm": member.get("height_cm"),
                    "weight_kg": member.get("weight_kg"),
                }
            )
        return rows
