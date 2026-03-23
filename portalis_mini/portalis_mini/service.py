from __future__ import annotations

from .models import PortalisState, VesselRecord, VoyageRecord, DocumentStatusRecord


def update_vessel_from_form(state: PortalisState, form: dict) -> PortalisState:
    state.vessel = VesselRecord(
        ship_name=form.get("ship_name", "").strip(),
        imo=form.get("imo", "").strip(),
        call_sign=form.get("call_sign", "").strip(),
        flag=form.get("flag", "").strip(),
        gross_tonnage=form.get("gross_tonnage", "").strip(),
        deadweight=form.get("deadweight", "").strip(),
        loa=form.get("loa", "").strip(),
        beam=form.get("beam", "").strip(),
        summer_draft=form.get("summer_draft", "").strip(),
        manager=form.get("manager", "").strip(),
        operator=form.get("operator", "").strip(),
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