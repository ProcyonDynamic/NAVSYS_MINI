from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from modules.portalis_mini.archive.document_registry import DocumentRegistry
from modules.portalis_mini.import_models import ImportRequest
from modules.portalis_mini.import_service import import_declared_document
from modules.portalis_mini.models import ReviewQueueItem, TCELiteEnvelope
from modules.portalis_mini.review_resolution_service import (
    ReviewResolutionCoupler,
    ReviewResolutionService,
)
from modules.portalis_mini.review_dashboard_service import (
    apply_alert_action,
    apply_assignment_action,
    apply_external_bridge_action,
    apply_incident_action,
    apply_notification_action,
    apply_reminder_action,
    apply_transport_action,
    apply_triage_action,
    apply_watch_action,
    build_alert_queue,
    build_cross_document_review_queue,
    build_dashboard_summary,
    build_dashboard_tce_delta,
    build_document_escalation_policies,
    build_notification_ledger,
    build_notification_queue,
    build_document_reminder_stage,
    build_document_routing_hints,
    build_document_sla_policies,
    build_reminder_queue,
    build_transport_queue,
    build_transport_requests,
    build_watch_queue,
    refresh_control_room_state,
)
from modules.portalis_mini.passport_review_service import (
    build_compare_ledger_entries,
    build_field_policy_packets,
    build_passport_candidate_bundles,
    build_passport_field_confidence,
    build_prioritized_field_queue,
    score_passport_field_conflicts,
    validate_passport_review_fields,
)
from modules.portalis_mini.service import (
    update_documents_from_form,
    update_vessel_from_form,
    update_voyage_from_form,
)
from modules.portalis_mini.storage import (
    load_portalis_state,
    load_review_queue,
    save_portalis_state,
    save_review_queue,
)


def test_state_defaults_and_roundtrip(tmp_path):
    state_path = tmp_path / "state.json"

    state = load_portalis_state(str(state_path))
    assert state.vessel.vessel_id == "default_vessel"
    assert state.voyage.voyage_id == "default_voyage"
    assert len(state.documents) == 4

    state.vessel.name = "MV TEST"
    state.voyage.arrival_port = "Houston"
    save_portalis_state(state, str(state_path))

    loaded = load_portalis_state(str(state_path))
    assert loaded.vessel.name == "MV TEST"
    assert loaded.voyage.arrival_port == "Houston"


def test_form_updates_use_single_truth_contract(tmp_path):
    state = load_portalis_state(str(tmp_path / "state.json"))
    form = {
        "name": "MV UNITY",
        "imo_number": "1234567",
        "call_sign": "ABCD",
        "flag_state": "Liberia",
        "vessel_type": "LNG",
        "voyage_no": "VOY-12",
        "departure_port": "Sabine Pass",
        "arrival_port": "Houston",
        "eta": "2026-04-01T12:00Z",
        "doc_0_name": "Crew List",
        "doc_0_required": "on",
        "doc_0_sent": "on",
    }

    state = update_vessel_from_form(state, form)
    state = update_voyage_from_form(state, form)
    state = update_documents_from_form(state, form)

    assert state.vessel.name == "MV UNITY"
    assert state.voyage.voyage_number == "VOY-12"
    assert state.voyage.current_port == "Houston"
    assert state.documents[0].sent is True
    assert state.documents[0].status == "complete"


def test_public_import_creates_manifest_and_review_queue(tmp_path, monkeypatch):
    portalis_root = tmp_path / "PORTALIS"
    portalis_root.mkdir(parents=True, exist_ok=True)
    source_path = tmp_path / "passport.pdf"
    source_path.write_bytes(b"fake pdf bytes")

    class FakeDocumentImportService:
        def __init__(self, root_dir: Path):
            self.root_dir = Path(root_dir)

        def import_document(self, doc_type, source_file, owner_entity="", owner_id=""):
            stored_dir = self.root_dir / "documents" / doc_type
            stored_dir.mkdir(parents=True, exist_ok=True)
            stored_file = stored_dir / source_file.name
            stored_file.write_bytes(source_file.read_bytes())

            registry = DocumentRegistry(self.root_dir)
            document_id = registry.register_document(
                doc_type="passport",
                owner_entity=owner_entity,
                owner_id=owner_id,
                source_file=stored_file,
                parsed_fields={"passport.number": "A1234567"},
                confidence=0.91,
                review_required=True,
                review_reasons=["Needs operator review"],
                warnings=["Needs operator review"],
                field_evidence={
                    "passport.number": {
                        "field_name": "passport.number",
                        "parsed_value": "A1234567",
                        "candidate_text": "Passport No A1234567",
                        "source_engine": "tesseract",
                        "source_kind": "text_line",
                        "source_method": "regex",
                        "notes": ["mapped_from:passport_number"],
                        "warnings": [],
                        "alternate_values": [],
                    }
                },
                field_validation={
                    "passport.number": {
                        "field_name": "passport.number",
                        "status": "PASS",
                        "normalized_value": "A1234567",
                        "validator_messages": ["Passport number format looks sane"],
                        "compared_fields": ["mrz"],
                    }
                },
                field_conflicts={
                    "passport.number": {
                        "field_name": "passport.number",
                        "agreement_present": True,
                        "agreement_source_count": 1,
                        "conflict_level": "NONE",
                        "compared_sources": ["tesseract:text_line:ocr"],
                        "warning_flags": [],
                        "rationale": ["Available evidence agrees on one value"],
                    }
                },
                field_confidence={
                    "passport.number": {
                        "field_name": "passport.number",
                        "confidence_score": 0.95,
                        "confidence_band": "HIGH",
                        "conflict_level": "NONE",
                        "agreement_sources": 1,
                        "warning_flags": [],
                        "recommended_action": "ACCEPTABLE",
                        "rationale": ["validation=PASS", "conflict=NONE"],
                    }
                },
                candidate_bundles={
                    "passport.number": {
                        "field_name": "passport.number",
                        "candidates": [
                            {
                                "candidate_id": "passport.number::ocr::text_line::0",
                                "field_name": "passport.number",
                                "candidate_value": "A1234567",
                            }
                        ],
                        "selected_candidate_id": "passport.number::ocr::text_line::0",
                        "selected_value": "A1234567",
                        "alternate_candidate_ids": [],
                        "agreement_summary": {"agreement_present": True},
                        "conflict_level": "NONE",
                        "confidence_summary": {"confidence_band": "HIGH"},
                        "recommended_action": "ACCEPTABLE",
                    }
                },
                compare_ledger=[
                    {
                        "document_id": "DOC_000001",
                        "field_name": "passport.number",
                        "compared_at": "2026-03-31T00:00:00Z",
                        "candidate_bundle_snapshot": {"selected_candidate_id": "passport.number::ocr::text_line::0"},
                        "selected_candidate_id": "passport.number::ocr::text_line::0",
                        "selected_value": "A1234567",
                        "conflict_level": "NONE",
                        "confidence_summary": {"confidence_band": "HIGH"},
                        "operator_override": False,
                        "operator_selected_value": "",
                        "rationale": [],
                        "decision_notes": "",
                        "review_status": "PENDING",
                    }
                ],
                accepted_candidate_refs={"passport.number": "passport.number::ocr::text_line::0"},
                operator_overrides={},
                tce_lite={
                    "WHAT": {"document_type": "passport", "field_keys": ["passport.number"]},
                    "WHO": {"owner_entity": owner_entity, "owner_id": owner_id},
                    "WHEN": {"imported_at": "2026-03-31T00:00:00Z"},
                    "WHERE": {"source_file": str(stored_file)},
                    "HOW": {"ocr_engine": "tesseract"},
                    "WHY": {"operational_reason": "Portalis import for Crew Passport"},
                },
                operational_reason="Portalis import for Crew Passport",
            )
            return {
                "ok": True,
                "document_id": document_id,
                "doc_type": "passport",
                "stored_file": str(stored_file),
                "owner_entity": owner_entity,
                "owner_id": owner_id,
                "confidence": 0.91,
                "parsed_fields": {"passport.number": "A1234567"},
                "field_evidence": {
                    "passport.number": {
                        "field_name": "passport.number",
                        "parsed_value": "A1234567",
                    }
                },
                "field_validation": {
                    "passport.number": {"status": "PASS"}
                },
                "field_conflicts": {
                    "passport.number": {"conflict_level": "NONE"}
                },
                "field_confidence": {
                    "passport.number": {"confidence_band": "HIGH", "recommended_action": "ACCEPTABLE"}
                },
                "review_required": True,
                "review_reasons": ["Needs operator review"],
                "warnings": ["Needs operator review"],
                "crew_record_path": None,
                "crew_update_error": None,
            }

    monkeypatch.setattr("modules.portalis_mini.import_service.DocumentImportService", FakeDocumentImportService)

    result = import_declared_document(
        ImportRequest(
            source_path=str(source_path),
            document_type="CREW_PASSPORT",
            declared_entity_kind="crew",
            declared_entity_id="crew_test_001",
        ),
        portalis_root=portalis_root,
    )

    assert result.ok is True
    assert result.manifest_path is not None
    manifest = json.loads(Path(result.manifest_path).read_text(encoding="utf-8"))
    assert manifest["result"]["review_required"] is True

    review_items = load_review_queue(portalis_root)
    assert len(review_items) == 1
    assert review_items[0].document_id.startswith("DOC_")
    assert review_items[0].tce.WHAT["document_type"] == "passport"
    assert review_items[0].field_evidence["passport.number"]["source_engine"] == "tesseract"
    assert review_items[0].field_validation["passport.number"]["status"] == "PASS"
    assert review_items[0].field_conflicts["passport.number"]["conflict_level"] == "NONE"
    assert review_items[0].field_confidence["passport.number"]["confidence_band"] == "HIGH"
    assert review_items[0].candidate_bundles["passport.number"]["selected_value"] == "A1234567"
    assert review_items[0].compare_ledger[0]["field_name"] == "passport.number"


