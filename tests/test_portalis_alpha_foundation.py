from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from modules.portalis_mini.archive.document_registry import DocumentRegistry
from modules.portalis_mini.file_lifecycle_service import FileLifecycleService
from modules.portalis_mini.import_models import ImportRequest
from modules.portalis_mini.import_service import import_declared_document
from modules.portalis_mini.models import ReviewQueueItem, TCELiteEnvelope
from modules.portalis_mini.review_layer_service import ReviewLayerService
from modules.portalis_mini.workspace_layout_service import WorkspaceLayoutService
from modules.portalis_mini.review_resolution_service import (
    ReviewResolutionCoupler,
    ReviewResolutionService,
)
from modules.portalis_mini.review_dashboard_service import (
    apply_alert_action,
    apply_assignment_action,
    apply_external_bridge_action,
    apply_incident_action,
    apply_intake_action,
    apply_dropzone_action,
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
from modules.portalis_mini.studio_workbench_service import (
    add_document_anchor,
    add_workbench_annotation,
    add_workbench_scratchpad_field,
    build_document_workbench,
    clear_reconstruction_cell,
    delete_document_anchor,
    delete_workbench_annotation,
    delete_workbench_scratchpad_field,
    merge_reconstruction_cells,
    open_document_in_workbench,
    select_document_anchor,
    select_reconstruction_block,
    select_reconstruction_cell,
    split_reconstruction_block,
    update_document_anchor,
    update_document_workbench,
    update_reconstruction_block,
    update_reconstruction_cell,
    update_workbench_annotation,
    update_workbench_scratchpad_field,
)
from modules.portalis_mini.navsys_shell_service import build_navsys_shell_state
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
from modules.portalis_mini.task_workspace_service import TaskWorkspaceService
from modules.portalis_mini.task_template_service import TaskTemplateService
from modules.portalis_mini.workspace_persistence_service import WorkspacePersistenceService
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


def test_intake_contract_validation_and_ack_history_are_persisted(tmp_path):
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

    apply_external_bridge_action(
        portalis_root,
        document_id=document_id,
        field_name="passport.number",
        bridge_action="STAGE_EXPORT",
        operator_name="control_room",
        bridge_note="Stage for intake",
        target_hint="LOCAL_EXPORT_FILE",
    )

    refreshed = refresh_control_room_state(portalis_root)
    assert refreshed["intake_queue"]
    assert refreshed["intake_queue"][0]["latest_ack_state"] == "INTAKE_PENDING"
    assert refreshed["intake_queue"][0]["validation"]["validation_state"] == "VALID"

    accepted = apply_intake_action(
        portalis_root,
        document_id=document_id,
        field_name="passport.number",
        intake_action="MARK_INTAKE_ACCEPTED",
        operator_name="admin_bridge",
        intake_note="Accepted by simulated intake",
    )
    assert accepted["intake_packet"]["intake_status"] == "INTAKE_ACCEPTED"

    invalid = apply_intake_action(
        portalis_root,
        document_id=document_id,
        field_name="passport.number",
        intake_action="MARK_INTAKE_INVALID",
        operator_name="admin_bridge",
        intake_note="Contract mismatch on retest",
    )
    assert invalid["intake_packet"]["intake_status"] == "INTAKE_INVALID"

    refreshed = refresh_control_room_state(portalis_root)
    item = load_review_queue(portalis_root)[0]
    updated_doc = registry.get_document(document_id)

    assert item.intake_contracts["passport.number"]["contract_version"] == "portalis-intake-v1"
    assert item.intake_acks["passport.number"]["ack_state"] == "INTAKE_INVALID"
    assert refreshed["intake_queue"][0]["latest_ack_state"] == "INTAKE_INVALID"
    assert updated_doc["intake_acks"]["passport.number"]["ack_reason"] == "Contract mismatch on retest"
    assert "intake_summary" in updated_doc["tce_lite"]["HOW"]
    assert "intake_validation_summary" in updated_doc["tce_lite"]["HOW"]
    assert "intake_reason" in updated_doc["tce_lite"]["WHY"]


def test_document_workbench_lists_opens_and_persists_notes(tmp_path):
    portalis_root = tmp_path / "PORTALIS"
    portalis_root.mkdir(parents=True, exist_ok=True)

    source_file = portalis_root / "documents" / "CREW_PASSPORT" / "passport.txt"
    source_file.parent.mkdir(parents=True, exist_ok=True)
    source_file.write_text("passport preview text\nmanual workbench line", encoding="utf-8")

    registry = DocumentRegistry(portalis_root)
    document_id = registry.register_document(
        doc_type="passport",
        owner_entity="crew",
        owner_id="crew_test_001",
        source_file=source_file,
        parsed_fields={"passport.number": "A1234567"},
        confidence=0.9,
        review_required=True,
        review_reasons=["manual studio review"],
        unresolved_fields={
            "passport.number": {
                "field_name": "passport.number",
                "status": "UNRESOLVED",
            }
        },
        local_alerts={
            "passport.number": {
                "severity": "HIGH",
                "alert_state": "ACTIVE",
                "alert_reason": "Workbench-linked alert",
                "updated_at": "2026-03-31T10:00:00Z",
            }
        },
        incident_threads={
            "passport.number": {
                "incident_state": "OPEN",
                "severity": "HIGH",
                "incident_reason": "Workbench-linked incident",
                "occurrence_count": 2,
                "last_alert_at": "2026-03-31T10:05:00Z",
            }
        },
        tce_lite={"WHAT": {"document_type": "passport"}},
    )

    workbench = build_document_workbench(portalis_root, search_text="crew_test_001")
    assert workbench["document_count"] == 1
    assert workbench["documents"][0]["document_id"] == document_id
    assert workbench["documents"][0]["preview_kind"] == "text"
    assert workbench["documents"][0]["preview_available"] is True

    opened = open_document_in_workbench(
        portalis_root,
        document_id=document_id,
        operator_name="studio_operator",
    )
    assert opened["document_id"] == document_id
    assert opened["status"] == "IN_WORKBENCH"

    updated = update_document_workbench(
        portalis_root,
        document_id=document_id,
        workbench_notes="Manual inspection started",
        workbench_status="IN_WORKBENCH",
        workbench_tags="passport, manual-check",
        operator_name="studio_operator",
    )
    assert updated["status"] == "IN_WORKBENCH"
    assert updated["notes"] == "Manual inspection started"
    assert updated["manual_tags"] == ["passport", "manual-check"]

    refreshed_doc = registry.get_document(document_id)
    assert refreshed_doc["workbench_notes"] == "Manual inspection started"
    assert refreshed_doc["workbench_status"] == "IN_WORKBENCH"
    assert refreshed_doc["workbench_tags"] == ["passport", "manual-check"]
    assert refreshed_doc["workbench_history"][-1]["action"] == "UPDATE_WORKBENCH"
    assert refreshed_doc["tce_lite"]["HOW"]["workbench_summary"]["status"] == "IN_WORKBENCH"
    assert refreshed_doc["tce_lite"]["WHY"]["workbench_reason"]["manual_first_workspace"] is True
    assert refreshed_doc["tce_lite"]["WHEN"]["document_opened_at"]
    assert refreshed_doc["tce_lite"]["WHEN"]["workbench_updated_at"]

    selected = build_document_workbench(portalis_root, selected_document_id=document_id)
    assert selected["selected_document"]["notes"] == "Manual inspection started"
    assert "manual workbench line" in selected["selected_document"]["preview_text"]
    assert selected["selected_document"]["control_room_context"]["review_required"] is True
    assert selected["selected_document"]["control_room_context"]["review_status"] == "PENDING"
    assert selected["selected_document"]["active_alert_count"] == 1
    assert selected["selected_document"]["open_incident_count"] == 1
    assert selected["selected_document"]["unresolved_field_count"] == 1
    assert selected["selected_document"]["tce_lite"]["WHAT"]["document_type"] == "passport"
    assert selected["menu_categories"] == ["File", "View", "Document", "Edit", "Workbench", "Tools", "Help"]
    assert "Grid" in selected["action_strip"]
    assert "Reconstruct" in selected["action_strip"]
    assert selected["pane_state"]["center_workspace_dominant"] is True
    assert selected["selected_document"]["reconstruction_ready"] is True
    assert selected["selected_document"]["reconstruction_grid"]["grid_rows"] >= 20
    assert "reconstruction_summary" in selected["selected_document"]["tce_lite"]["HOW"]
    assert "workbench_layout_summary" in selected["selected_document"]["tce_lite"]["HOW"]


def test_navsys_shell_state_packets_are_explicit():
    shell = build_navsys_shell_state(
        selected_module="PORTALIS",
        selected_submodule="STUDIO",
        ui_mode="STUDIO",
        selected_item_id="DOC::001",
        selected_object_id="ANCHOR::001",
        selected_object_type="FIELD",
        active_workspace_mode="RECONSTRUCT",
        active_menu="TOOLS",
        active_dropdown="STUDIO",
        active_dialog="WORKBENCH_SETTINGS",
        command_palette_open=True,
        command_palette_query="studio",
        selected_command_id="SHOW_STUDIO_ACTIONS",
        left_pane_collapsed=True,
        right_pane_collapsed=False,
        bottom_pane_collapsed=True,
        active_ribbon_tab="STUDIO",
        open_document_tabs=[
            {"tab_id": "DOC::001", "document_id": "DOC::001", "label": "Passport 001", "source_lane": "STUDIO"},
            {"tab_id": "DOC::002", "document_id": "DOC::002", "label": "Passport 002", "source_lane": "REVIEW"},
        ],
        active_document_tab_id="DOC::001",
        split_view_enabled=True,
        split_view_mode="TWO_PANE_VERTICAL",
        split_orientation="VERTICAL",
        active_pane_id="RIGHT",
        pane_documents={
            "LEFT": {"document_id": "DOC::001"},
            "RIGHT": {"document_id": "DOC::002"},
        },
        compare_session={
            "compare_session_id": "COMPARE::001",
            "compare_type": "VARIANT_COMPARE",
            "left_source_id": "DOC::001",
            "right_source_id": "DOC::002",
        },
        inspector_follow_mode="FOLLOW_ACTIVE_PANE",
        selected_file_id="DOC::001",
        selected_file_status="ACTIVE",
        selected_file_action="RENAME_FILE",
        explorer_active_section="FILE_EXPLORER",
        archive_visible=True,
        recent_file_action_result={"action_id": "FILE_RENAMED::DOC::001", "message": "Renamed file display label."},
        pending_file_lifecycle_action={"action_id": "RENAME_FILE"},
        file_entries=[
            {"file_id": "DOC::001", "display_name": "Passport 001", "file_type": "passport", "status": "ACTIVE", "workspace_membership": ["workspace_a"], "opened_in_tabs": True},
        ],
        archive_entries=[
            {"file_id": "DOC::900", "display_name": "Archived Passport", "file_type": "passport", "status": "ARCHIVED"},
        ],
        linked_file_entries=[
            {"file_id": "DOC::777", "display_name": "Linked Support", "file_type": "pdf", "status": "LINKED"},
        ],
        workspace_summary={"selected_document_id": "DOC::001"},
        status_summary={"pending_review_total": 3},
        selected_task_workspace_id="task_arrival_alpha",
        task_entries=[
            {
                "task_workspace_id": "task_arrival_alpha",
                "name": "Arrival Alpha",
                "progress_percent": 50,
                "pending_items": ["item_2"],
            }
        ],
        active_task_workspace={
            "task_workspace_id": "task_arrival_alpha",
            "task_type": "ARRIVAL",
            "workflow_stage": "VALIDATE",
            "progress_percent": 50,
            "pending_items": ["item_2"],
            "resume_target": {"nav_submodule": "STUDIO"},
            "checklist": [{"item_id": "item_1", "label": "Open docs", "status": "DONE"}],
        },
        selected_template_id="template_arrival_alpha",
        selected_template_category="Arrival Package",
        template_entries=[
            {
                "template_id": "template_arrival_alpha",
                "name": "Arrival Alpha Template",
                "category": "Arrival Package",
                "task_type": "ARRIVAL",
                "slot_definitions": [{"slot_id": "CREW_LIST_SLOT"}],
                "favorite": True,
            }
        ],
        active_template={
            "template_id": "template_arrival_alpha",
            "name": "Arrival Alpha Template",
            "category": "Arrival Package",
            "template_type": "TASK_WORKSPACE",
            "task_type": "ARRIVAL",
            "slot_definitions": [{"slot_id": "CREW_LIST_SLOT"}],
        },
        template_wizard={
            "wizard_id": "wizard_001",
            "current_step": 4,
            "review_ready": True,
        },
        selected_review_item_id="review_item_001",
        review_mode_enabled=True,
        review_filter="OPEN",
        review_session_id="review_session_001",
        review_pending_count=2,
        review_annotation_tool="HIGHLIGHT_REGION",
        review_comment_draft="Check discrepancy against source.",
        review_signoff_state={"signed_off": False, "status": "ACTIVE"},
        selected_workspace_mode_id="REVIEW",
        selected_layout_profile_id="layout_review",
        selected_panel_configuration_id="panel_review",
        layout_editor_enabled=True,
        layout_editor_dirty=True,
        panel_visibility_state={
            "left_sidebar_visible": True,
            "right_inspector_visible": True,
            "bottom_panel_visible": True,
            "review_summary_visible": True,
            "task_header_visible": True,
            "compare_summary_visible": True,
        },
        saved_layout_profiles=[
            {"layout_profile_id": "layout_review", "name": "Review Layout", "workspace_mode_id": "REVIEW"},
        ],
        workspace_modes=[
            {"mode_id": "REVIEW", "name": "Review", "default_layout_profile_id": "layout_review"},
        ],
        panel_configurations=[
            {"panel_configuration_id": "panel_review", "name": "Review Panels"},
        ],
        layout_editor_state={
            "enabled": True,
            "editing_profile_id": "layout_review",
            "draft_panel_configuration": {"review_summary_visible": True},
            "draft_dimensions": {"left_width": "92px", "right_width": "320px", "bottom_height": "180px"},
            "preview_mode": "LIVE",
            "dirty": True,
        },
        workspace_mode_switch_pending=False,
        active_layout_profile={
            "layout_profile_id": "layout_review",
            "name": "Review Layout",
            "workspace_mode_id": "REVIEW",
            "panel_configuration_id": "panel_review",
            "left_width": "104px",
            "right_width": "360px",
            "bottom_height": "220px",
            "left_collapsed": True,
            "right_collapsed": False,
            "bottom_collapsed": True,
            "active_split_mode": "TWO_PANE_VERTICAL",
        },
        active_panel_configuration={
            "panel_configuration_id": "panel_review",
            "name": "Review Panels",
            "left_sidebar_visible": True,
            "right_inspector_visible": True,
            "bottom_panel_visible": True,
        },
        review_items=[
            {
                "review_item_id": "review_item_001",
                "title": "Mismatch in passport number",
                "status": "OPEN",
                "severity": "HIGH",
                "pane_id": "LEFT",
            }
        ],
        annotations=[
            {
                "annotation_id": "annotation_001",
                "document_id": "DOC::001",
                "annotation_type": "HIGHLIGHT_REGION",
                "pane_id": "LEFT",
            }
        ],
        review_comments=[
            {
                "comment_id": "comment_001",
                "review_item_id": "review_item_001",
                "body": "Needs second pass.",
            }
        ],
        review_session={
            "review_session_id": "review_session_001",
            "status": "ACTIVE",
            "pending_count": 2,
            "signed_off": False,
        },
        review_audit_entries=[
            {
                "entry_id": "audit_001",
                "kind": "REVIEW_ITEM_CREATED",
                "message": "Created review item.",
            }
        ],
    )
    assert shell["selected_module"] == "PORTALIS"
    assert shell["selected_submodule"] == "STUDIO"
    assert shell["ui_mode"] == "STUDIO"
    assert shell["selected_object_type"] == "FIELD"
    assert shell["selected_workspace_id"] == ""
    assert shell["selected_file_status"] == "ACTIVE"
    assert shell["selected_file_action"] == "RENAME_FILE"
    assert shell["archive_visible"] is True
    assert shell["selected_task_workspace_id"] == "task_arrival_alpha"
    assert shell["selected_template_id"] == "template_arrival_alpha"
    assert shell["selected_review_item_id"] == "review_item_001"
    assert shell["review_mode_enabled"] is True
    assert shell["review_filter"] == "OPEN"
    assert shell["review_session_id"] == "review_session_001"
    assert shell["review_pending_count"] == 2
    assert shell["review_annotation_tool"] == "HIGHLIGHT_REGION"
    assert shell["review_comment_draft"] == "Check discrepancy against source."
    assert shell["selected_workspace_mode_id"] == "REVIEW"
    assert shell["selected_layout_profile_id"] == "layout_review"
    assert shell["selected_panel_configuration_id"] == "panel_review"
    assert shell["layout_editor_enabled"] is True
    assert shell["layout_editor_dirty"] is True
    assert shell["panel_visibility_state"]["review_summary_visible"] is True
    assert shell["saved_layout_profiles"][0]["layout_profile_id"] == "layout_review"
    assert shell["workspace_modes"][0]["mode_id"] == "REVIEW"
    assert shell["panel_configurations"][0]["panel_configuration_id"] == "panel_review"
    assert shell["layout_editor_state"]["editing_profile_id"] == "layout_review"
    assert shell["workspace_dirty"] is False
    assert shell["workspace_state"]["selected_item_id"] == "DOC::001"
    assert shell["workspace_state"]["selected_object_id"] == "ANCHOR::001"
    assert shell["layout_mode"] == "COUPLER_WIDE"
    assert shell["module_subnav"]["PORTALIS"] == ["CONTROL_ROOM", "STUDIO", "ARCHIVE", "REVIEW", "OUTPUT"]
    assert shell["menu_bar"]
    assert shell["dropdown_state"]["dropdown_id"] == "STUDIO"
    assert shell["dropdown_state"]["active"] is True
    assert shell["dialog_state"]["dialog_id"] == "WORKBENCH_SETTINGS"
    assert shell["dialog_state"]["visible"] is True
    assert shell["command_palette"]["open"] is True
    assert shell["command_palette"]["selected_command_id"] == "SHOW_STUDIO_ACTIONS"
    assert shell["command_palette"]["commands"]
    assert shell["pane_state"]["left_pane_collapsed"] is True
    assert shell["pane_state"]["bottom_pane_collapsed"] is True
    assert shell["quick_actions"]
    assert shell["keyboard_shortcuts"]
    assert shell["layout_profile"]["restore_available"] is True
    assert shell["layout_profile"]["workspace_mode_id"] == "REVIEW"
    assert shell["layout_profile"]["panel_configuration_id"] == "panel_review"
    assert shell["partial_refresh"]["enabled"] is True
    assert shell["docking_state"]["default_dock_mode"] == "FLOAT"
    assert any(action["action_id"] == "STUDIO_REVIEW" for action in shell["quick_actions"])
    assert any(tab["ribbon_id"] == "STUDIO" and tab["active"] for tab in shell["ribbon_tabs"])
    assert shell["document_tab_state"]["active_document_tab_id"] == "DOC::001"
    assert len(shell["document_tab_state"]["tabs"]) == 2
    assert shell["document_tab_state"]["tab_order"] == ["DOC::001", "DOC::002"]
    assert shell["document_tab_state"]["tab_groups"][0]["group_id"] == "PRIMARY"
    assert shell["sidebar_sections"]
    assert shell["sidebar_sections"][0]["section_id"] == "WORKSPACES"
    assert any(section["section_id"] == "TASK_WORKSPACES" for section in shell["sidebar_sections"])
    assert any(section["section_id"] == "TEMPLATES" for section in shell["sidebar_sections"])
    assert any(section["section_id"] == "FILE_EXPLORER" for section in shell["sidebar_sections"])
    assert any(section["section_id"] == "ARCHIVE" for section in shell["sidebar_sections"])
    assert shell["bottom_host_tabs"]
    assert shell["bottom_host_tabs"][0]["tab_id"] == "STATUS"
    assert shell["inspector_modes"][0]["mode_id"] == "SELECTION"
    assert shell["workspace_registry"]
    assert shell["selection_event"]["target_id"] == "ANCHOR::001"
    assert shell["selection_event"]["target_type"] == "FIELD"
    assert shell["selection_event"]["recommended_ribbon_tab"] == "LAYOUT"
    assert shell["selection_event"]["recommended_ribbon_group"] == "Field Map"
    assert shell["context_menu_state"]["visible"] is False
    assert shell["context_menu_state"]["quick_actions"]
    assert shell["context_menu_state"]["object_actions"]
    assert shell["floating_toolbar_state"]["visible"] is True
    assert shell["floating_toolbar_state"]["tools"]
    assert shell["object_layer_state"]["layer_order"][0] == "BASE_DOCUMENT"
    assert shell["favorite_tools"]["pinned_ribbon_actions"]
    assert shell["split_view_state"]["group_ids"] == ["PRIMARY"]
    assert shell["split_view_enabled"] is True
    assert shell["split_view_mode"] == "TWO_PANE_VERTICAL"
    assert shell["active_pane_id"] == "RIGHT"
    assert shell["pane_contexts"][0]["pane_id"] == "LEFT"
    assert shell["pane_contexts"][1]["pane_id"] == "RIGHT"
    assert shell["compare_session_id"] == "COMPARE::001"
    assert shell["compare_type"] == "VARIANT_COMPARE"
    assert shell["active_compare_sources"]["LEFT"] == "DOC::001"
    assert shell["active_compare_sources"]["RIGHT"] == "DOC::002"
    assert shell["inspector_follow_mode"] == "FOLLOW_ACTIVE_PANE"
    assert shell["layout_profile"]["layout_profile_id"] == "layout_review"
    assert shell["active_task_type"] == "ARRIVAL"
    assert shell["task_stage"] == "VALIDATE"
    assert shell["task_progress_percent"] == 50
    assert shell["task_pending_count"] == 1
    assert shell["task_workspaces"][0]["task_workspace_id"] == "task_arrival_alpha"
    assert shell["active_task_workspace"]["task_type"] == "ARRIVAL"
    assert shell["selected_template_category"] == "Arrival Package"
    assert shell["template_wizard_step"] == 4
    assert shell["template_wizard_visible"] is True
    assert shell["template_launch_ready"] is True
    assert shell["recent_file_action_result"]["action_id"] == "FILE_RENAMED::DOC::001"
    assert shell["pending_file_lifecycle_action"]["action_id"] == "RENAME_FILE"
    assert shell["templates"][0]["template_id"] == "template_arrival_alpha"
    assert shell["active_template"]["template_id"] == "template_arrival_alpha"
    assert shell["review_items"][0]["review_item_id"] == "review_item_001"
    assert shell["annotations"][0]["annotation_id"] == "annotation_001"
    assert shell["review_comments"][0]["comment_id"] == "comment_001"
    assert shell["review_session"]["review_session_id"] == "review_session_001"
    assert shell["review_audit_entries"][0]["entry_id"] == "audit_001"
    assert "WORKSPACES" in [menu["menu_id"] for menu in shell["menu_bar"]]


def test_navsys_shell_control_room_quick_actions_include_jump_paths():
    shell = build_navsys_shell_state(
        selected_module="PORTALIS",
        selected_submodule="CONTROL_ROOM",
        selected_item_id="DOC::009",
        selected_object_id="passport.number",
        active_workspace_mode="WORKSPACE",
    )
    action_ids = {action["action_id"] for action in shell["quick_actions"]}
    assert "CONTROL_ROOM_REVIEW" in action_ids
    assert "CONTROL_ROOM_STUDIO" in action_ids


def test_workspace_persistence_service_roundtrip(tmp_path):
    portalis_root = tmp_path / "PORTALIS"
    portalis_root.mkdir(parents=True, exist_ok=True)
    service = WorkspacePersistenceService(portalis_root)
    payload = {
        "workspace_name": "Arrival Desk",
        "ui_mode": "STUDIO",
        "open_tabs": [{"tab_id": "DOC::001", "document_id": "DOC::001", "label": "Passport 001", "source_lane": "STUDIO"}],
        "tab_order": ["DOC::001"],
        "active_document_tab_id": "DOC::001",
        "active_ribbon_tab": "STUDIO",
        "left_pane_state": "VISIBLE",
        "right_pane_state": "DOCUMENT",
        "bottom_pane_state": "SCRATCHPAD",
        "layout_profile": {"left_collapsed": False, "right_collapsed": False, "bottom_collapsed": False},
    }

    saved = service.save_workspace(workspace_id="workspace_arrival", name="Arrival Desk", payload=payload)
    assert saved["workspace_id"] == "workspace_arrival"
    assert service.list_workspaces()[0]["name"] == "Arrival Desk"

    renamed = service.rename_workspace(workspace_id="workspace_arrival", new_name="Arrival Desk Updated")
    assert renamed["name"] == "Arrival Desk Updated"

    snapshot = service.save_snapshot(workspace_id="workspace_arrival", payload=payload, note="Checkpoint")
    assert snapshot["workspace_id"] == "workspace_arrival"
    assert service.list_snapshots("workspace_arrival")[0]["label"] == "Checkpoint"

    duplicate = service.duplicate_workspace(workspace_id="workspace_arrival", new_name="Arrival Desk Copy")
    assert duplicate["name"] == "Arrival Desk Copy"

    last_session = service.load_last_session()
    assert last_session["workspace_id"] == duplicate["workspace_id"]

    autosave = service.autosave_workspace(workspace_id="workspace_arrival", payload=payload)
    assert autosave["source_kind"] == "AUTOSAVE"
    recovery = service.load_recovery_state()
    assert recovery["workspace_id"] == "workspace_arrival"

    restored = service.restore_snapshot(snapshot["snapshot_id"])
    assert restored["label"] == "Checkpoint"

    deleted = service.delete_workspace("workspace_arrival")
    assert deleted["workspace_id"] == "workspace_arrival"


def test_workspace_layout_service_roundtrip(tmp_path):
    portalis_root = tmp_path / "PORTALIS"
    portalis_root.mkdir(parents=True, exist_ok=True)
    service = WorkspaceLayoutService(portalis_root)

    modes = service.list_workspace_modes()
    assert any(mode["mode_id"] == "STUDIO" for mode in modes)

    saved_config = service.save_panel_configuration(
        panel_configuration_id="panel_ops",
        name="Ops Panels",
        payload={
            "left_sidebar_visible": True,
            "right_inspector_visible": False,
            "bottom_panel_visible": True,
            "compare_summary_visible": True,
            "active_sections": ["LEFT_SIDEBAR", "BOTTOM_PANEL"],
        },
    )
    assert saved_config["panel_configuration_id"] == "panel_ops"

    saved_profile = service.save_layout_profile(
        layout_profile_id="layout_ops",
        name="Ops Layout",
        payload={
            "workspace_mode_id": "BRIDGE_OPS",
            "left_width": "120px",
            "right_width": "240px",
            "bottom_height": "160px",
            "left_collapsed": False,
            "right_collapsed": True,
            "bottom_collapsed": False,
            "active_split_mode": "SINGLE",
            "panel_configuration_id": "panel_ops",
        },
    )
    assert saved_profile["layout_profile_id"] == "layout_ops"
    assert service.load_layout_profile("layout_ops")["panel_configuration_id"] == "panel_ops"

    renamed = service.rename_layout_profile(layout_profile_id="layout_ops", new_name="Ops Layout Updated")
    assert renamed["name"] == "Ops Layout Updated"

    duplicated = service.duplicate_layout_profile(layout_profile_id="layout_ops", new_name="Ops Layout Copy")
    assert duplicated["layout_profile_id"] != "layout_ops"

    defaulted_mode = service.set_default_layout_for_mode(mode_id="BRIDGE_OPS", layout_profile_id="layout_ops")
    assert defaulted_mode["default_layout_profile_id"] == "layout_ops"

    editor = service.enter_layout_editor(
        editing_profile_id="layout_ops",
        current_state={
            "draft_panel_configuration": {"left_sidebar_visible": True},
            "draft_dimensions": {"left_width": "120px"},
            "preview_mode": "LIVE",
            "dirty": False,
        },
    )
    assert editor["enabled"] is True
    applied = service.apply_layout_editor_draft(
        draft_state={
            "enabled": True,
            "editing_profile_id": "layout_ops",
            "draft_panel_configuration": {"right_inspector_visible": False},
            "draft_dimensions": {"right_width": "240px"},
            "preview_mode": "PREVIEW",
            "dirty": True,
        }
    )
    assert applied["dirty"] is True
    cancelled = service.cancel_layout_editor()
    assert cancelled["enabled"] is False


def test_task_workspace_service_roundtrip(tmp_path):
    portalis_root = tmp_path / "PORTALIS"
    portalis_root.mkdir(parents=True, exist_ok=True)
    service = TaskWorkspaceService(portalis_root)

    created = service.create_task_workspace(
        workspace_id="workspace_arrival",
        name="Arrival Package Alpha",
        task_type="ARRIVAL",
        resume_target={"nav_submodule": "STUDIO", "document_id": "DOC::001", "ribbon_tab": "TASKS"},
    )
    assert created["task_type"] == "ARRIVAL"
    assert created["workflow_stage"] == "INTAKE"
    assert created["checklist"]
    assert created["pending_items"]

    first_item = created["checklist"][0]
    updated = service.update_checklist_item(
        task_workspace_id=created["task_workspace_id"],
        item_id=first_item["item_id"],
        status="DONE",
        note="Loaded into Studio.",
    )
    assert any(item["status"] == "DONE" for item in updated["checklist"])
    assert updated["progress_percent"] > 0

    staged = service.change_task_stage(task_workspace_id=created["task_workspace_id"], stage="VALIDATE")
    assert staged["workflow_stage"] == "VALIDATE"

    checkpointed = service.save_task_checkpoint(
        task_workspace_id=created["task_workspace_id"],
        note="Checkpoint before review.",
    )
    assert any(entry["kind"] == "TASK_CHECKPOINT_SAVED" for entry in checkpointed["history_log"])

    resumed = service.resume_task_workspace(created["task_workspace_id"])
    assert resumed["resume_target"]["nav_submodule"] == "STUDIO"
    assert any(entry["kind"] == "TASK_WORKSPACE_RESUMED" for entry in resumed["history_log"])

    completed = service.mark_task_complete(created["task_workspace_id"])
    assert completed["completion_status"] == "COMPLETE"
    assert completed["workflow_stage"] == "COMPLETE"
    assert any(entry["kind"] == "TASK_MARKED_COMPLETE" for entry in completed["history_log"])


def test_task_template_service_roundtrip_and_launch(tmp_path):
    portalis_root = tmp_path / "PORTALIS"
    portalis_root.mkdir(parents=True, exist_ok=True)
    task_service = TaskWorkspaceService(portalis_root)
    template_service = TaskTemplateService(portalis_root)

    template = template_service.create_template(
        name="US Arrival Package",
        category="Arrival Package",
        template_type="TASK_WORKSPACE",
        task_type="ARRIVAL",
        description="Reusable arrival package blueprint.",
    )
    assert template["template_id"].startswith("template_")
    assert template["slot_definitions"]

    renamed = template_service.rename_template(template_id=template["template_id"], new_name="US Arrival Package v2")
    assert renamed["name"] == "US Arrival Package v2"

    duplicate = template_service.duplicate_template(template_id=template["template_id"], new_name="US Arrival Package Copy")
    assert duplicate["name"] == "US Arrival Package Copy"

    favorite = template_service.set_template_favorite(template_id=template["template_id"], favorite=True)
    assert favorite["favorite"] is True

    wizard = template_service.start_template_wizard(template_type="TASK_WORKSPACE")
    updated_wizard = template_service.update_template_wizard(
        wizard_id=wizard["wizard_id"],
        updates={
            "current_step": 7,
            "draft_name": "Wizard Arrival Template",
            "draft_category": "Arrival Package",
            "draft_task_type": "ARRIVAL",
            "draft_stage_template": ["INTAKE", "VALIDATE", "REVIEW", "EXPORT", "COMPLETE"],
            "draft_slot_definitions": template_service.default_slots_for_task_type("ARRIVAL"),
            "draft_checklist_template": template_service.default_checklist_template("ARRIVAL"),
        },
    )
    assert updated_wizard["review_ready"] is True

    saved_from_wizard = template_service.save_template_from_wizard(wizard["wizard_id"])
    assert saved_from_wizard["name"] == "Wizard Arrival Template"

    launched = template_service.create_task_from_template(
        template_id=template["template_id"],
        task_name="Sabine Pass Arrival",
        workspace_id="workspace_arrival",
        resume_target={"nav_submodule": "STUDIO", "document_id": "DOC::001", "ribbon_tab": "TASKS"},
        slot_assignments=[
            {"slot_id": "CREW_LIST_SLOT", "assigned_source_id": "DOC::CREW", "assigned_source_type": "XLSX"},
            {"slot_id": "VOYAGE_SLOT", "assigned_source_id": "CTX::VOYAGE", "assigned_source_type": "JSON"},
        ],
        task_service=task_service,
    )
    assert launched["template_id"] == template["template_id"]
    assert launched["slot_assignments"]
    assert any(entry["kind"] == "TASK_CREATED_FROM_TEMPLATE" for entry in launched["history_log"])


def test_file_lifecycle_service_active_archive_and_duplicate_flow(tmp_path):
    portalis_root = tmp_path / "PORTALIS"
    portalis_root.mkdir(parents=True, exist_ok=True)
    registry = DocumentRegistry(portalis_root)
    source_file = portalis_root / "documents" / "CREW_PASSPORT" / "passport.txt"
    source_file.parent.mkdir(parents=True, exist_ok=True)
    source_file.write_text("passport body", encoding="utf-8")
    document_id = registry.register_document(
        doc_type="passport",
        owner_entity="crew",
        owner_id="crew_001",
        source_file=source_file,
        parsed_fields={"passport.number": "A1234567"},
        confidence=0.9,
        review_required=False,
        tce_lite={"WHAT": {"document_type": "passport"}},
    )

    service = FileLifecycleService(portalis_root)
    active = service.list_workspace_files(workspace_id="workspace_alpha")
    assert len(active) == 1
    physical_file_id = active[0]["file_id"]
    assert physical_file_id.startswith("FILE_")
    assert active[0]["instance_count"] == 1
    assert active[0]["instances"][0]["document_id"] == document_id

    renamed = service.rename_file(file_id=document_id, workspace_id="workspace_alpha", new_name="Passport Alpha")
    assert renamed["success"] is True
    assert service.get_file(document_id, workspace_id="workspace_alpha")["display_name"] == "Passport Alpha"

    duplicated = service.duplicate_file(file_id=document_id, workspace_id="workspace_alpha", new_name="Passport Alpha Copy")
    assert duplicated["success"] is True
    duplicate_file_id = duplicated["result_file_id"]
    duplicate_document_id = duplicated["updated_refs"]["document_id"]
    assert duplicate_file_id != physical_file_id
    assert duplicate_document_id != document_id

    removed = service.remove_from_workspace(workspace_id="workspace_alpha", file_id=document_id)
    assert removed["updated_refs"]["close_tab_recommended"] is True

    archived = service.archive_file(file_id=duplicate_file_id, workspace_id="workspace_alpha", archive_reason="Done with copy")
    assert archived["success"] is True
    assert any(item["file_id"] == duplicate_file_id for item in service.list_archived_files(workspace_id="workspace_alpha"))

    restored = service.restore_file(file_id=duplicate_file_id, workspace_id="workspace_alpha")
    assert restored["success"] is True
    assert service.get_file(duplicate_file_id, workspace_id="workspace_alpha")["status"] == "ACTIVE"

    deleted = service.delete_file(file_id=document_id, workspace_id="workspace_alpha")
    assert deleted["success"] is True
    assert service.get_file(document_id, workspace_id="workspace_alpha")["status"] == "DELETED"


def test_file_lifecycle_service_deduplicates_external_intake_and_groups_instances(tmp_path):
    portalis_root = tmp_path / "PORTALIS"
    portalis_root.mkdir(parents=True, exist_ok=True)
    external_root = tmp_path / "external"
    external_root.mkdir(parents=True, exist_ok=True)
    source_file = external_root / "passport.pdf"
    source_file.write_bytes(b"same-passport-bytes")

    service = FileLifecycleService(portalis_root)
    first = service.import_external_file(
        workspace_id="workspace_alpha",
        file_path=str(source_file),
        import_mode="IMPORT",
        requested_name="Passport Intake",
    )
    second = service.import_external_file(
        workspace_id="workspace_alpha",
        file_path=str(source_file),
        import_mode="LINK",
        requested_name="Passport Intake Linked",
    )

    assert first["success"] is True
    assert second["success"] is True
    assert first["result_file_id"] == second["result_file_id"]

    active = service.list_workspace_files(workspace_id="workspace_alpha")
    assert len(active) == 1
    assert active[0]["file_id"] == first["result_file_id"]
    assert active[0]["instance_count"] >= 1
    assert active[0]["default_document_id"] == first["updated_refs"]["document_id"]


def test_review_layer_service_roundtrip(tmp_path):
    portalis_root = tmp_path / "PORTALIS"
    portalis_root.mkdir(parents=True, exist_ok=True)
    service = ReviewLayerService(portalis_root)

    session = service.get_or_create_review_session(scope_type="DOCUMENT", scope_id="DOC::001")
    assert session["scope_id"] == "DOC::001"

    review_item = service.create_review_item(
        review_session_id=session["review_session_id"],
        document_id="DOC::001",
        document_tab_id="DOC::001",
        pane_id="LEFT",
        target_object_id="ANCHOR::001",
        kind="ISSUE",
        severity="HIGH",
        title="Passport number mismatch",
        body="Value differs from source image.",
        created_by="watchkeeper",
    )
    assert review_item["status"] == "OPEN"

    comment = service.add_comment(
        review_item_id=review_item["review_item_id"],
        document_id="DOC::001",
        target_object_id="ANCHOR::001",
        body="Escalate to review lead.",
        created_by="watchkeeper",
    )
    assert comment["review_item_id"] == review_item["review_item_id"]

    annotation = service.create_annotation(
        document_id="DOC::001",
        pane_id="LEFT",
        target_object_id="ANCHOR::001",
        annotation_type="HIGHLIGHT_REGION",
        content="Highlighted mismatch region",
        review_session_id=session["review_session_id"],
    )
    assert annotation["annotation_type"] == "HIGHLIGHT_REGION"

    approved = service.approve_review_item(review_item["review_item_id"], actor="chief_officer", note="Accepted after check.")
    assert approved["status"] == "APPROVED"

    signed_off = service.signoff_review_session(review_session_id=session["review_session_id"], actor="chief_officer", note="Review pass complete.")
    assert signed_off["signed_off"] is True

    listed_items = service.list_review_items(review_session_id=session["review_session_id"], document_id="DOC::001")
    assert listed_items[0]["review_item_id"] == review_item["review_item_id"]
    assert service.list_comments(review_item_id=review_item["review_item_id"])[0]["comment_id"] == comment["comment_id"]
    assert service.list_annotations(document_id="DOC::001", review_session_id=session["review_session_id"])[0]["annotation_id"] == annotation["annotation_id"]
    assert any(entry["kind"] == "REVIEW_SESSION_SIGNED_OFF" for entry in service.list_audit_entries(review_session_id=session["review_session_id"]))


def test_document_workbench_anchor_crud_and_contextual_selection(tmp_path):
    portalis_root = tmp_path / "PORTALIS"
    portalis_root.mkdir(parents=True, exist_ok=True)

    source_file = portalis_root / "documents" / "CREW_PASSPORT" / "passport.txt"
    source_file.parent.mkdir(parents=True, exist_ok=True)
    source_file.write_text("anchor preview text", encoding="utf-8")

    registry = DocumentRegistry(portalis_root)
    document_id = registry.register_document(
        doc_type="passport",
        owner_entity="crew",
        owner_id="crew_anchor_001",
        source_file=source_file,
        parsed_fields={"passport.number": "A1234567"},
        confidence=0.92,
        review_required=True,
        tce_lite={"WHAT": {"document_type": "passport"}},
    )

    anchored = add_document_anchor(
        portalis_root,
        document_id=document_id,
        anchor_type="FIELD_BOX",
        x1=12,
        y1=15,
        x2=34,
        y2=24,
        field_name="passport.number",
        label="Passport Number",
        note="Operator-marked field",
        linked_entity_field="crew.passport_number",
        confidence=0.91,
        operator_name="studio_operator",
    )
    assert anchored["anchor_count"] == 1
    anchor_id = anchored["anchors"][0]["anchor_id"]

    selected = select_document_anchor(
        portalis_root,
        document_id=document_id,
        anchor_id=anchor_id,
        operator_name="studio_operator",
    )
    assert selected["anchors"][0]["anchor_id"] == anchor_id

    updated = update_document_anchor(
        portalis_root,
        document_id=document_id,
        anchor_id=anchor_id,
        label="Passport Number Box",
        note="Adjusted manually",
        x1=14,
        y1=16,
        x2=36,
        y2=26,
        operator_name="studio_operator",
    )
    assert updated["anchors"][0]["label"] == "Passport Number Box"
    assert updated["anchors"][0]["x1"] == 14.0
    assert updated["anchors"][0]["x2"] == 36.0

    packet = build_document_workbench(
        portalis_root,
        selected_document_id=document_id,
        selected_anchor_id=anchor_id,
        active_tool_mode="SELECT",
        active_center_mode="ANNOTATE",
        active_bottom_tab="AUDIT",
        inspector_mode="SELECTION",
    )
    assert packet["selected_document"]["anchor_count"] == 1
    assert packet["selected_anchor"]["anchor_id"] == anchor_id
    assert packet["selected_anchor"]["label"] == "Passport Number Box"
    assert packet["selected_anchor"]["status"] == "ACTIVE"
    assert packet["state"]["selected_document_id"] == document_id
    assert packet["state"]["selected_anchor_id"] == anchor_id
    assert packet["state"]["active_center_mode"] == "ANNOTATE"
    assert packet["state"]["active_bottom_tab"] == "AUDIT"
    assert packet["state"]["inspector_mode"] == "SELECTION"
    assert packet["selected_document"]["tce_lite"]["HOW"]["editor_summary"]["anchor_count"] == 1
    assert packet["selected_document"]["tce_lite"]["HOW"]["anchor_summary"]["anchor_id"] == anchor_id
    assert packet["selected_document"]["tce_lite"]["HOW"]["region_edit_summary"]["selected_anchor_id"] == anchor_id
    assert packet["selected_document"]["tce_lite"]["WHY"]["editor_reason"]["manual_anchor_editing"] is True
    assert packet["selected_document"]["tce_lite"]["WHEN"]["anchor_created_at"]
    assert packet["selected_document"]["tce_lite"]["WHEN"]["anchor_updated_at"]

    deleted = delete_document_anchor(
        portalis_root,
        document_id=document_id,
        anchor_id=anchor_id,
        operator_name="studio_operator",
    )
    assert deleted["anchor_count"] == 0

    refreshed_doc = registry.get_document(document_id)
    assert len(refreshed_doc["workbench_anchor_history"]) >= 4


def test_document_workbench_annotations_and_scratchpad_are_additive(tmp_path):
    portalis_root = tmp_path / "PORTALIS"
    portalis_root.mkdir(parents=True, exist_ok=True)

    source_file = portalis_root / "documents" / "CREW_PASSPORT" / "passport.txt"
    source_file.parent.mkdir(parents=True, exist_ok=True)
    source_file.write_text("annotation preview text", encoding="utf-8")

    registry = DocumentRegistry(portalis_root)
    document_id = registry.register_document(
        doc_type="passport",
        owner_entity="crew",
        owner_id="crew_annotation_001",
        source_file=source_file,
        parsed_fields={"passport.number": "A1234567"},
        confidence=0.87,
        review_required=True,
        tce_lite={"WHAT": {"document_type": "passport"}},
    )

    annotated = add_workbench_annotation(
        portalis_root,
        document_id=document_id,
        annotation_type="REVIEW_HINT",
        label="Passport Number Looks Soft",
        note="Digits are readable but visually soft",
        page_number=1,
        region_hint="upper center block",
        operator_name="studio_operator",
    )
    assert annotated["annotation_count"] == 1
    annotation_id = annotated["annotations"][0]["annotation_id"]

    updated_annotation_doc = update_workbench_annotation(
        portalis_root,
        document_id=document_id,
        annotation_id=annotation_id,
        annotation_type="WARNING",
        label="Passport Number Needs Cross-Check",
        note="Compare against crew list",
        status="REVIEWED",
        operator_name="studio_operator",
    )
    assert updated_annotation_doc["annotations"][0]["annotation_type"] == "WARNING"
    assert updated_annotation_doc["annotations"][0]["status"] == "REVIEWED"

    scratch_doc = add_workbench_scratchpad_field(
        portalis_root,
        document_id=document_id,
        field_name="passport.number",
        candidate_value="A1234567",
        linked_entity_field="crew.passport_number",
        confidence_note="visually plausible",
        source_hint="page 1 header",
        operator_note="Needs cross-check with manifest",
        operator_name="studio_operator",
    )
    assert scratch_doc["scratchpad_count"] == 1
    scratchpad_id = scratch_doc["scratchpad_fields"][0]["scratchpad_id"]

    updated_scratch_doc = update_workbench_scratchpad_field(
        portalis_root,
        document_id=document_id,
        scratchpad_id=scratchpad_id,
        field_name="passport.number",
        candidate_value="A1234567",
        linked_entity_field="crew.passport_number",
        confidence_note="operator reviewed",
        source_hint="page 1 header",
        operator_note="Looks consistent",
        status="REVIEWED",
        operator_name="studio_operator",
    )
    assert updated_scratch_doc["scratchpad_fields"][0]["status"] == "REVIEWED"

    packet = build_document_workbench(portalis_root, selected_document_id=document_id)
    selected = packet["selected_document"]
    assert selected["annotation_count"] == 1
    assert selected["scratchpad_count"] == 1
    assert "SCRATCHPAD" in packet["bottom_tab_options"]
    assert "ANNOTATION" in packet["inspector_mode_options"]
    assert selected["tce_lite"]["HOW"]["annotation_summary"]["annotation_count"] == 1
    assert selected["tce_lite"]["HOW"]["scratchpad_summary"]["scratchpad_count"] == 1
    assert selected["tce_lite"]["WHY"]["annotation_reason"]["manual_annotation_capture"] is True
    assert selected["tce_lite"]["WHEN"]["annotation_created_at"]
    assert selected["tce_lite"]["WHEN"]["scratchpad_updated_at"]

    delete_workbench_annotation(
        portalis_root,
        document_id=document_id,
        annotation_id=annotation_id,
        operator_name="studio_operator",
    )
    delete_workbench_scratchpad_field(
        portalis_root,
        document_id=document_id,
        scratchpad_id=scratchpad_id,
        operator_name="studio_operator",
    )
    refreshed_doc = registry.get_document(document_id)
    assert len(refreshed_doc["workbench_annotation_history"]) >= 3
    assert len(refreshed_doc["workbench_scratchpad_history"]) >= 3


def test_document_workbench_reconstruction_foundation_is_derived(tmp_path):
    portalis_root = tmp_path / "PORTALIS"
    portalis_root.mkdir(parents=True, exist_ok=True)

    source_file = portalis_root / "documents" / "CREW_PASSPORT" / "passport.txt"
    source_file.parent.mkdir(parents=True, exist_ok=True)
    source_file.write_text(
        "passport number A1234567\nsurname TESTER\ngiven names PORTALIS USER\nnationality TESTLAND\n",
        encoding="utf-8",
    )

    registry = DocumentRegistry(portalis_root)
    document_id = registry.register_document(
        doc_type="passport",
        owner_entity="crew",
        owner_id="crew_reconstruct_001",
        source_file=source_file,
        parsed_fields={"passport.number": "A1234567"},
        confidence=0.93,
        review_required=True,
        tce_lite={"WHAT": {"document_type": "passport"}},
    )

    add_document_anchor(
        portalis_root,
        document_id=document_id,
        anchor_type="FIELD_BOX",
        x1=10,
        y1=12,
        x2=36,
        y2=20,
        field_name="passport.number",
        label="Passport Number",
        note="Primary document identifier",
        linked_entity_field="crew.passport_number",
        operator_name="studio_operator",
    )
    add_workbench_annotation(
        portalis_root,
        document_id=document_id,
        annotation_type="FIELD_OBSERVATION",
        label="MRZ region",
        note="Lower machine-readable strip",
        page_number=1,
        region_hint="bottom strip",
        operator_name="studio_operator",
    )
    add_workbench_scratchpad_field(
        portalis_root,
        document_id=document_id,
        field_name="passport.number",
        candidate_value="A1234567",
        linked_entity_field="crew.passport_number",
        confidence_note="clear",
        source_hint="header block",
        operator_note="grid reconstruction candidate",
        operator_name="studio_operator",
    )

    packet = build_document_workbench(
        portalis_root,
        selected_document_id=document_id,
        active_center_mode="RECONSTRUCT",
        active_bottom_tab="RECONSTRUCTION",
    )

    selected = packet["selected_document"]
    assert packet["state"]["reconstruction_mode"] == "RECONSTRUCT"
    assert selected["reconstruction_ready"] is True
    assert selected["reconstruction_grid"]["grid_rows"] >= 20
    assert selected["reconstruction_grid"]["grid_cols"] >= 16
    assert len(selected["reconstruction_grid"]["cells"]) >= 1
    assert len(selected["reconstruction_grid"]["regions"]) >= 2
    assert selected["reconstruction_grid"]["editable_surface"] is True
    assert selected["tce_lite"]["HOW"]["reconstruction_summary"]["editable_surface"] is True
    assert selected["tce_lite"]["WHY"]["reconstruction_reason"]["grid_backed_foundation"] is True
    assert selected["tce_lite"]["WHEN"]["reconstruction_started_at"]


def test_document_workbench_reconstruction_cells_and_blocks_are_editable(tmp_path):
    portalis_root = tmp_path / "PORTALIS"
    portalis_root.mkdir(parents=True, exist_ok=True)

    source_file = portalis_root / "documents" / "CREW_PASSPORT" / "passport.txt"
    source_file.parent.mkdir(parents=True, exist_ok=True)
    source_file.write_text(
        "passport number A1234567\nsurname TESTER\ngiven names PORTALIS USER\n",
        encoding="utf-8",
    )

    registry = DocumentRegistry(portalis_root)
    document_id = registry.register_document(
        doc_type="passport",
        owner_entity="crew",
        owner_id="crew_cells_001",
        source_file=source_file,
        parsed_fields={"passport.number": "A1234567"},
        confidence=0.91,
        review_required=True,
        tce_lite={"WHAT": {"document_type": "passport"}},
    )

    anchored = add_document_anchor(
        portalis_root,
        document_id=document_id,
        anchor_type="FIELD_BOX",
        x1=10,
        y1=10,
        x2=34,
        y2=20,
        field_name="passport.number",
        label="Passport Number",
        operator_name="studio_operator",
    )
    anchor_id = anchored["anchors"][0]["anchor_id"]

    packet = build_document_workbench(
        portalis_root,
        selected_document_id=document_id,
        active_center_mode="RECONSTRUCT",
        active_bottom_tab="RECONSTRUCTION",
    )
    cells = packet["selected_document"]["reconstruction_grid"]["cells"]
    assert len(cells) >= 2
    first_cell_id = cells[0]["cell_id"]

    selected_cell = select_reconstruction_cell(
        portalis_root,
        document_id=document_id,
        cell_id=first_cell_id,
    )
    assert selected_cell["cell_id"] == first_cell_id

    updated = update_reconstruction_cell(
        portalis_root,
        document_id=document_id,
        cell_id=first_cell_id,
        text_value="A1234567",
        content_type="FIELD_VALUE",
        linked_field_name="passport.number",
        linked_anchor_id=anchor_id,
        operator_name="studio_operator",
    )
    updated_cells = updated["reconstruction_grid"]["cells"]
    assert updated_cells[0]["text_value"] == "A1234567"
    assert updated_cells[0]["linked_anchor_id"] == anchor_id

    merged = merge_reconstruction_cells(
        portalis_root,
        document_id=document_id,
        lead_cell_id=first_cell_id,
        row_span=1,
        col_span=2,
        label="Passport Header",
        note="Merged header block",
        linked_anchor_id=anchor_id,
        operator_name="studio_operator",
    )
    blocks = merged["reconstruction_grid"]["blocks"]
    assert len(blocks) == 1
    block_id = blocks[0]["block_id"]
    assert blocks[0]["label"] == "Passport Header"
    assert blocks[0]["linked_anchor_id"] == anchor_id

    selected_block = select_reconstruction_block(
        portalis_root,
        document_id=document_id,
        block_id=block_id,
    )
    assert selected_block["block_id"] == block_id

    relabeled = update_reconstruction_block(
        portalis_root,
        document_id=document_id,
        block_id=block_id,
        label="Passport Number Block",
        note="Manual merged block label",
        linked_anchor_id=anchor_id,
        operator_name="studio_operator",
    )
    assert relabeled["reconstruction_grid"]["blocks"][0]["label"] == "Passport Number Block"

    split = split_reconstruction_block(
        portalis_root,
        document_id=document_id,
        block_id=block_id,
        operator_name="studio_operator",
    )
    assert split["reconstruction_grid"]["blocks"] == []

    cleared = clear_reconstruction_cell(
        portalis_root,
        document_id=document_id,
        cell_id=first_cell_id,
        operator_name="studio_operator",
    )
    assert cleared["reconstruction_grid"]["cells"][0]["text_value"] == ""
    assert cleared["reconstruction_grid"]["cells"][0]["content_type"] == "EMPTY"

    refreshed_packet = build_document_workbench(
        portalis_root,
        selected_document_id=document_id,
        selected_cell_id=first_cell_id,
        active_center_mode="RECONSTRUCT",
        active_bottom_tab="RECONSTRUCTION",
        inspector_mode="SELECTION",
    )
    selected = refreshed_packet["selected_document"]
    assert refreshed_packet["selected_cell"]["cell_id"] == first_cell_id
    assert selected["reconstruction_history"]
    assert selected["tce_lite"]["HOW"]["reconstruction_edit_summary"]["selected_cell"] is True
    assert "block_count" in selected["tce_lite"]["HOW"]["reconstruction_summary"]
    assert "member_cells" in selected["tce_lite"]["HOW"]["block_summary"]
    assert selected["tce_lite"]["WHY"]["block_reason"]["manual_block_structuring"] is True
    assert "cell_updated_at" in selected["tce_lite"]["WHEN"]
    assert "block_merged_at" in selected["tce_lite"]["WHEN"]
    assert "block_split_at" in selected["tce_lite"]["WHEN"]

    refreshed_doc = registry.get_document(document_id)
    assert len(refreshed_doc["workbench_reconstruction_history"]) >= 4
    assert len(refreshed_doc["workbench_reconstruction_cells"]) >= 1


def test_document_anchor_links_to_annotation_and_scratchpad(tmp_path):
    portalis_root = tmp_path / "PORTALIS"
    portalis_root.mkdir(parents=True, exist_ok=True)

    source_file = portalis_root / "documents" / "CREW_PASSPORT" / "passport.txt"
    source_file.parent.mkdir(parents=True, exist_ok=True)
    source_file.write_text("anchor link preview", encoding="utf-8")

    registry = DocumentRegistry(portalis_root)
    document_id = registry.register_document(
        doc_type="passport",
        owner_entity="crew",
        owner_id="crew_link_001",
        source_file=source_file,
        parsed_fields={"passport.number": "A1234567"},
        confidence=0.88,
        review_required=True,
        tce_lite={"WHAT": {"document_type": "passport"}},
    )

    annotated = add_workbench_annotation(
        portalis_root,
        document_id=document_id,
        annotation_type="WARNING",
        label="MRZ check",
        note="Lower block needs review",
        page_number=1,
        region_hint="bottom strip",
        operator_name="studio_operator",
    )
    annotation_id = annotated["annotations"][0]["annotation_id"]

    scratch_doc = add_workbench_scratchpad_field(
        portalis_root,
        document_id=document_id,
        field_name="passport.number",
        candidate_value="A1234567",
        linked_entity_field="crew.passport_number",
        confidence_note="clear",
        source_hint="header",
        operator_note="candidate value",
        operator_name="studio_operator",
    )
    scratchpad_id = scratch_doc["scratchpad_fields"][0]["scratchpad_id"]

    anchored = add_document_anchor(
        portalis_root,
        document_id=document_id,
        anchor_type="TEXT_REGION",
        x1=9,
        y1=12,
        x2=40,
        y2=21,
        label="Passport Text Region",
        linked_annotation_id=annotation_id,
        linked_scratchpad_id=scratchpad_id,
        linked_entity_field="crew.passport_number",
        status="FLAGGED",
        operator_name="studio_operator",
    )
    anchor_id = anchored["anchors"][0]["anchor_id"]

    updated = update_document_anchor(
        portalis_root,
        document_id=document_id,
        anchor_id=anchor_id,
        label="Passport Number Region",
        linked_annotation_id=annotation_id,
        linked_scratchpad_id=scratchpad_id,
        linked_entity_field="crew.passport_number",
        status="REVIEWED",
        operator_name="studio_operator",
    )
    assert updated["anchors"][0]["linked_annotation_id"] == annotation_id
    assert updated["anchors"][0]["linked_scratchpad_id"] == scratchpad_id
    assert updated["anchors"][0]["status"] == "REVIEWED"

    packet = build_document_workbench(
        portalis_root,
        selected_document_id=document_id,
        selected_anchor_id=anchor_id,
        active_center_mode="RECONSTRUCT",
        active_bottom_tab="RECONSTRUCTION",
        inspector_mode="SELECTION",
    )
    selected_anchor = packet["selected_anchor"]
    assert selected_anchor["linked_annotation_id"] == annotation_id
    assert selected_anchor["linked_scratchpad_id"] == scratchpad_id
    assert selected_anchor["status"] == "REVIEWED"
    assert packet["selected_document"]["anchor_link_options"]["annotations"][0]["annotation_id"] == annotation_id
    assert packet["selected_document"]["anchor_link_options"]["scratchpad"][0]["scratchpad_id"] == scratchpad_id
    assert packet["selected_document"]["tce_lite"]["HOW"]["anchor_summary"]["linked_annotation_id"] == annotation_id
    assert packet["selected_document"]["tce_lite"]["HOW"]["region_edit_summary"]["linked_scratchpad_id"] == scratchpad_id
    assert packet["selected_document"]["tce_lite"]["WHY"]["anchor_reason"]["manual_region_editing"] is True
    assert packet["selected_document"]["tce_lite"]["WHEN"]["region_linked_at"]

    refreshed_doc = registry.get_document(document_id)
    assert refreshed_doc["workbench_anchor_history"][-1]["anchor_action"] == "UPDATE_ANCHOR"


def test_dropzone_handshake_stages_and_processes_receipt_files(tmp_path):
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

    apply_external_bridge_action(
        portalis_root,
        document_id=document_id,
        field_name="passport.number",
        bridge_action="STAGE_EXPORT",
        operator_name="control_room",
        bridge_note="Stage for dropzone",
        target_hint="COUPLER_DROP",
    )

    staged = apply_dropzone_action(
        portalis_root,
        document_id=document_id,
        field_name="passport.number",
        handshake_action="STAGE_TO_DROPZONE",
        operator_name="control_room",
        handshake_note="Wrote outgoing dropzone packet",
    )
    assert staged["dropzone_packet"]["handshake_status"] == "DROPZONE_STAGED"

    refreshed = refresh_control_room_state(portalis_root)
    assert refreshed["dropzone_queue"]
    handshake_row = refreshed["dropzone_queue"][0]
    outgoing_path = Path(handshake_row["dropzone_path"])
    assert outgoing_path.exists()

    receipt_dir = portalis_root / "exports" / "dropzone" / "receipts"
    receipt_dir.mkdir(parents=True, exist_ok=True)
    receipt_file = receipt_dir / f"{handshake_row['handshake_id'].replace(':', '_')}__receipt.json"
    receipt_file.write_text(
        json.dumps(
            {
                "handshake_id": handshake_row["handshake_id"],
                "export_id": handshake_row["export_id"],
                "receipt_state": "RECEIPT_ACCEPTED",
                "receipt_reason": "External coupler accepted payload",
                "received_at": "2026-03-31T12:30:00Z",
                "receiver_name": "ADMIN_BRIDGE",
                "receiver_status": "ACTIVE",
            }
        ),
        encoding="utf-8",
    )

    checked = apply_dropzone_action(
        portalis_root,
        document_id=document_id,
        field_name="passport.number",
        handshake_action="CHECK_FOR_RECEIPT",
        operator_name="control_room",
        handshake_note="Polling receipt folder",
    )
    assert checked["dropzone_packet"]["handshake_status"] == "RECEIPT_PENDING"

    refreshed = refresh_control_room_state(portalis_root)
    item = load_review_queue(portalis_root)[0]
    updated_doc = registry.get_document(document_id)
    dropzone_row = refreshed["dropzone_queue"][0]

    assert item.dropzone_handshakes["passport.number"]["handshake_state"] == "RECEIPT_ACCEPTED"
    assert item.dropzone_receipts["passport.number"]["receipt_state"] == "RECEIPT_ACCEPTED"
    assert dropzone_row["latest_receipt_state"] == "RECEIPT_ACCEPTED"
    assert Path(item.dropzone_receipts["passport.number"]["archived_path"]).exists()
    assert "handshake_summary" in updated_doc["tce_lite"]["HOW"]


def test_dropzone_reconciliation_flags_duplicate_receipts_and_stale_recovery(tmp_path):
    from datetime import datetime, timezone

    portalis_root = tmp_path / "PORTALIS"
    portalis_root.mkdir(parents=True, exist_ok=True)

    source_file = portalis_root / "documents" / "CREW_PASSPORT" / "passport.pdf"
    source_file.parent.mkdir(parents=True, exist_ok=True)
    source_file.write_bytes(b"fake pdf bytes")

    registry = DocumentRegistry(portalis_root)
    document_id = registry.register_document(
        doc_type="passport",
        owner_entity="crew",
        owner_id="crew_test_002",
        source_file=source_file,
        parsed_fields={"passport.number": "B7654321"},
        confidence=0.84,
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
                "priority_score": 185,
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
                        "priority_score": 185,
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

    apply_external_bridge_action(
        portalis_root,
        document_id=document_id,
        field_name="passport.number",
        bridge_action="STAGE_EXPORT",
        operator_name="control_room",
        bridge_note="Stage for duplicate reconciliation test",
        target_hint="COUPLER_DROP",
    )
    apply_dropzone_action(
        portalis_root,
        document_id=document_id,
        field_name="passport.number",
        handshake_action="STAGE_TO_DROPZONE",
        operator_name="control_room",
        handshake_note="Initial stage",
    )

    handshake_row = refresh_control_room_state(portalis_root)["dropzone_queue"][0]
    receipt_dir = portalis_root / "exports" / "dropzone" / "receipts"
    receipt_dir.mkdir(parents=True, exist_ok=True)
    receipt_id = handshake_row["handshake_id"].replace(":", "_")
    for index, (state, reason) in enumerate(
        [
            ("RECEIPT_ACCEPTED", "External coupler accepted payload"),
            ("RECEIPT_REJECTED", "External coupler rejected duplicate payload"),
        ],
        start=1,
    ):
        (receipt_dir / f"{receipt_id}__receipt_{index}.json").write_text(
            json.dumps(
                {
                    "handshake_id": handshake_row["handshake_id"],
                    "export_id": handshake_row["export_id"],
                    "receipt_state": state,
                    "receipt_reason": reason,
                    "received_at": f"2026-03-31T12:3{index}:00Z",
                    "receiver_name": "ADMIN_BRIDGE",
                    "receiver_status": "ACTIVE" if state == "RECEIPT_ACCEPTED" else "ATTENTION",
                }
            ),
            encoding="utf-8",
        )

    apply_dropzone_action(
        portalis_root,
        document_id=document_id,
        field_name="passport.number",
        handshake_action="CHECK_FOR_RECEIPT",
        operator_name="control_room",
        handshake_note="Poll duplicate receipts",
    )

    refreshed_item = load_review_queue(portalis_root)[0]
    reconciliation = refreshed_item.dropzone_reconciliation["passport.number"]
    recovery = refreshed_item.dropzone_recovery["passport.number"]
    assert len(refreshed_item.dropzone_receipt_history["passport.number"]) >= 3
    assert reconciliation["duplicate_detected"] is True
    assert reconciliation["conflicting_receipts"] is True
    assert recovery["recovery_state"] == "HANDSHAKE_RECOVERY_NEEDED"

    refreshed_item.dropzone_handshakes["passport.number"]["staged_at"] = "2026-03-31T00:00:00Z"
    refreshed_item.dropzone_handshakes["passport.number"]["last_checked_at"] = "2026-03-31T00:00:00Z"
    refreshed_item.dropzone_receipts["passport.number"]["receipt_state"] = "RECEIPT_PENDING"
    refreshed_item.dropzone_receipts["passport.number"]["received_at"] = ""
    refreshed_item.dropzone_recovery["passport.number"] = {}
    save_review_queue(portalis_root, [refreshed_item])

    refreshed = refresh_control_room_state(
        portalis_root,
        now=datetime(2026, 4, 1, 12, 0, tzinfo=timezone.utc),
    )
    stale_row = refreshed["dropzone_queue"][0]
    updated_doc = registry.get_document(document_id)

    assert stale_row["recovery"]["recovery_state"] in {"HANDSHAKE_STALE", "HANDSHAKE_RESTAGE_RECOMMENDED", "HANDSHAKE_RECOVERY_NEEDED"}
    assert stale_row["reconciliation"]["duplicate_detected"] is True
    assert "reconciliation_summary" in updated_doc["tce_lite"]["HOW"]
    assert "recovery_summary" in updated_doc["tce_lite"]["HOW"]
    assert "recovery_reason" in updated_doc["tce_lite"]["WHY"]
    assert updated_doc["tce_lite"]["WHEN"]["reconciled_at"]
    assert "dropzone_summary" in updated_doc["tce_lite"]["HOW"]
    assert "handshake_reason" in updated_doc["tce_lite"]["WHY"]
    assert "receipt_reason" in updated_doc["tce_lite"]["WHY"]


def test_dropzone_reconciliation_detects_stale_and_conflicting_receipts(tmp_path):
    from datetime import datetime, timezone

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
                "last_updated": "2026-03-25T00:00:00Z",
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
                updated_at="2026-03-25T00:00:00Z",
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
                        "last_updated": "2026-03-25T00:00:00Z",
                        "status": "UNRESOLVED",
                    }
                },
            )
        ],
    )

    apply_external_bridge_action(
        portalis_root,
        document_id=document_id,
        field_name="passport.number",
        bridge_action="STAGE_EXPORT",
        operator_name="control_room",
        bridge_note="Stage for stale test",
        target_hint="COUPLER_DROP",
    )
    apply_dropzone_action(
        portalis_root,
        document_id=document_id,
        field_name="passport.number",
        handshake_action="STAGE_TO_DROPZONE",
        operator_name="control_room",
        handshake_note="Initial dropzone staging",
    )

    staged_item = load_review_queue(portalis_root)[0]
    staged_item.dropzone_handshakes["passport.number"]["staged_at"] = "2026-03-25T00:00:00Z"
    staged_item.dropzone_handshakes["passport.number"]["last_checked_at"] = "2026-03-25T00:00:00Z"
    staged_item.dropzone_receipts["passport.number"]["receipt_state"] = "RECEIPT_PENDING"
    save_review_queue(portalis_root, [staged_item])

    stale_now = datetime(2026, 3, 26, 8, 0, 0, tzinfo=timezone.utc)
    refreshed = refresh_control_room_state(portalis_root, now=stale_now)
    dropzone_row = refreshed["dropzone_queue"][0]
    assert dropzone_row["recovery"]["recovery_state"] in {"HANDSHAKE_STALE", "HANDSHAKE_RESTAGE_RECOMMENDED", "HANDSHAKE_RECOVERY_NEEDED"}

    receipt_dir = portalis_root / "exports" / "dropzone" / "receipts"
    receipt_dir.mkdir(parents=True, exist_ok=True)
    handshake_id = dropzone_row["handshake_id"].replace(":", "_")
    export_id = dropzone_row["export_id"]
    (receipt_dir / f"{handshake_id}__receipt_a.json").write_text(
        json.dumps(
            {
                "handshake_id": dropzone_row["handshake_id"],
                "export_id": export_id,
                "receipt_state": "RECEIPT_ACCEPTED",
                "receipt_reason": "First receipt accepted",
                "received_at": "2026-03-26T08:10:00Z",
                "receiver_name": "ADMIN_BRIDGE",
            }
        ),
        encoding="utf-8",
    )
    (receipt_dir / f"{handshake_id}__receipt_b.json").write_text(
        json.dumps(
            {
                "handshake_id": dropzone_row["handshake_id"],
                "export_id": export_id,
                "receipt_state": "RECEIPT_REJECTED",
                "receipt_reason": "Second receipt rejected",
                "received_at": "2026-03-26T08:11:00Z",
                "receiver_name": "ADMIN_BRIDGE",
            }
        ),
        encoding="utf-8",
    )

    apply_dropzone_action(
        portalis_root,
        document_id=document_id,
        field_name="passport.number",
        handshake_action="CHECK_FOR_RECEIPT",
        operator_name="control_room",
        handshake_note="Reconcile repeated receipts",
    )

    refreshed = refresh_control_room_state(portalis_root, now=datetime(2026, 3, 26, 8, 20, 0, tzinfo=timezone.utc))
    item = load_review_queue(portalis_root)[0]
    updated_doc = registry.get_document(document_id)
    row = refreshed["dropzone_queue"][0]

    assert len(item.dropzone_receipt_history["passport.number"]) >= 3
    assert row["reconciliation"]["duplicate_detected"] is True
    assert row["reconciliation"]["conflicting_receipts"] is True
    assert row["recovery"]["recovery_state"] == "HANDSHAKE_RECOVERY_NEEDED"
    assert refreshed["dashboard_summary"]["total_duplicate_receipt_items"] >= 1
    assert refreshed["dashboard_summary"]["total_recovery_needed_items"] >= 1
    assert "reconciliation_summary" in updated_doc["tce_lite"]["HOW"]
    assert "recovery_summary" in updated_doc["tce_lite"]["HOW"]
    assert "recovery_reason" in updated_doc["tce_lite"]["WHY"]
    assert "reconciled_at" in updated_doc["tce_lite"]["WHEN"]
