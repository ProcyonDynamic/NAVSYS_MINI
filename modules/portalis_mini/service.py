from __future__ import annotations

from .models import PortalisState, VesselRecord, VoyageRecord, DocumentStatusRecord


def _to_float_or_none(v):
    s = (v or "").strip()
    if not s:
        return None
    try:
        return float(s.replace(",", ""))
    except ValueError:
        return None


def update_vessel_from_form(state: PortalisState, form: dict) -> PortalisState:
    state.vessel = VesselRecord(
        vessel_id=state.vessel.vessel_id,
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
        audit=state.vessel.audit,
    )
    return state


def update_voyage_from_form(state: PortalisState, form: dict) -> PortalisState:
    state.voyage = VoyageRecord(
        voyage_no=form.get("voyage_no", "").strip(),
        departure_port=form.get("departure_port", "").strip(),
        arrival_port=form.get("arrival_port", "").strip(),
        eta=form.get("eta", "").strip(),
        etb=form.get("etb", "").strip(),
        etc=form.get("etc", "").strip(),
        cargo_summary=form.get("cargo_summary", "").strip(),
        port_history=form.get("port_history", "").strip(),
    )
    return state


def update_documents_from_form(state: PortalisState, form: dict) -> PortalisState:
    docs = []
    for i, old in enumerate(state.documents):
        prefix = f"doc_{i}_"
        docs.append(
            DocumentStatusRecord(
                doc_name=form.get(prefix + "name", old.doc_name).strip(),
                required=(prefix + "required") in form,
                filled=(prefix + "filled") in form,
                printed=(prefix + "printed") in form,
                signed=(prefix + "signed") in form,
                recorded=(prefix + "recorded") in form,
                sent=(prefix + "sent") in form,
                notes=form.get(prefix + "notes", "").strip(),
            )
        )
    state.documents = docs
    return state