def test_review_resolution_accepts_edited_fields_and_writes_registry_and_crew(tmp_path):
    portalis_root = tmp_path / "PORTALIS"
    crew_root = portalis_root / "crew" / "crew_test_001"
    crew_root.mkdir(parents=True, exist_ok=True)
    (crew_root / "record.json").write_text(
        json.dumps({"crew_id": "crew_test_001", "name": "", "documents": []}),
        encoding="utf-8",
    )

    source_file = portalis_root / "documents" / "CREW_PASSPORT" / "passport.pdf"
    source_file.parent.mkdir(parents=True, exist_ok=True)
    source_file.write_bytes(b"fake pdf bytes")

    registry = DocumentRegistry(portalis_root)
    document_id = registry.register_document(
        doc_type="passport",
        owner_entity="crew",
        owner_id="crew_test_001",
        source_file=source_file,
        parsed_fields={"passport.number": "A1234567", "crew.given_names": "OLD"},
        confidence=0.88,
        review_required=True,
        review_reasons=["Name mismatch"],
        warnings=["Name mismatch"],
        field_evidence={
            "passport.number": {
                "field_name": "passport.number",
                "parsed_value": "A1234567",
                "candidate_text": "P<UTOERIKSSON<<ANNA<MARIA<<<<<<<<<<<",
                "source_engine": "tesseract",
                "source_kind": "mrz_field",
                "source_method": "mrz",
                "notes": ["mapped_from:passport_number"],
                "warnings": [],
                "alternate_values": [],
            },
            "crew.given_names": {
                "field_name": "crew.given_names",
                "parsed_value": "OLD",
                "candidate_text": "Given names OLD",
                "source_engine": "tesseract",
                "source_kind": "text_line",
                "source_method": "keyword_window",
                "notes": ["mapped_from:given_names"],
                "warnings": [],
                "alternate_values": [],
            },
        },
        field_validation={},
        field_conflicts={},
        field_confidence={},
        candidate_bundles={},
        compare_ledger=[],
        accepted_candidate_refs={},
        operator_overrides={},
        tce_lite={
            "WHAT": {"document_type": "passport"},
            "WHO": {"owner_entity": "crew", "owner_id": "crew_test_001"},
            "WHEN": {"imported_at": "2026-03-31T00:00:00Z"},
            "WHERE": {"source_file": str(source_file)},
            "HOW": {"ocr_engine": "tesseract"},
            "WHY": {"operational_reason": "Portalis import"},
        },
    )

    save_review_queue(
        portalis_root,
        [
            ReviewQueueItem(
                document_id=document_id,
                review_required=True,
                review_reasons=["Name mismatch"],
                parsed_fields={"passport.number": "A1234567", "crew.given_names": "OLD"},
                field_evidence={
                    "passport.number": {
                        "field_name": "passport.number",
                        "parsed_value": "A1234567",
                        "candidate_text": "P<UTOERIKSSON<<ANNA<MARIA<<<<<<<<<<<",
                        "source_engine": "tesseract",
                        "source_kind": "mrz_field",
                        "source_method": "mrz",
                        "notes": ["mapped_from:passport_number"],
                        "warnings": [],
                        "alternate_values": [],
                    },
                    "crew.given_names": {
                        "field_name": "crew.given_names",
                        "parsed_value": "OLD",
                        "candidate_text": "Given names OLD",
                        "source_engine": "tesseract",
                        "source_kind": "text_line",
                        "source_method": "keyword_window",
                        "notes": ["mapped_from:given_names"],
                        "warnings": [],
                        "alternate_values": [],
                    },
                },
                field_conflicts={},
                field_confidence={},
                candidate_bundles={},
                compare_ledger=[],
                accepted_candidate_refs={},
                operator_overrides={},
                status="PENDING",
                tce=TCELiteEnvelope(
                    WHAT={"document_type": "passport"},
                    WHO={"owner_entity": "crew", "owner_id": "crew_test_001"},
                    WHEN={"imported_at": "2026-03-31T00:00:00Z"},
                    WHERE={"source_file": str(source_file)},
                    HOW={"ocr_engine": "tesseract"},
                    WHY={"operational_reason": "Portalis import"},
                ),
                created_at="2026-03-31T00:00:00Z",
                updated_at="2026-03-31T00:00:00Z",
            )
        ],
    )

    service = ReviewResolutionService(portalis_root)
    result = service.resolve(
        ReviewResolutionCoupler(
            review_item=service.get_review_item(document_id),
            operator_action="RESOLVE",
            edited_fields={"crew.given_names": "EDWARD"},
            operator_name="watchkeeper",
            resolution_reason="Verified against passport image",
        )
    )

    assert result.resolution_packet.review_status == "RESOLVED"
    assert result.resolution_packet.accepted_fields["crew.given_names"] == "EDWARD"

    updated_doc = registry.get_document(document_id)
    assert updated_doc["parsed_fields"]["crew.given_names"] == "OLD"
    assert updated_doc["accepted_fields"]["crew.given_names"] == "EDWARD"
    assert updated_doc["field_evidence"]["passport.number"]["source_kind"] == "mrz_field"
    assert updated_doc["field_validation"]["passport.number"]["status"] in {"PASS", "WARN"}
    assert updated_doc["field_conflicts"]["passport.number"]["conflict_level"] in {"NONE", "LOW", "MEDIUM", "HIGH"}
    assert updated_doc["field_confidence"]["passport.number"]["recommended_action"] in {"ACCEPTABLE", "REVIEW", "HIGH_ATTENTION"}
    assert isinstance(updated_doc["compare_ledger"], list)
    assert updated_doc["tce_lite"]["HOW"]["resolved_by"] == "watchkeeper"
    assert "validation_summary" in updated_doc["tce_lite"]["HOW"]
    assert "conflict_summary" in updated_doc["tce_lite"]["HOW"]
    assert "confidence_summary" in updated_doc["tce_lite"]["HOW"]
    assert updated_doc["tce_lite"]["WHY"]["resolution_reason"] == "Verified against passport image"

    review_items = load_review_queue(portalis_root)
    assert review_items[0].status == "RESOLVED"
    assert review_items[0].accepted_fields["crew.given_names"] == "EDWARD"
    assert review_items[0].field_validation["crew.given_names"]["normalized_value"] == "EDWARD"
    assert review_items[0].field_confidence["crew.given_names"]["recommended_action"] in {"ACCEPTABLE", "REVIEW", "HIGH_ATTENTION"}

    crew_record = json.loads((crew_root / "record.json").read_text(encoding="utf-8"))
    assert crew_record["given_name"] == "EDWARD"


def test_passport_validation_reports_fail_for_bad_dates():
    evidence = {
        "passport.number": {
            "alternate_values": [{"value": "A1234567", "source_kind": "mrz_field"}],
            "source_kind": "text_line",
        }
    }
    results = validate_passport_review_fields(
        {
            "passport.number": "B7654321",
            "crew.surname": "DOE",
            "crew.given_names": "JANE",
            "crew.date_of_birth": "2035-01-01",
            "passport.issue_date": "2025-01-01",
            "passport.expiry_date": "2024-01-01",
        },
        evidence,
    )

    assert results["passport.number"]["status"] == "WARN"
    assert results["crew.date_of_birth"]["status"] == "FAIL"
    assert results["passport.expiry_date"]["status"] == "FAIL"


def test_passport_conflict_and_confidence_packets_flag_disagreement():
    evidence = {
        "passport.number": {
            "candidate_text": "B7654321",
            "source_engine": "tesseract",
            "source_kind": "text_line",
            "provenance_branch": "ocr",
            "alternate_values": [
                {"value": "A1234567", "source_kind": "mrz_field", "provenance_branch": "mrz"},
            ],
            "warnings": ["ocr_blur"],
        }
    }
    validation = validate_passport_review_fields(
        {
            "passport.number": "B7654321",
            "crew.surname": "DOE",
            "crew.given_names": "JANE",
            "crew.nationality": "GRC",
            "crew.date_of_birth": "1990-01-01",
            "passport.issue_date": "2020-01-01",
            "passport.expiry_date": "2030-01-01",
        },
        evidence,
    )
    conflicts = score_passport_field_conflicts(
        {
            "passport.number": "B7654321",
            "crew.surname": "DOE",
            "crew.given_names": "JANE",
            "crew.nationality": "GRC",
            "crew.date_of_birth": "1990-01-01",
            "passport.issue_date": "2020-01-01",
            "passport.expiry_date": "2030-01-01",
        },
        evidence,
        validation,
    )
    confidence = build_passport_field_confidence(conflicts, validation)

    assert conflicts["passport.number"]["conflict_level"] in {"MEDIUM", "HIGH"}
    assert confidence["passport.number"]["recommended_action"] in {"REVIEW", "HIGH_ATTENTION"}


def test_candidate_bundle_and_compare_ledger_capture_selected_candidate_and_override():
    fields = {
        "passport.number": "B7654321",
        "crew.surname": "DOE",
        "crew.given_names": "JANE",
        "crew.nationality": "GRC",
        "crew.date_of_birth": "1990-01-01",
        "passport.issue_date": "2020-01-01",
        "passport.expiry_date": "2030-01-01",
    }
    evidence = {
        "passport.number": {
            "parsed_value": "B7654321",
            "candidate_text": "B7654321",
            "source_engine": "tesseract",
            "source_kind": "text_line",
            "source_method": "regex",
            "provenance_branch": "ocr",
            "alternate_values": [
                {"value": "A1234567", "source_kind": "mrz_field", "source_method": "mrz", "provenance_branch": "mrz"},
            ],
        }
    }
    validation = validate_passport_review_fields(fields, evidence)
    conflicts = score_passport_field_conflicts(fields, evidence, validation)
    confidence = build_passport_field_confidence(conflicts, validation)
    bundles = build_passport_candidate_bundles(fields, evidence, validation, conflicts, confidence)
    ledger = build_compare_ledger_entries(
        document_id="DOC_123",
        candidate_bundles=bundles,
        field_confidence=confidence,
        review_status="RESOLVED",
        decision_notes="Operator checked OCR against scan",
        operator_overrides={"passport.number": "MANUAL999"},
    )

    assert len(bundles["passport.number"]["candidates"]) == 2
    assert bundles["passport.number"]["selected_candidate_id"] is not None
    assert ledger[0]["document_id"] == "DOC_123"
    assert any(entry["operator_override"] for entry in ledger if entry["field_name"] == "passport.number")


