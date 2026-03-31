from __future__ import annotations

from .models import DocumentStatusRecord, PortalisState, VesselRecord, VoyageRecord


def _to_float_or_none(value):
    text = str(value or "").strip()
    if not text:
        return None

    try:
        return float(text.replace(",", ""))
    except ValueError:
        return None


def update_vessel_from_form(state: PortalisState, form: dict) -> PortalisState:
    current = state.vessel or VesselRecord()

    state.vessel = VesselRecord(
        vessel_id=current.vessel_id,
        name=form.get("name", "").strip(),
        imo_number=form.get("imo_number", "").strip() or None,
        call_sign=form.get("call_sign", "").strip() or None,
        flag_state=form.get("flag_state", "").strip() or None,
        vessel_type=form.get("vessel_type", "").strip() or None,
        gross_tonnage=_to_float_or_none(form.get("gross_tonnage", "")),
        net_tonnage=_to_float_or_none(form.get("net_tonnage", "")),
        deadweight=_to_float_or_none(form.get("deadweight", "")),
        owner_name=form.get("owner_name", "").strip() or None,
        operator_name=form.get("operator_name", "").strip() or None,
    )
    return state


def update_voyage_from_form(state: PortalisState, form: dict) -> PortalisState:
    current = state.voyage or VoyageRecord()

    arrival_port = form.get("arrival_port", "").strip()
    next_port = form.get("next_port", "").strip()

    state.voyage = VoyageRecord(
        voyage_id=current.voyage_id,
        voyage_number=form.get("voyage_no", form.get("voyage_number", "")).strip(),
        departure_port=form.get("departure_port", "").strip(),
        arrival_port=arrival_port,
        eta=form.get("eta", "").strip(),
        etb=form.get("etb", "").strip(),
        etc=form.get("etc", "").strip(),
        cargo_summary=form.get("cargo_summary", "").strip(),
        port_history=form.get("port_history", "").strip(),
        current_port=arrival_port,
        next_port=next_port,
    )
    return state


def update_documents_from_form(state: PortalisState, form: dict) -> PortalisState:
    updated = []

    for idx, existing in enumerate(state.documents):
        prefix = f"doc_{idx}_"
        sent = (prefix + "sent") in form
        updated.append(
            DocumentStatusRecord(
                doc_name=form.get(prefix + "name", existing.doc_name).strip(),
                required=(prefix + "required") in form,
                filled=(prefix + "filled") in form,
                printed=(prefix + "printed") in form,
                signed=(prefix + "signed") in form,
                recorded=(prefix + "recorded") in form,
                sent=sent,
                status="complete" if sent else "pending",
                notes=form.get(prefix + "notes", existing.notes).strip(),
            )
        )

    state.documents = updated
    return state
