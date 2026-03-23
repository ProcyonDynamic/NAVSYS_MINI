from __future__ import annotations

from typing import Dict, List

from modules.portalis_mini.crew_service import create_crew, add_document_to_crew, list_crew
from modules.portalis_mini.certificate_registry import save_certificate


def apply_ship_to_state(state, ship_data: Dict[str, str]):
    state.vessel.name = ship_data.get("ship_name", "") or state.vessel.name
    state.vessel.imo_number = ship_data.get("imo", "") or state.vessel.imo_number
    state.vessel.call_sign = ship_data.get("call_sign", "") or state.vessel.call_sign
    state.vessel.flag_state = ship_data.get("flag", "") or state.vessel.flag_state
    return state


def import_crew_rows(portalis_root, crew_rows: List[Dict[str, str]]):
    created_ids = []

    for row in crew_rows:
        family = row.get("Family Name", "") or row.get("Surname", "")
        given = row.get("Given Name", "") or row.get("First Name", "")
        middle = row.get("Middle Name", "")
        full_name = " ".join(x for x in [given, middle, family] if x).strip()
        rank = row.get("Rank", "")

        if not full_name:
            continue

        crew_id = create_crew(portalis_root, full_name, rank)
        created_ids.append(crew_id)

        passport_no = row.get("Passport No.", "") or row.get("Passport Number", "")
        nationality = row.get("Nationality", "")
        dob = row.get("Date of Birth", "") or row.get("DOB", "")

        if passport_no:
            add_document_to_crew(
                portalis_root,
                crew_id,
                doc_type="PASSPORT",
                doc_subtype="",
                document_number=passport_no,
                country=nationality,
                issue_date="",
                expiry_date="",
                is_primary=True,
                status="ACTIVE",
                source_file="Arrival Database",
                confidence="0.95",
                notes=f"DOB: {dob}",
            )

    return created_ids


def import_certificates(portalis_root, certs: List[Dict[str, str]]):
    for cert in certs:
        save_certificate(
            portalis_root,
            name=cert.get("name", ""),
            number=cert.get("number", ""),
            issuer=cert.get("issuer", ""),
            issue_date=cert.get("issue_date", ""),
            expiry_date=cert.get("expiry_date", ""),
            notes=f"Last survey: {cert.get('last_survey_date', '')} | Source: {cert.get('source_file', '')}",
        )