def test_field_level_unresolved_action_keeps_document_pending_and_records_field_state(tmp_path):
    portalis_root = tmp_path / "PORTALIS"
    portalis_root.mkdir(parents=True, exist_ok=True)

    source_file = portalis_root / "documents" / "CREW_PASSPORT" / "passport.pdf"
    source_file.parent.mkdir(parents=True, exist_ok=True)
    source_file.write_bytes(b"fake pdf bytes")

    registry = DocumentRegistry(portalis_root)
    document_id = registry.register_document(
        doc_type="passport",
        owner_entity="crew",
        owner_id="crew_test_001",
        source_file=source_file,
        parsed_fields={"passport.number": "A1234567", "crew.given_names": "OLD"},
        confidence=0.88,
        review_required=True,
        field_evidence={
            "passport.number": {
                "field_name": "passport.number",
                "parsed_value": "A1234567",
                "candidate_text": "A1234567",
                "source_engine": "tesseract",
                "source_kind": "text_line",
                "source_method": "regex",
                "alternate_values": [],
            }
        },
        field_validation={},
        field_conflicts={},
        field_confidence={},
        candidate_bundles={},
        compare_ledger=[],
        accepted_candidate_refs={},
        operator_overrides={},
        field_statuses={},
        unresolved_fields={},
        tce_lite={},
    )

    save_review_queue(
        portalis_root,
        [
            ReviewQueueItem(
                document_id=document_id,
                review_required=True,
                parsed_fields={"passport.number": "A1234567", "crew.given_names": "OLD"},
                status="PENDING",
            )
        ],
    )

    service = ReviewResolutionService(portalis_root)
    result = service.resolve(
        ReviewResolutionCoupler(
            review_item=service.get_review_item(document_id),
            operator_action="RESOLVE",
            field_actions={"passport.number": "MARK_UNRESOLVED", "crew.given_names": "APPLY_OPERATOR_OVERRIDE"},
            edited_fields={"crew.given_names": "EDWARD"},
            unresolved_reasons={"passport.number": "Number still ambiguous"},
            operator_name="watchkeeper",
            resolution_reason="Field-by-field review",
        )
    )

    assert result.resolution_packet.review_status == "PENDING"
    assert result.resolution_packet.field_statuses["passport.number"]["status"] == "UNRESOLVED"
    assert result.resolution_packet.field_statuses["crew.given_names"]["status"] == "OVERRIDDEN"
    assert result.resolution_packet.unresolved_fields["passport.number"]["unresolved_reason"] == "Number still ambiguous"

    updated_doc = registry.get_document(document_id)
    assert updated_doc["field_statuses"]["passport.number"]["status"] == "UNRESOLVED"
    assert updated_doc["unresolved_fields"]["passport.number"]["status"] == "UNRESOLVED"
    assert any(
        entry.get("field_name") == "passport.number" and entry.get("field_status") == "UNRESOLVED"
        for entry in updated_doc["compare_ledger"]
    )


def test_field_level_accept_selected_candidate_records_candidate_ref(tmp_path):
    portalis_root = tmp_path / "PORTALIS"
    portalis_root.mkdir(parents=True, exist_ok=True)

    source_file = portalis_root / "documents" / "CREW_PASSPORT" / "passport.pdf"
    source_file.parent.mkdir(parents=True, exist_ok=True)
    source_file.write_bytes(b"fake pdf bytes")

    registry = DocumentRegistry(portalis_root)
    document_id = registry.register_document(
        doc_type="passport",
        owner_entity="crew",
        owner_id="crew_test_001",
        source_file=source_file,
        parsed_fields={"passport.number": "B7654321"},
        confidence=0.88,
        review_required=True,
        field_evidence={
            "passport.number": {
                "field_name": "passport.number",
                "parsed_value": "B7654321",
                "candidate_text": "B7654321",
                "source_engine": "tesseract",
                "source_kind": "text_line",
                "source_method": "regex",
                "provenance_branch": "ocr",
                "alternate_values": [
                    {"value": "A1234567", "source_kind": "mrz_field", "source_method": "mrz", "provenance_branch": "mrz"},
                ],
            }
        },
        field_validation={},
        field_conflicts={},
        field_confidence={},
        candidate_bundles={},
        compare_ledger=[],
        accepted_candidate_refs={},
        operator_overrides={},
        field_statuses={},
        unresolved_fields={},
        tce_lite={},
    )
    save_review_queue(portalis_root, [ReviewQueueItem(document_id=document_id, review_required=True, parsed_fields={"passport.number": "B7654321"}, status="PENDING")])

    service = ReviewResolutionService(portalis_root)
    review_item = service.get_review_item(document_id)
    probe = service.resolve(
        ReviewResolutionCoupler(
            review_item=review_item,
            operator_action="RESOLVE",
            selected_candidate_ids={"passport.number": "passport.number::mrz::mrz_field::1"},
            field_actions={"passport.number": "ACCEPT_SELECTED_CANDIDATE"},
            operator_name="watchkeeper",
            resolution_reason="Accepting MRZ candidate",
        )
    )

    assert probe.resolution_packet.accepted_candidate_refs["passport.number"] == "passport.number::mrz::mrz_field::1"
    assert probe.resolution_packet.field_statuses["passport.number"]["status"] == "ACCEPTED"


def test_field_policy_distinguishes_attention_from_unresolved():
    candidate_bundles = {
        "passport.number": {"recommended_action": "HIGH_ATTENTION"},
        "crew.nationality": {"recommended_action": "REVIEW"},
    }
    field_validation = {
        "passport.number": {"status": "FAIL"},
        "crew.nationality": {"status": "PASS"},
    }
    field_confidence = {
        "passport.number": {"confidence_band": "LOW", "recommended_action": "HIGH_ATTENTION"},
        "crew.nationality": {"confidence_band": "LOW", "recommended_action": "REVIEW"},
    }
    field_conflicts = {
        "passport.number": {"conflict_level": "HIGH"},
        "crew.nationality": {"conflict_level": "LOW"},
    }
    field_statuses = {
        "passport.number": {"status": "UNRESOLVED"},
        "crew.nationality": {"status": "PENDING"},
    }
    unresolved_fields = {
        "passport.number": {"status": "UNRESOLVED", "unresolved_reason": "Still ambiguous"},
    }

    policy = build_field_policy_packets(
        candidate_bundles=candidate_bundles,
        field_validation=field_validation,
        field_confidence=field_confidence,
        field_conflicts=field_conflicts,
        field_statuses=field_statuses,
        unresolved_fields=unresolved_fields,
    )
    queue = build_prioritized_field_queue(
        document_id="DOC_123",
        field_policy=policy,
        field_statuses=field_statuses,
        field_conflicts=field_conflicts,
        field_confidence=field_confidence,
        candidate_bundles=candidate_bundles,
    )

    assert policy["passport.number"]["attention_state"] == "UNRESOLVED"
    assert policy["crew.nationality"]["attention_state"] == "ATTENTION"
    assert queue[0]["field_name"] == "passport.number"
    assert queue[0]["attention_state"] == "UNRESOLVED"
    assert any(item["field_name"] == "crew.nationality" and item["attention_state"] == "ATTENTION" for item in queue)


def test_cross_document_dashboard_aggregates_priority_and_age():
    review_items = [
        ReviewQueueItem(
            document_id="DOC_001",
            review_required=True,
            status="PENDING",
            created_at="2026-03-29T00:00:00Z",
            updated_at="2026-03-31T00:00:00Z",
            tce=TCELiteEnvelope(WHAT={"document_type": "passport"}),
            prioritized_field_queue=[
                {
                    "document_id": "DOC_001",
                    "field_name": "passport.number",
                    "queue_rank": 1,
                    "priority_score": 180,
                    "priority_band": "CRITICAL",
                    "current_status": "UNRESOLVED",
                    "conflict_level": "HIGH",
                    "confidence_band": "LOW",
                    "recommended_action": "HIGH_ATTENTION",
                    "attention_state": "UNRESOLVED",
                }
            ],
            unresolved_fields={
                "passport.number": {
                    "last_updated": "2026-03-31T00:00:00Z",
                    "status": "UNRESOLVED",
                }
            },
        ),
        ReviewQueueItem(
            document_id="DOC_002",
            review_required=True,
            status="PENDING",
            created_at="2026-03-30T12:00:00Z",
            updated_at="2026-03-30T16:00:00Z",
            tce=TCELiteEnvelope(WHAT={"document_type": "passport"}),
            prioritized_field_queue=[
                {
                    "document_id": "DOC_002",
                    "field_name": "crew.nationality",
                    "queue_rank": 1,
                    "priority_score": 75,
                    "priority_band": "MEDIUM",
                    "current_status": "PENDING",
                    "conflict_level": "LOW",
                    "confidence_band": "LOW",
                    "recommended_action": "REVIEW",
                    "attention_state": "ATTENTION",
                }
            ],
        ),
    ]

    from datetime import datetime, timezone
    now = datetime(2026, 3, 31, 12, 0, tzinfo=timezone.utc)
    queue = build_cross_document_review_queue(review_items, now=now)
    watch_queue = build_watch_queue(review_items, now=now)
    escalation = build_document_escalation_policies(review_items, now=now)
    routing = build_document_routing_hints(review_items, escalation_by_document=escalation, now=now)
    sla = build_document_sla_policies(review_items, escalation_by_document=escalation, routing_by_document=routing, now=now)
    reminder_stage = build_document_reminder_stage(
        review_items,
        escalation_by_document=escalation,
        routing_by_document=routing,
        sla_by_document=sla,
        now=now,
    )
    reminder_queue = build_reminder_queue(review_items, now=now, reminder_by_document=reminder_stage)
    notification_ledger = build_notification_ledger(review_items, reminder_by_document=reminder_stage, sla_by_document=sla, now=now)
    notification_queue = build_notification_queue(review_items, now=now, notification_by_document=notification_ledger)
    transport_requests = build_transport_requests(review_items, notification_by_document=notification_ledger, now=now)
    transport_queue = build_transport_queue(review_items, now=now, transport_by_document=transport_requests)
    alert_feed = build_alert_queue(review_items, now=now)
    summary = build_dashboard_summary(review_items, queue, watch_queue, reminder_queue, notification_queue, transport_queue, alert_feed, now=now)
    tce_delta = build_dashboard_tce_delta(queue, summary, refreshed_at="2026-03-31T12:00:00Z")

    assert queue[0]["document_id"] == "DOC_001"
    assert queue[0]["attention_state"] == "UNRESOLVED"
    assert queue[0]["staleness_band"] in {"FRESH", "ACTIVE", "STALE", "AGED"}
    assert summary["total_pending_review_documents"] == 2
    assert summary["total_unresolved_fields"] == 1
    assert summary["total_attention_fields"] == 2
    assert tce_delta["HOW"]["queue_summary"]["total_queue_items"] == 2
    assert tce_delta["WHEN"]["dashboard_refreshed_at"] == "2026-03-31T12:00:00Z"


def test_escalation_policy_marks_critical_unresolved_passport_number():
    review_items = [
        ReviewQueueItem(
            document_id="DOC_001",
            review_required=True,
            status="PENDING",
            created_at="2026-03-27T00:00:00Z",
            updated_at="2026-03-31T00:00:00Z",
            tce=TCELiteEnvelope(WHAT={"document_type": "passport"}),
            field_policy={
                "passport.number": {"criticality": "CRITICAL"},
            },
            prioritized_field_queue=[
                {
                    "document_id": "DOC_001",
                    "field_name": "passport.number",
                    "queue_rank": 1,
                    "priority_score": 180,
                    "priority_band": "CRITICAL",
                    "current_status": "UNRESOLVED",
                    "conflict_level": "HIGH",
                    "confidence_band": "LOW",
                    "recommended_action": "HIGH_ATTENTION",
                    "attention_state": "UNRESOLVED",
                }
            ],
            unresolved_fields={
                "passport.number": {
                    "last_updated": "2026-03-31T00:00:00Z",
                    "status": "UNRESOLVED",
                }
            },
        )
    ]
    from datetime import datetime, timezone
    now = datetime(2026, 3, 31, 12, 0, tzinfo=timezone.utc)

    escalation = build_document_escalation_policies(review_items, now=now)
    queue = build_cross_document_review_queue(review_items, now=now, escalation_by_document=escalation)

    assert escalation["DOC_001"]["passport.number"]["escalation_level"] == "CRITICAL"
    assert queue[0]["escalation_level"] == "CRITICAL"


def test_triage_action_is_persisted_and_refreshes_control_room_state(tmp_path):
    portalis_root = tmp_path / "PORTALIS"
    portalis_root.mkdir(parents=True, exist_ok=True)

    source_file = portalis_root / "documents" / "CREW_PASSPORT" / "passport.pdf"
    source_file.parent.mkdir(parents=True, exist_ok=True)
    source_file.write_bytes(b"fake pdf bytes")

    registry = DocumentRegistry(portalis_root)
    document_id = registry.register_document(
        doc_type="passport",
        owner_entity="crew",
        owner_id="crew_test_001",
        source_file=source_file,
        parsed_fields={"passport.number": "B7654321"},
        confidence=0.88,
        review_required=True,
        field_policy={"passport.number": {"criticality": "CRITICAL"}},
        prioritized_field_queue=[
            {
                "document_id": "DOC_001",
                "field_name": "passport.number",
                "queue_rank": 1,
                "priority_score": 180,
                "priority_band": "CRITICAL",
                "current_status": "UNRESOLVED",
                "conflict_level": "HIGH",
                "confidence_band": "LOW",
                "recommended_action": "HIGH_ATTENTION",
                "attention_state": "UNRESOLVED",
            }
        ],
        unresolved_fields={
            "passport.number": {
                "document_id": "DOC_001",
                "field_name": "passport.number",
                "unresolved_reason": "Still ambiguous",
                "conflict_level": "HIGH",
                "confidence_band": "LOW",
                "recommended_action": "HIGH_ATTENTION",
                "candidate_bundle_ref": "passport.number",
                "last_updated": "2026-03-31T00:00:00Z",
                "status": "UNRESOLVED",
            }
        },
        tce_lite={"WHAT": {"document_type": "passport"}},
    )
    save_review_queue(
        portalis_root,
        [
            ReviewQueueItem(
                document_id=document_id,
                review_required=True,
                status="PENDING",
                created_at="2026-03-30T00:00:00Z",
                updated_at="2026-03-31T00:00:00Z",
                tce=TCELiteEnvelope(WHAT={"document_type": "passport"}),
                field_policy={"passport.number": {"criticality": "CRITICAL"}},
                prioritized_field_queue=[
                    {
                        "document_id": document_id,
                        "field_name": "passport.number",
                        "queue_rank": 1,
                        "priority_score": 180,
                        "priority_band": "CRITICAL",
                        "current_status": "UNRESOLVED",
                        "conflict_level": "HIGH",
                        "confidence_band": "LOW",
                        "recommended_action": "HIGH_ATTENTION",
                        "attention_state": "UNRESOLVED",
                    }
                ],
                unresolved_fields={
                    "passport.number": {
                        "document_id": document_id,
                        "field_name": "passport.number",
                        "unresolved_reason": "Still ambiguous",
                        "conflict_level": "HIGH",
                        "confidence_band": "LOW",
                        "recommended_action": "HIGH_ATTENTION",
                        "candidate_bundle_ref": "passport.number",
                        "last_updated": "2026-03-31T00:00:00Z",
                        "status": "UNRESOLVED",
                    }
                },
            )
        ],
    )

    result = apply_triage_action(
        portalis_root,
        document_id=document_id,
        field_name="passport.number",
        triage_action="PIN",
        operator_name="control_room",
        triage_note="Watch this first",
    )
    refreshed = refresh_control_room_state(portalis_root)
    item = load_review_queue(portalis_root)[0]
    updated_doc = registry.get_document(document_id)

    assert result["triage_packet"]["triage_status"] == "PINNED"
    assert item.triage_state["passport.number"]["triage_status"] == "PINNED"
    assert item.escalation_policy["passport.number"]["escalation_level"] in {"HIGH", "CRITICAL"}
    assert refreshed["global_review_queue"][0]["triage_status"] == "PINNED"
    assert updated_doc["triage_state"]["passport.number"]["triage_status"] == "PINNED"
    assert "escalation_summary" in updated_doc["tce_lite"]["HOW"]
    assert "triage_summary" in updated_doc["tce_lite"]["HOW"]


def test_routing_hint_and_assignment_are_persisted(tmp_path):
    portalis_root = tmp_path / "PORTALIS"
    portalis_root.mkdir(parents=True, exist_ok=True)

    source_file = portalis_root / "documents" / "CREW_PASSPORT" / "passport.pdf"
    source_file.parent.mkdir(parents=True, exist_ok=True)
    source_file.write_bytes(b"fake pdf bytes")

    registry = DocumentRegistry(portalis_root)
    document_id = registry.register_document(
        doc_type="passport",
        owner_entity="crew",
        owner_id="crew_test_001",
        source_file=source_file,
        parsed_fields={"passport.number": "B7654321"},
        confidence=0.88,
        review_required=True,
        field_policy={"passport.number": {"criticality": "CRITICAL"}},
        field_conflicts={"passport.number": {"conflict_level": "HIGH"}},
        field_confidence={"passport.number": {"confidence_band": "LOW"}},
        field_evidence={"passport.number": {"warnings": []}},
        prioritized_field_queue=[
            {
                "document_id": "DOC_PENDING",
                "field_name": "passport.number",
                "queue_rank": 1,
                "priority_score": 180,
                "priority_band": "CRITICAL",
                "current_status": "UNRESOLVED",
                "conflict_level": "HIGH",
                "confidence_band": "LOW",
                "recommended_action": "HIGH_ATTENTION",
                "attention_state": "UNRESOLVED",
            }
        ],
        unresolved_fields={
            "passport.number": {
                "document_id": "DOC_PENDING",
                "field_name": "passport.number",
                "unresolved_reason": "Still ambiguous",
                "conflict_level": "HIGH",
                "confidence_band": "LOW",
                "recommended_action": "HIGH_ATTENTION",
                "candidate_bundle_ref": "passport.number",
                "last_updated": "2026-03-31T00:00:00Z",
                "status": "UNRESOLVED",
            }
        },
        tce_lite={"WHAT": {"document_type": "passport"}},
    )
    save_review_queue(
        portalis_root,
        [
            ReviewQueueItem(
                document_id=document_id,
                review_required=True,
                status="PENDING",
                created_at="2026-03-27T00:00:00Z",
                updated_at="2026-03-31T00:00:00Z",
                tce=TCELiteEnvelope(WHAT={"document_type": "passport"}),
                field_policy={"passport.number": {"criticality": "CRITICAL"}},
                field_conflicts={"passport.number": {"conflict_level": "HIGH"}},
                field_confidence={"passport.number": {"confidence_band": "LOW"}},
                field_evidence={"passport.number": {"warnings": []}},
                prioritized_field_queue=[
                    {
                        "document_id": document_id,
                        "field_name": "passport.number",
                        "queue_rank": 1,
                        "priority_score": 180,
                        "priority_band": "CRITICAL",
                        "current_status": "UNRESOLVED",
                        "conflict_level": "HIGH",
                        "confidence_band": "LOW",
                        "recommended_action": "HIGH_ATTENTION",
                        "attention_state": "UNRESOLVED",
                    }
                ],
                unresolved_fields={
                    "passport.number": {
                        "document_id": "DOC_PENDING",
                        "field_name": "passport.number",
                        "unresolved_reason": "Still ambiguous",
                        "conflict_level": "HIGH",
                        "confidence_band": "LOW",
                        "recommended_action": "HIGH_ATTENTION",
                        "candidate_bundle_ref": "passport.number",
                        "last_updated": "2026-03-31T00:00:00Z",
                        "status": "UNRESOLVED",
                    }
                },
            )
        ],
    )

    from datetime import datetime, timezone
    now = datetime(2026, 3, 31, 12, 0, tzinfo=timezone.utc)
    items = load_review_queue(portalis_root)
    escalation = build_document_escalation_policies(items, now=now)
    routing = build_document_routing_hints(items, escalation_by_document=escalation, now=now)
    assert routing[document_id]["passport.number"]["routing_bucket"] in {"ASSIGN_SENIOR_REVIEW", "ASSIGN_DOC_REVIEW", "REVIEW_NOW"}

    assignment = apply_assignment_action(
        portalis_root,
        document_id=document_id,
        field_name="passport.number",
        assignment_action="ACCEPT_ROUTING_HINT",
        operator_name="control_room",
        assignment_note="Route per policy",
    )
    refreshed = refresh_control_room_state(portalis_root)
    item = load_review_queue(portalis_root)[0]
    updated_doc = registry.get_document(document_id)

    assert assignment["assignment_packet"]["assignment_status"] == "ASSIGNED"
    assert item.routing_hints["passport.number"]["routing_bucket"] in {"ASSIGN_SENIOR_REVIEW", "ASSIGN_DOC_REVIEW", "REVIEW_NOW"}
    assert item.assignment_state["passport.number"]["assignment_status"] == "ASSIGNED"
    assert refreshed["global_review_queue"][0]["assignment_status"] == "ASSIGNED"
    assert updated_doc["assignment_state"]["passport.number"]["assignment_status"] == "ASSIGNED"
    assert "routing_summary" in updated_doc["tce_lite"]["HOW"]
    assert "assignment_summary" in updated_doc["tce_lite"]["HOW"]


def test_sla_watch_queue_and_watch_ack_are_derived_and_persisted(tmp_path):
    portalis_root = tmp_path / "PORTALIS"
    portalis_root.mkdir(parents=True, exist_ok=True)

    source_file = portalis_root / "documents" / "CREW_PASSPORT" / "passport.pdf"
    source_file.parent.mkdir(parents=True, exist_ok=True)
    source_file.write_bytes(b"fake pdf bytes")

    registry = DocumentRegistry(portalis_root)
    document_id = registry.register_document(
        doc_type="passport",
        owner_entity="crew",
        owner_id="crew_test_001",
        source_file=source_file,
        parsed_fields={"passport.number": "B7654321"},
        confidence=0.88,
        review_required=True,
        field_policy={"passport.number": {"criticality": "CRITICAL"}},
        field_conflicts={"passport.number": {"conflict_level": "HIGH"}},
        field_confidence={"passport.number": {"confidence_band": "LOW"}},
        field_evidence={"passport.number": {"warnings": []}},
        prioritized_field_queue=[
            {
                "document_id": "DOC_PENDING",
                "field_name": "passport.number",
                "queue_rank": 1,
                "priority_score": 180,
                "priority_band": "CRITICAL",
                "current_status": "UNRESOLVED",
                "conflict_level": "HIGH",
                "confidence_band": "LOW",
                "recommended_action": "HIGH_ATTENTION",
                "attention_state": "UNRESOLVED",
            }
        ],
        unresolved_fields={
            "passport.number": {
                "document_id": "DOC_PENDING",
                "field_name": "passport.number",
                "unresolved_reason": "Still ambiguous",
                "conflict_level": "HIGH",
                "confidence_band": "LOW",
                "recommended_action": "HIGH_ATTENTION",
                "candidate_bundle_ref": "passport.number",
                "last_updated": "2026-03-31T00:00:00Z",
                "status": "UNRESOLVED",
            }
        },
        tce_lite={"WHAT": {"document_type": "passport"}},
    )
    save_review_queue(
        portalis_root,
        [
            ReviewQueueItem(
                document_id=document_id,
                review_required=True,
                status="PENDING",
                created_at="2026-03-27T00:00:00Z",
                updated_at="2026-03-31T00:00:00Z",
                tce=TCELiteEnvelope(WHAT={"document_type": "passport"}),
                field_policy={"passport.number": {"criticality": "CRITICAL"}},
                field_conflicts={"passport.number": {"conflict_level": "HIGH"}},
                field_confidence={"passport.number": {"confidence_band": "LOW"}},
                field_evidence={"passport.number": {"warnings": []}},
                prioritized_field_queue=[
                    {
                        "document_id": document_id,
                        "field_name": "passport.number",
                        "queue_rank": 1,
                        "priority_score": 180,
                        "priority_band": "CRITICAL",
                        "current_status": "UNRESOLVED",
                        "conflict_level": "HIGH",
                        "confidence_band": "LOW",
                        "recommended_action": "HIGH_ATTENTION",
                        "attention_state": "UNRESOLVED",
                    }
                ],
                unresolved_fields={
                    "passport.number": {
                        "document_id": document_id,
                        "field_name": "passport.number",
                        "unresolved_reason": "Still ambiguous",
                        "conflict_level": "HIGH",
                        "confidence_band": "LOW",
                        "recommended_action": "HIGH_ATTENTION",
                        "candidate_bundle_ref": "passport.number",
                        "last_updated": "2026-03-31T00:00:00Z",
                        "status": "UNRESOLVED",
                    }
                },
                assignment_state={
                    "passport.number": {
                        "assigned_bucket": "ASSIGN_SENIOR_REVIEW",
                        "owner_hint": "SENIOR_REVIEW",
                        "assignment_status": "ASSIGNED",
                        "assigned_at": "2026-03-31T00:00:00Z",
                        "last_assignment_refresh": "2026-03-31T00:00:00Z",
                    }
                },
            )
        ],
    )

    from datetime import datetime, timezone
    now = datetime(2026, 3, 31, 12, 0, tzinfo=timezone.utc)
    items = load_review_queue(portalis_root)
    escalation = build_document_escalation_policies(items, now=now)
    routing = build_document_routing_hints(items, escalation_by_document=escalation, now=now)
    sla = build_document_sla_policies(items, escalation_by_document=escalation, routing_by_document=routing, now=now)
    watch_queue = build_watch_queue(items, now=now, escalation_by_document=escalation, routing_by_document=routing, sla_by_document=sla)

    assert sla[document_id]["passport.number"]["sla_state"] in {"WATCH", "WARNING", "BREACH"}
    assert watch_queue[0]["notification_ready"] in {True, False}

    watch_result = apply_watch_action(
        portalis_root,
        document_id=document_id,
        field_name="passport.number",
        watch_action="ACKNOWLEDGE_WATCH",
        operator_name="watchkeeper",
        watch_note="Monitoring this escalation",
    )
    refreshed = refresh_control_room_state(portalis_root)
    item = load_review_queue(portalis_root)[0]
    updated_doc = registry.get_document(document_id)

    assert watch_result["watch_packet"]["watch_status"] == "ACKNOWLEDGED"
    assert item.watch_state["passport.number"]["watch_acknowledged_at"]
    assert refreshed["watch_queue"][0]["sla_state"] in {"WATCH", "WARNING", "BREACH"}
    assert refreshed["watch_queue"][0]["requires_ack"] is False
    assert updated_doc["watch_state"]["passport.number"]["watch_acknowledged_at"]
    assert "watch_summary" in updated_doc["tce_lite"]["HOW"]
    assert "sla_summary" in updated_doc["tce_lite"]["HOW"]


def test_reminder_stage_and_actions_are_derived_and_persisted(tmp_path):
    portalis_root = tmp_path / "PORTALIS"
    portalis_root.mkdir(parents=True, exist_ok=True)

    source_file = portalis_root / "documents" / "CREW_PASSPORT" / "passport.pdf"
    source_file.parent.mkdir(parents=True, exist_ok=True)
    source_file.write_bytes(b"fake pdf bytes")

    registry = DocumentRegistry(portalis_root)
    document_id = registry.register_document(
        doc_type="passport",
        owner_entity="crew",
        owner_id="crew_test_001",
        source_file=source_file,
        parsed_fields={"passport.number": "B7654321"},
        confidence=0.88,
        review_required=True,
        field_policy={"passport.number": {"criticality": "CRITICAL"}},
        field_conflicts={"passport.number": {"conflict_level": "HIGH"}},
        field_confidence={"passport.number": {"confidence_band": "LOW"}},
        field_evidence={"passport.number": {"warnings": []}},
        prioritized_field_queue=[
            {
                "document_id": "DOC_PENDING",
                "field_name": "passport.number",
                "queue_rank": 1,
                "priority_score": 180,
                "priority_band": "CRITICAL",
                "current_status": "UNRESOLVED",
                "conflict_level": "HIGH",
                "confidence_band": "LOW",
                "recommended_action": "HIGH_ATTENTION",
                "attention_state": "UNRESOLVED",
            }
        ],
        unresolved_fields={
            "passport.number": {
                "document_id": "DOC_PENDING",
                "field_name": "passport.number",
                "unresolved_reason": "Still ambiguous",
                "conflict_level": "HIGH",
                "confidence_band": "LOW",
                "recommended_action": "HIGH_ATTENTION",
                "candidate_bundle_ref": "passport.number",
                "last_updated": "2026-03-31T00:00:00Z",
                "status": "UNRESOLVED",
            }
        },
        tce_lite={"WHAT": {"document_type": "passport"}},
    )
    save_review_queue(
        portalis_root,
        [
            ReviewQueueItem(
                document_id=document_id,
                review_required=True,
                status="PENDING",
                created_at="2026-03-27T00:00:00Z",
                updated_at="2026-03-31T00:00:00Z",
                tce=TCELiteEnvelope(WHAT={"document_type": "passport"}),
                field_policy={"passport.number": {"criticality": "CRITICAL"}},
                field_conflicts={"passport.number": {"conflict_level": "HIGH"}},
                field_confidence={"passport.number": {"confidence_band": "LOW"}},
                field_evidence={"passport.number": {"warnings": []}},
                prioritized_field_queue=[
                    {
                        "document_id": document_id,
                        "field_name": "passport.number",
                        "queue_rank": 1,
                        "priority_score": 180,
                        "priority_band": "CRITICAL",
                        "current_status": "UNRESOLVED",
                        "conflict_level": "HIGH",
                        "confidence_band": "LOW",
                        "recommended_action": "HIGH_ATTENTION",
                        "attention_state": "UNRESOLVED",
                    }
                ],
                unresolved_fields={
                    "passport.number": {
                        "document_id": document_id,
                        "field_name": "passport.number",
                        "unresolved_reason": "Still ambiguous",
                        "conflict_level": "HIGH",
                        "confidence_band": "LOW",
                        "recommended_action": "HIGH_ATTENTION",
                        "candidate_bundle_ref": "passport.number",
                        "last_updated": "2026-03-31T00:00:00Z",
                        "status": "UNRESOLVED",
                    }
                },
                assignment_state={
                    "passport.number": {
                        "assigned_bucket": "ASSIGN_SENIOR_REVIEW",
                        "owner_hint": "SENIOR_REVIEW",
                        "assignment_status": "ASSIGNED",
                        "assigned_at": "2026-03-31T00:00:00Z",
                        "last_assignment_refresh": "2026-03-31T00:00:00Z",
                    }
                },
            )
        ],
    )

    refreshed = refresh_control_room_state(portalis_root)
    initial_row = refreshed["reminder_queue"][0]
    assert initial_row["reminder_state"] == "READY"

    snooze_result = apply_reminder_action(
        portalis_root,
        document_id=document_id,
        field_name="passport.number",
        reminder_action="SNOOZE_2H",
        operator_name="watchkeeper",
        reminder_note="Waiting for source callback",
    )
    assert snooze_result["reminder_packet"]["reminder_status"] == "SNOOZED"

    refreshed = refresh_control_room_state(portalis_root)
    item = load_review_queue(portalis_root)[0]
    updated_doc = registry.get_document(document_id)

    assert item.notification_prep["passport.number"]["prep_state"] == "SNOOZED"
    assert refreshed["reminder_queue"][0]["reminder_state"] == "SNOOZED"
    assert refreshed["dashboard_summary"]["total_reminder_snoozed_items"] >= 1
    assert "reminder_summary" in updated_doc["tce_lite"]["HOW"]
    assert "notification_prep_summary" in updated_doc["tce_lite"]["HOW"]

    sent_result = apply_reminder_action(
        portalis_root,
        document_id=document_id,
        field_name="passport.number",
        reminder_action="MARK_PREP_SENT",
        operator_name="watchkeeper",
        reminder_note="Prepared for later notifier",
    )
    assert sent_result["reminder_packet"]["reminder_status"] == "SENT"

    refreshed = refresh_control_room_state(portalis_root)
    updated_doc = registry.get_document(document_id)
    assert refreshed["reminder_queue"][0]["reminder_state"] == "SENT"
    assert updated_doc["notification_prep"]["passport.number"]["prep_state"] == "SENT"
    assert "reminder_sent_at" in updated_doc["tce_lite"]["WHEN"]


def test_notification_ledger_and_delivery_attempts_are_persisted(tmp_path):
    portalis_root = tmp_path / "PORTALIS"
    portalis_root.mkdir(parents=True, exist_ok=True)

    source_file = portalis_root / "documents" / "CREW_PASSPORT" / "passport.pdf"
    source_file.parent.mkdir(parents=True, exist_ok=True)
    source_file.write_bytes(b"fake pdf bytes")

    registry = DocumentRegistry(portalis_root)
    document_id = registry.register_document(
        doc_type="passport",
        owner_entity="crew",
        owner_id="crew_test_001",
        source_file=source_file,
        parsed_fields={"passport.number": "B7654321"},
        confidence=0.88,
        review_required=True,
        field_policy={"passport.number": {"criticality": "CRITICAL"}},
        field_conflicts={"passport.number": {"conflict_level": "HIGH"}},
        field_confidence={"passport.number": {"confidence_band": "LOW"}},
        field_evidence={"passport.number": {"warnings": []}},
        prioritized_field_queue=[
            {
                "document_id": "DOC_PENDING",
                "field_name": "passport.number",
                "queue_rank": 1,
                "priority_score": 180,
                "priority_band": "CRITICAL",
                "current_status": "UNRESOLVED",
                "conflict_level": "HIGH",
                "confidence_band": "LOW",
                "recommended_action": "HIGH_ATTENTION",
                "attention_state": "UNRESOLVED",
            }
        ],
        unresolved_fields={
            "passport.number": {
                "document_id": "DOC_PENDING",
                "field_name": "passport.number",
                "unresolved_reason": "Still ambiguous",
                "conflict_level": "HIGH",
                "confidence_band": "LOW",
                "recommended_action": "HIGH_ATTENTION",
                "candidate_bundle_ref": "passport.number",
                "last_updated": "2026-03-31T00:00:00Z",
                "status": "UNRESOLVED",
            }
        },
        tce_lite={"WHAT": {"document_type": "passport"}},
    )
    save_review_queue(
        portalis_root,
        [
            ReviewQueueItem(
                document_id=document_id,
                review_required=True,
                status="PENDING",
                created_at="2026-03-27T00:00:00Z",
                updated_at="2026-03-31T00:00:00Z",
                tce=TCELiteEnvelope(WHAT={"document_type": "passport"}),
                field_policy={"passport.number": {"criticality": "CRITICAL"}},
                field_conflicts={"passport.number": {"conflict_level": "HIGH"}},
                field_confidence={"passport.number": {"confidence_band": "LOW"}},
                field_evidence={"passport.number": {"warnings": []}},
                prioritized_field_queue=[
                    {
                        "document_id": document_id,
                        "field_name": "passport.number",
                        "queue_rank": 1,
                        "priority_score": 180,
                        "priority_band": "CRITICAL",
                        "current_status": "UNRESOLVED",
                        "conflict_level": "HIGH",
                        "confidence_band": "LOW",
                        "recommended_action": "HIGH_ATTENTION",
                        "attention_state": "UNRESOLVED",
                    }
                ],
                unresolved_fields={
                    "passport.number": {
                        "document_id": document_id,
                        "field_name": "passport.number",
                        "unresolved_reason": "Still ambiguous",
                        "conflict_level": "HIGH",
                        "confidence_band": "LOW",
                        "recommended_action": "HIGH_ATTENTION",
                        "candidate_bundle_ref": "passport.number",
                        "last_updated": "2026-03-31T00:00:00Z",
                        "status": "UNRESOLVED",
                    }
                },
                assignment_state={
                    "passport.number": {
                        "assigned_bucket": "ASSIGN_SENIOR_REVIEW",
                        "owner_hint": "SENIOR_REVIEW",
                        "assignment_status": "ASSIGNED",
                        "assigned_at": "2026-03-31T00:00:00Z",
                        "last_assignment_refresh": "2026-03-31T00:00:00Z",
                    }
                },
            )
        ],
    )

    refreshed = refresh_control_room_state(portalis_root)
    assert refreshed["notification_queue"][0]["prep_state"] == "READY"

    failed_result = apply_notification_action(
        portalis_root,
        document_id=document_id,
        field_name="passport.number",
        notification_action="MARK_FAILED",
        operator_name="control_room",
        notification_note="Transport not yet available",
    )
    assert failed_result["notification_packet"]["notification_status"] == "FAILED"

    refreshed = refresh_control_room_state(portalis_root)
    item = load_review_queue(portalis_root)[0]
    updated_doc = registry.get_document(document_id)
    assert item.notification_ledger["passport.number"]["prep_state"] == "FAILED"
    assert len(item.delivery_attempts["passport.number"]) == 1
    assert refreshed["notification_queue"][0]["prep_state"] == "FAILED"
    assert updated_doc["delivery_attempts"]["passport.number"][0]["attempt_state"] == "FAILED"

    restaged_result = apply_notification_action(
        portalis_root,
        document_id=document_id,
        field_name="passport.number",
        notification_action="RESTAGE_NOTIFICATION",
        operator_name="control_room",
        notification_note="Restaged after manual retry review",
    )
    assert restaged_result["notification_packet"]["notification_status"] == "READY"

    emitted_result = apply_notification_action(
        portalis_root,
        document_id=document_id,
        field_name="passport.number",
        notification_action="MARK_EMITTED",
        operator_name="control_room",
        notification_note="Handed to manual channel",
    )
    assert emitted_result["notification_packet"]["notification_status"] == "EMITTED"

    refreshed = refresh_control_room_state(portalis_root)
    updated_doc = registry.get_document(document_id)
    assert refreshed["notification_queue"][0]["prep_state"] == "EMITTED"
    assert updated_doc["notification_ledger"]["passport.number"]["prep_state"] == "EMITTED"
    assert updated_doc["delivery_attempts"]["passport.number"][-1]["attempt_state"] == "EMITTED"
    assert "notification_ledger_summary" in updated_doc["tce_lite"]["HOW"]
    assert "delivery_attempt_summary" in updated_doc["tce_lite"]["HOW"]


def test_transport_handoff_requests_and_results_are_persisted(tmp_path):
    portalis_root = tmp_path / "PORTALIS"
    portalis_root.mkdir(parents=True, exist_ok=True)

    source_file = portalis_root / "documents" / "CREW_PASSPORT" / "passport.pdf"
    source_file.parent.mkdir(parents=True, exist_ok=True)
    source_file.write_bytes(b"fake pdf bytes")

    registry = DocumentRegistry(portalis_root)
    document_id = registry.register_document(
        doc_type="passport",
        owner_entity="crew",
        owner_id="crew_test_001",
        source_file=source_file,
        parsed_fields={"passport.number": "B7654321"},
        confidence=0.88,
        review_required=True,
        field_policy={"passport.number": {"criticality": "CRITICAL"}},
        field_conflicts={"passport.number": {"conflict_level": "HIGH"}},
        field_confidence={"passport.number": {"confidence_band": "LOW"}},
        field_evidence={"passport.number": {"warnings": []}},
        prioritized_field_queue=[
            {
                "document_id": "DOC_PENDING",
                "field_name": "passport.number",
                "queue_rank": 1,
                "priority_score": 180,
                "priority_band": "CRITICAL",
                "current_status": "UNRESOLVED",
                "conflict_level": "HIGH",
                "confidence_band": "LOW",
                "recommended_action": "HIGH_ATTENTION",
                "attention_state": "UNRESOLVED",
            }
        ],
        unresolved_fields={
            "passport.number": {
                "document_id": "DOC_PENDING",
                "field_name": "passport.number",
                "unresolved_reason": "Still ambiguous",
                "conflict_level": "HIGH",
                "confidence_band": "LOW",
                "recommended_action": "HIGH_ATTENTION",
                "candidate_bundle_ref": "passport.number",
                "last_updated": "2026-03-31T00:00:00Z",
                "status": "UNRESOLVED",
            }
        },
        tce_lite={"WHAT": {"document_type": "passport"}},
    )
    save_review_queue(
        portalis_root,
        [
            ReviewQueueItem(
                document_id=document_id,
                review_required=True,
                status="PENDING",
                created_at="2026-03-27T00:00:00Z",
                updated_at="2026-03-31T00:00:00Z",
                tce=TCELiteEnvelope(WHAT={"document_type": "passport"}),
                field_policy={"passport.number": {"criticality": "CRITICAL"}},
                field_conflicts={"passport.number": {"conflict_level": "HIGH"}},
                field_confidence={"passport.number": {"confidence_band": "LOW"}},
                field_evidence={"passport.number": {"warnings": []}},
                prioritized_field_queue=[
                    {
                        "document_id": document_id,
                        "field_name": "passport.number",
                        "queue_rank": 1,
                        "priority_score": 180,
                        "priority_band": "CRITICAL",
                        "current_status": "UNRESOLVED",
                        "conflict_level": "HIGH",
                        "confidence_band": "LOW",
                        "recommended_action": "HIGH_ATTENTION",
                        "attention_state": "UNRESOLVED",
                    }
                ],
                unresolved_fields={
                    "passport.number": {
                        "document_id": document_id,
                        "field_name": "passport.number",
                        "unresolved_reason": "Still ambiguous",
                        "conflict_level": "HIGH",
                        "confidence_band": "LOW",
                        "recommended_action": "HIGH_ATTENTION",
                        "candidate_bundle_ref": "passport.number",
                        "last_updated": "2026-03-31T00:00:00Z",
                        "status": "UNRESOLVED",
                    }
                },
                assignment_state={
                    "passport.number": {
                        "assigned_bucket": "ASSIGN_SENIOR_REVIEW",
                        "owner_hint": "SENIOR_REVIEW",
                        "assignment_status": "ASSIGNED",
                        "assigned_at": "2026-03-31T00:00:00Z",
                        "last_assignment_refresh": "2026-03-31T00:00:00Z",
                    }
                },
            )
        ],
    )

    refreshed = refresh_control_room_state(portalis_root)
    assert refreshed["transport_queue"][0]["latest_result_state"] == "HANDOFF_READY"
    assert refreshed["transport_queue"][0]["channel_hint"] in {"LOCAL_UI", "CONTROL_ROOM_FEED", "FUTURE_EMAIL", "FUTURE_EXTERNAL"}

    accepted = apply_transport_action(
        portalis_root,
        document_id=document_id,
        field_name="passport.number",
        transport_action="MARK_HANDOFF_ACCEPTED",
        operator_name="control_room",
        transport_note="Adapter accepted for future feed",
        channel_hint="CONTROL_ROOM_FEED",
    )
    assert accepted["transport_packet"]["transport_status"] == "HANDOFF_ACCEPTED"

    failed = apply_transport_action(
        portalis_root,
        document_id=document_id,
        field_name="passport.number",
        transport_action="MARK_HANDOFF_FAILED",
        operator_name="control_room",
        transport_note="Future transport unavailable",
        channel_hint="CONTROL_ROOM_FEED",
    )
    assert failed["transport_packet"]["transport_status"] == "HANDOFF_FAILED"

    refreshed = refresh_control_room_state(portalis_root)
    item = load_review_queue(portalis_root)[0]
    updated_doc = registry.get_document(document_id)

    assert item.transport_requests["passport.number"]["channel_hint"] == "CONTROL_ROOM_FEED"
    assert len(item.transport_results["passport.number"]) == 2
    assert item.transport_results["passport.number"][-1]["result_state"] == "HANDOFF_FAILED"
    assert refreshed["transport_queue"][0]["latest_result_state"] == "HANDOFF_FAILED"
    assert updated_doc["transport_results"]["passport.number"][-1]["result_state"] == "HANDOFF_FAILED"
    assert "transport_summary" in updated_doc["tce_lite"]["HOW"]
    assert "handoff_summary" in updated_doc["tce_lite"]["HOW"]


def test_local_alert_feed_is_derived_and_actions_are_persisted(tmp_path):
    portalis_root = tmp_path / "PORTALIS"
    portalis_root.mkdir(parents=True, exist_ok=True)

    source_file = portalis_root / "documents" / "CREW_PASSPORT" / "passport.pdf"
    source_file.parent.mkdir(parents=True, exist_ok=True)
    source_file.write_bytes(b"fake pdf bytes")

    registry = DocumentRegistry(portalis_root)
    document_id = registry.register_document(
        doc_type="passport",
        owner_entity="crew",
        owner_id="crew_test_001",
        source_file=source_file,
        parsed_fields={"passport.number": "B7654321"},
        confidence=0.88,
        review_required=True,
        field_policy={"passport.number": {"criticality": "CRITICAL"}},
        field_conflicts={"passport.number": {"conflict_level": "HIGH"}},
        field_confidence={"passport.number": {"confidence_band": "LOW"}},
        field_evidence={"passport.number": {"warnings": []}},
        prioritized_field_queue=[
            {
                "document_id": "DOC_PENDING",
                "field_name": "passport.number",
                "queue_rank": 1,
                "priority_score": 180,
                "priority_band": "CRITICAL",
                "current_status": "UNRESOLVED",
                "conflict_level": "HIGH",
                "confidence_band": "LOW",
                "recommended_action": "HIGH_ATTENTION",
                "attention_state": "UNRESOLVED",
            }
        ],
        unresolved_fields={
            "passport.number": {
                "document_id": "DOC_PENDING",
                "field_name": "passport.number",
                "unresolved_reason": "Critical passport number mismatch",
                "conflict_level": "HIGH",
                "confidence_band": "LOW",
                "recommended_action": "HIGH_ATTENTION",
                "candidate_bundle_ref": "passport.number",
                "last_updated": "2026-03-31T00:00:00Z",
                "status": "UNRESOLVED",
            }
        },
        tce_lite={"WHAT": {"document_type": "passport"}},
    )
    save_review_queue(
        portalis_root,
        [
            ReviewQueueItem(
                document_id=document_id,
                review_required=True,
                status="PENDING",
                created_at="2026-03-25T00:00:00Z",
                updated_at="2026-03-31T00:00:00Z",
                tce=TCELiteEnvelope(WHAT={"document_type": "passport"}),
                field_policy={"passport.number": {"criticality": "CRITICAL"}},
                field_conflicts={"passport.number": {"conflict_level": "HIGH"}},
                field_confidence={"passport.number": {"confidence_band": "LOW"}},
                field_evidence={"passport.number": {"warnings": []}},
                prioritized_field_queue=[
                    {
                        "document_id": document_id,
                        "field_name": "passport.number",
                        "queue_rank": 1,
                        "priority_score": 180,
                        "priority_band": "CRITICAL",
                        "current_status": "UNRESOLVED",
                        "conflict_level": "HIGH",
                        "confidence_band": "LOW",
                        "recommended_action": "HIGH_ATTENTION",
                        "attention_state": "UNRESOLVED",
                    }
                ],
                unresolved_fields={
                    "passport.number": {
                        "document_id": document_id,
                        "field_name": "passport.number",
                        "unresolved_reason": "Critical passport number mismatch",
                        "conflict_level": "HIGH",
                        "confidence_band": "LOW",
                        "recommended_action": "HIGH_ATTENTION",
                        "candidate_bundle_ref": "passport.number",
                        "last_updated": "2026-03-31T00:00:00Z",
                        "status": "UNRESOLVED",
                    }
                },
                assignment_state={
                    "passport.number": {
                        "assigned_bucket": "ASSIGN_SENIOR_REVIEW",
                        "owner_hint": "SENIOR_REVIEW",
                        "assignment_status": "ASSIGNED",
                        "assigned_at": "2026-03-31T00:00:00Z",
                        "last_assignment_refresh": "2026-03-31T00:00:00Z",
                    }
                },
            )
        ],
    )

    refreshed = refresh_control_room_state(portalis_root)
    assert refreshed["alert_feed"]
    assert refreshed["alert_feed"][0]["field_name"] == "passport.number"
    assert refreshed["alert_feed"][0]["alert_state"] in {"ACTIVE", "REOPENED"}

    ack_result = apply_alert_action(
        portalis_root,
        document_id=document_id,
        field_name="passport.number",
        alert_action="ACKNOWLEDGE_ALERT",
        operator_name="control_room",
        alert_note="Seen by operator",
    )
    assert ack_result["alert_packet"]["alert_status"] == "ACKNOWLEDGED"

    cleared_result = apply_alert_action(
        portalis_root,
        document_id=document_id,
        field_name="passport.number",
        alert_action="CLEAR_ALERT",
        operator_name="control_room",
        alert_note="Temporarily cleared",
    )
    assert cleared_result["alert_packet"]["alert_status"] == "CLEARED"

    refreshed = refresh_control_room_state(portalis_root)
    item = load_review_queue(portalis_root)[0]
    updated_doc = registry.get_document(document_id)

    assert item.local_alerts["passport.number"]["alert_state"] == "CLEARED"
    assert item.local_alerts["passport.number"]["acknowledged_at"]
    assert item.local_alerts["passport.number"]["cleared_at"]
    assert refreshed["dashboard_summary"]["total_cleared_alerts"] >= 1
    assert updated_doc["local_alerts"]["passport.number"]["alert_state"] == "CLEARED"
    assert "alert_feed_summary" in updated_doc["tce_lite"]["HOW"]
    assert "alert_reason" in updated_doc["tce_lite"]["WHY"]


def test_incident_threads_group_alerts_and_preserve_actions(tmp_path):
    portalis_root = tmp_path / "PORTALIS"
    portalis_root.mkdir(parents=True, exist_ok=True)

    source_file = portalis_root / "documents" / "CREW_PASSPORT" / "passport.pdf"
    source_file.parent.mkdir(parents=True, exist_ok=True)
    source_file.write_bytes(b"fake pdf bytes")

    registry = DocumentRegistry(portalis_root)
    document_id = registry.register_document(
        doc_type="passport",
        owner_entity="crew",
        owner_id="crew_test_001",
        source_file=source_file,
        parsed_fields={"passport.number": "B7654321"},
        confidence=0.88,
        review_required=True,
        field_policy={"passport.number": {"criticality": "CRITICAL"}},
        field_conflicts={"passport.number": {"conflict_level": "HIGH"}},
        field_confidence={"passport.number": {"confidence_band": "LOW"}},
        field_evidence={"passport.number": {"warnings": []}},
        prioritized_field_queue=[
            {
                "document_id": "DOC_PENDING",
                "field_name": "passport.number",
                "queue_rank": 1,
                "priority_score": 180,
                "priority_band": "CRITICAL",
                "current_status": "UNRESOLVED",
                "conflict_level": "HIGH",
                "confidence_band": "LOW",
                "recommended_action": "HIGH_ATTENTION",
                "attention_state": "UNRESOLVED",
            }
        ],
        unresolved_fields={
            "passport.number": {
                "document_id": "DOC_PENDING",
                "field_name": "passport.number",
                "unresolved_reason": "Critical passport mismatch",
                "conflict_level": "HIGH",
                "confidence_band": "LOW",
                "recommended_action": "HIGH_ATTENTION",
                "candidate_bundle_ref": "passport.number",
                "last_updated": "2026-03-31T00:00:00Z",
                "status": "UNRESOLVED",
            }
        },
        tce_lite={"WHAT": {"document_type": "passport"}},
    )
    save_review_queue(
        portalis_root,
        [
            ReviewQueueItem(
                document_id=document_id,
                review_required=True,
                status="PENDING",
                created_at="2026-03-25T00:00:00Z",
                updated_at="2026-03-31T00:00:00Z",
                tce=TCELiteEnvelope(WHAT={"document_type": "passport"}),
                field_policy={"passport.number": {"criticality": "CRITICAL"}},
                field_conflicts={"passport.number": {"conflict_level": "HIGH"}},
                field_confidence={"passport.number": {"confidence_band": "LOW"}},
                field_evidence={"passport.number": {"warnings": []}},
                prioritized_field_queue=[
                    {
                        "document_id": document_id,
                        "field_name": "passport.number",
                        "queue_rank": 1,
                        "priority_score": 180,
                        "priority_band": "CRITICAL",
                        "current_status": "UNRESOLVED",
                        "conflict_level": "HIGH",
                        "confidence_band": "LOW",
                        "recommended_action": "HIGH_ATTENTION",
                        "attention_state": "UNRESOLVED",
                    }
                ],
                unresolved_fields={
                    "passport.number": {
                        "document_id": document_id,
                        "field_name": "passport.number",
                        "unresolved_reason": "Critical passport mismatch",
                        "conflict_level": "HIGH",
                        "confidence_band": "LOW",
                        "recommended_action": "HIGH_ATTENTION",
                        "candidate_bundle_ref": "passport.number",
                        "last_updated": "2026-03-31T00:00:00Z",
                        "status": "UNRESOLVED",
                    }
                },
            )
        ],
    )

    refreshed = refresh_control_room_state(portalis_root)
    assert refreshed["incident_feed"]
    assert refreshed["incident_feed"][0]["field_name"] == "passport.number"
    assert refreshed["incident_feed"][0]["occurrence_count"] >= 1

    ack_result = apply_incident_action(
        portalis_root,
        document_id=document_id,
        field_name="passport.number",
        incident_action="ACK_INCIDENT",
        operator_name="control_room",
        incident_note="Grouped and acknowledged",
    )
    assert ack_result["incident_packet"]["incident_status"] == "ACKNOWLEDGED"

    close_result = apply_incident_action(
        portalis_root,
        document_id=document_id,
        field_name="passport.number",
        incident_action="CLOSE_INCIDENT",
        operator_name="control_room",
        incident_note="Closed for now",
    )
    assert close_result["incident_packet"]["incident_status"] == "CLOSED"

    reopen_alert = apply_alert_action(
        portalis_root,
        document_id=document_id,
        field_name="passport.number",
        alert_action="REOPEN_ALERT",
        operator_name="control_room",
        alert_note="Source condition recurred",
    )
    assert reopen_alert["alert_packet"]["alert_status"] == "REOPENED"

    refreshed = refresh_control_room_state(portalis_root)
    item = load_review_queue(portalis_root)[0]
    updated_doc = registry.get_document(document_id)

    assert item.incident_threads["passport.number"]["occurrence_count"] >= 2
    assert item.incident_threads["passport.number"]["incident_state"] in {"REOPENED", "OPEN", "ACKNOWLEDGED", "PINNED"}
    assert item.incident_actions[-1]["incident_action"] == "CLOSE_INCIDENT"
    assert updated_doc["incident_threads"]["passport.number"]["related_alert_ids"]
    assert "incident_summary" in updated_doc["tce_lite"]["HOW"]
    assert "incident_reason" in updated_doc["tce_lite"]["WHY"]


def test_external_bridge_export_queue_and_file_export_are_persisted(tmp_path):
    portalis_root = tmp_path / "PORTALIS"
    portalis_root.mkdir(parents=True, exist_ok=True)

    source_file = portalis_root / "documents" / "CREW_PASSPORT" / "passport.pdf"
    source_file.parent.mkdir(parents=True, exist_ok=True)
    source_file.write_bytes(b"fake pdf bytes")

    registry = DocumentRegistry(portalis_root)
    document_id = registry.register_document(
        doc_type="passport",
        owner_entity="crew",
        owner_id="crew_test_001",
        source_file=source_file,
        parsed_fields={"passport.number": "B7654321"},
        confidence=0.88,
        review_required=True,
        field_policy={"passport.number": {"criticality": "CRITICAL"}},
        field_conflicts={"passport.number": {"conflict_level": "HIGH"}},
        field_confidence={"passport.number": {"confidence_band": "LOW"}},
        field_evidence={"passport.number": {"warnings": []}},
        prioritized_field_queue=[
            {
                "document_id": "DOC_PENDING",
                "field_name": "passport.number",
                "queue_rank": 1,
                "priority_score": 180,
                "priority_band": "CRITICAL",
                "current_status": "UNRESOLVED",
                "conflict_level": "HIGH",
                "confidence_band": "LOW",
                "recommended_action": "HIGH_ATTENTION",
                "attention_state": "UNRESOLVED",
            }
        ],
        unresolved_fields={
            "passport.number": {
                "document_id": "DOC_PENDING",
                "field_name": "passport.number",
                "unresolved_reason": "Critical passport mismatch",
                "conflict_level": "HIGH",
                "confidence_band": "LOW",
                "recommended_action": "HIGH_ATTENTION",
                "candidate_bundle_ref": "passport.number",
                "last_updated": "2026-03-31T00:00:00Z",
                "status": "UNRESOLVED",
            }
        },
        tce_lite={"WHAT": {"document_type": "passport"}},
    )
    save_review_queue(
        portalis_root,
        [
            ReviewQueueItem(
                document_id=document_id,
                review_required=True,
                status="PENDING",
                created_at="2026-03-25T00:00:00Z",
                updated_at="2026-03-31T00:00:00Z",
                tce=TCELiteEnvelope(WHAT={"document_type": "passport"}),
                field_policy={"passport.number": {"criticality": "CRITICAL"}},
                field_conflicts={"passport.number": {"conflict_level": "HIGH"}},
                field_confidence={"passport.number": {"confidence_band": "LOW"}},
                field_evidence={"passport.number": {"warnings": []}},
                prioritized_field_queue=[
                    {
                        "document_id": document_id,
                        "field_name": "passport.number",
                        "queue_rank": 1,
                        "priority_score": 180,
                        "priority_band": "CRITICAL",
                        "current_status": "UNRESOLVED",
                        "conflict_level": "HIGH",
                        "confidence_band": "LOW",
                        "recommended_action": "HIGH_ATTENTION",
                        "attention_state": "UNRESOLVED",
                    }
                ],
                unresolved_fields={
                    "passport.number": {
                        "document_id": document_id,
                        "field_name": "passport.number",
                        "unresolved_reason": "Critical passport mismatch",
                        "conflict_level": "HIGH",
                        "confidence_band": "LOW",
                        "recommended_action": "HIGH_ATTENTION",
                        "candidate_bundle_ref": "passport.number",
                        "last_updated": "2026-03-31T00:00:00Z",
                        "status": "UNRESOLVED",
                    }
                },
            )
        ],
    )

    refreshed = refresh_control_room_state(portalis_root)
    assert refreshed["export_queue"]
    assert refreshed["export_queue"][0]["field_name"] == "passport.number"
    assert refreshed["export_queue"][0]["latest_result_state"] == "EXPORT_READY"

    staged = apply_external_bridge_action(
        portalis_root,
        document_id=document_id,
        field_name="passport.number",
        bridge_action="STAGE_EXPORT",
        operator_name="control_room",
        bridge_note="Stage for future coupler",
        target_hint="LOCAL_EXPORT_FILE",
    )
    assert staged["external_bridge_packet"]["bridge_status"] == "EXPORT_READY"

    accepted = apply_external_bridge_action(
        portalis_root,
        document_id=document_id,
        field_name="passport.number",
        bridge_action="MARK_EXPORT_ACCEPTED",
        operator_name="control_room",
        bridge_note="Bridge accepted payload",
        target_hint="ADMIN_BRIDGE",
    )
    assert accepted["external_bridge_packet"]["bridge_status"] == "EXPORT_ACCEPTED"

    refreshed = refresh_control_room_state(portalis_root)
    item = load_review_queue(portalis_root)[0]
    updated_doc = registry.get_document(document_id)
    export_row = refreshed["export_queue"][0]

    assert item.external_bridge_exports["passport.number"]["target_hint"] in {"LOCAL_EXPORT_FILE", "ADMIN_BRIDGE"}
    assert item.external_bridge_results["passport.number"]["result_state"] == "EXPORT_ACCEPTED"
    assert export_row["latest_result_state"] == "EXPORT_ACCEPTED"
    assert Path(updated_doc["external_bridge_results"]["passport.number"]["export_file_path"]).exists()
    export_payload = json.loads(Path(updated_doc["external_bridge_results"]["passport.number"]["export_file_path"]).read_text(encoding="utf-8"))
    assert export_payload["export_packet"]["document_id"] == document_id
    assert "export_summary" in updated_doc["tce_lite"]["HOW"]
    assert "bridge_summary" in updated_doc["tce_lite"]["HOW"]
    assert "export_reason" in updated_doc["tce_lite"]["WHY"]
