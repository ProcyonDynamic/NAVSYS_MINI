from pathlib import Path
import shutil
from dataclasses import asdict
from datetime import datetime, timezone

from .document_registry import DocumentRegistry
from .document_type_registry import get_document_type
from ..intelligence.document_pipeline import DocumentPipeline
from ..intelligence.ocr_service import OCRService
from ..intelligence.document_classifier import DocumentClassifier
from ..intelligence.field_extractor import FieldExtractor
from ..intelligence.canonical_mapper import CanonicalMapper
from ..passport_review_service import (
    build_compare_ledger_entries,
    build_field_statuses,
    build_field_policy_packets,
    build_passport_candidate_bundles,
    build_passport_field_evidence,
    build_passport_field_confidence,
    build_prioritized_field_queue,
    build_passport_review_tce_delta,
    build_unresolved_field_packets,
    score_passport_field_conflicts,
    validate_passport_review_fields,
)
from ..record_update_service import RecordUpdateService

class DocumentImportService:
    def __init__(self, root_dir: Path):
        self.root_dir = Path(root_dir)
        self.registry = DocumentRegistry(self.root_dir)
        self.documents_dir = self.root_dir / "documents"
        self.documents_dir.mkdir(parents=True, exist_ok=True)

        self.pipeline = DocumentPipeline(
            ocr_service=OCRService(),
            classifier=DocumentClassifier(),
            extractor=FieldExtractor(),
            mapper=CanonicalMapper(),
        )
        
        self.record_update_service = RecordUpdateService(self.root_dir)
        
    def import_document(
        self,
        doc_type: str,
        source_file: Path,
        owner_entity: str = "",
        owner_id: str = "",
    ) -> dict:
        source_file = Path(source_file)

        owner_entity = (owner_entity or "").strip().lower()

        if not source_file.exists():
            return {"ok": False, "errors": [f"Source file not found: {source_file}"]}

        doc_def = get_document_type(doc_type)
        if not doc_def:
            return {"ok": False, "errors": [f"Unknown document type: {doc_type}"]}

        if doc_def.requires_owner and (not owner_entity or not owner_id):
            return {"ok": False, "errors": [f"{doc_def.code} requires owner_entity and owner_id."]}

        stored_dir = self.documents_dir / doc_def.code
        stored_dir.mkdir(parents=True, exist_ok=True)

        stored_file = stored_dir / source_file.name
        shutil.copy2(source_file, stored_file)

        try:
            
            pipeline_result = self.pipeline.process_file(stored_file)
        
        except Exception as exc:
            return {
                "ok": False,
                "errors": [f"Pipeline failed: {type(exc).__name__}: {exc}"],
                "stored_file": str(stored_file),
                "owner_entity": owner_entity,
                "owner_id": owner_id,
                "doc_type": doc_def.code,
            }
                    
        parsed_fields = (
            pipeline_result.canonical_fields
            or pipeline_result.resolved_fields
            or {}
        )

        if parsed_fields is None:
            parsed_fields = {}
        confidence = float(
            pipeline_result.confidence
            if pipeline_result.confidence is not None
            else doc_def.default_confidence
        )
        field_evidence = {}
        field_validation = {}
        field_conflicts = {}
        field_confidence = {}
        candidate_bundles = {}
        compare_ledger = []
        accepted_candidate_refs = {}
        operator_overrides = {}
        field_statuses = {}
        unresolved_fields = {}
        field_policy = {}
        prioritized_field_queue = []

        detected_doc_type = (
            pipeline_result.classification.document_type
            if pipeline_result.classification is not None
            else doc_def.code
        )
        if detected_doc_type == "passport":
            field_evidence = build_passport_field_evidence(
                getattr(pipeline_result, "field_evidence", {}) or {},
                parsed_fields,
            )
            field_validation = validate_passport_review_fields(
                parsed_fields,
                field_evidence,
            )
            field_conflicts = score_passport_field_conflicts(
                parsed_fields,
                field_evidence,
                field_validation,
            )
            field_confidence = build_passport_field_confidence(
                field_conflicts,
                field_validation,
            )
            candidate_bundles = build_passport_candidate_bundles(
                parsed_fields,
                field_evidence,
                field_validation,
                field_conflicts,
                field_confidence,
            )
            compare_ledger = build_compare_ledger_entries(
                document_id="PENDING_DOCUMENT_ID",
                candidate_bundles=candidate_bundles,
                field_confidence=field_confidence,
                review_status="PENDING" if pipeline_result.review_required else "ACCEPTED",
            )
            accepted_candidate_refs = {
                field_name: bundle.get("selected_candidate_id")
                for field_name, bundle in candidate_bundles.items()
                if bundle.get("selected_candidate_id")
            }
            field_statuses = build_field_statuses(
                candidate_bundles,
                accepted_candidate_refs=accepted_candidate_refs,
                operator_overrides=operator_overrides,
            )
            unresolved_fields = build_unresolved_field_packets(
                document_id="PENDING_DOCUMENT_ID",
                candidate_bundles=candidate_bundles,
                field_confidence=field_confidence,
                field_conflicts=field_conflicts,
                field_statuses=field_statuses,
            )
            field_policy = build_field_policy_packets(
                candidate_bundles=candidate_bundles,
                field_validation=field_validation,
                field_confidence=field_confidence,
                field_conflicts=field_conflicts,
                field_statuses=field_statuses,
                unresolved_fields=unresolved_fields,
            )
            prioritized_field_queue = build_prioritized_field_queue(
                document_id="PENDING_DOCUMENT_ID",
                field_policy=field_policy,
                field_statuses=field_statuses,
                field_conflicts=field_conflicts,
                field_confidence=field_confidence,
                candidate_bundles=candidate_bundles,
            )

        tce_lite = self._build_tce_lite(
            doc_type=detected_doc_type,
            owner_entity=owner_entity,
            owner_id=owner_id,
            stored_file=stored_file,
            parsed_fields=parsed_fields,
            pipeline_result=pipeline_result,
            doc_def=doc_def,
        )
        if field_validation:
            tce_lite = self._merge_tce_delta(
                tce_lite,
                build_passport_review_tce_delta(
                    field_evidence=field_evidence,
                    field_validation=field_validation,
                    field_conflicts=field_conflicts,
                    field_confidence=field_confidence,
                    candidate_bundles=candidate_bundles,
                    compare_ledger=compare_ledger,
                    selection_mode="machine_selected",
                    field_statuses=field_statuses,
                    unresolved_fields=unresolved_fields,
                    field_policy=field_policy,
                    prioritized_field_queue=prioritized_field_queue,
                ),
            )

        doc_id = self.registry.register_document(
            doc_type=detected_doc_type,
            owner_entity=owner_entity,
            owner_id=owner_id,
            source_file=stored_file,
            parsed_fields=parsed_fields,
            confidence=confidence,
            review_required=pipeline_result.review_required,
            review_reasons=pipeline_result.review_reasons,
            warnings=pipeline_result.warnings,
            field_evidence=field_evidence,
            field_validation=field_validation,
            field_conflicts=field_conflicts,
            field_confidence=field_confidence,
            candidate_bundles=candidate_bundles,
            compare_ledger=compare_ledger,
            accepted_candidate_refs=accepted_candidate_refs,
            operator_overrides=operator_overrides,
            field_statuses=field_statuses,
            unresolved_fields=unresolved_fields,
            field_policy=field_policy,
            prioritized_field_queue=prioritized_field_queue,
            tce_lite=tce_lite,
            operational_reason=f"Portalis declared import for {doc_def.label}",
        )
        if compare_ledger:
            for entry in compare_ledger:
                entry["document_id"] = doc_id
            for item in prioritized_field_queue:
                item["document_id"] = doc_id
            tce_lite = self._merge_tce_delta(
                tce_lite,
                build_passport_review_tce_delta(
                    field_evidence=field_evidence,
                    field_validation=field_validation,
                    field_conflicts=field_conflicts,
                    field_confidence=field_confidence,
                    candidate_bundles=candidate_bundles,
                    compare_ledger=compare_ledger,
                    selection_mode="machine_selected",
                    field_statuses=field_statuses,
                    unresolved_fields=unresolved_fields,
                    field_policy=field_policy,
                    prioritized_field_queue=prioritized_field_queue,
                ),
            )
            self.registry.update_document_qtr_artifacts(
                doc_id,
                candidate_bundles=candidate_bundles,
                compare_ledger=compare_ledger,
                accepted_candidate_refs=accepted_candidate_refs,
                operator_overrides=operator_overrides,
                field_statuses=field_statuses,
                unresolved_fields=unresolved_fields,
                field_policy=field_policy,
                prioritized_field_queue=prioritized_field_queue,
                tce_lite=tce_lite,
            )

        crew_record_path = None
        crew_update_error = None

        if owner_entity == "crew" and owner_id and parsed_fields:
            try:
                crew_record_path = str(
                    self.record_update_service.update_crew_from_mapped_fields(
                        crew_id=owner_id,
                        mapped_fields=parsed_fields,
                        source_file=str(stored_file),
                    )
                )
            except Exception as exc:
                crew_update_error = f"{type(exc).__name__}: {exc}"

        return {
            "ok": True,
            "document_id": doc_id,
            "doc_type": (
                pipeline_result.classification.document_type
                if pipeline_result.classification is not None
                else doc_def.code
            ),
            "stored_file": str(stored_file),
            "owner_entity": owner_entity,
            "owner_id": owner_id,
            "confidence": confidence,
            "parsed_fields": parsed_fields,
            "field_evidence": field_evidence,
            "field_validation": field_validation,
            "field_conflicts": field_conflicts,
            "field_confidence": field_confidence,
            "candidate_bundles": candidate_bundles,
            "compare_ledger": compare_ledger,
            "accepted_candidate_refs": accepted_candidate_refs,
            "operator_overrides": operator_overrides,
            "field_statuses": field_statuses,
            "unresolved_fields": unresolved_fields,
            "field_policy": field_policy,
            "prioritized_field_queue": prioritized_field_queue,
            "review_required": bool(pipeline_result.review_required),
            "review_reasons": list(pipeline_result.review_reasons or []),
            "warnings": list(pipeline_result.warnings or []),
            "crew_record_path": crew_record_path,
            "crew_update_error": crew_update_error,
            "pipeline_result": pipeline_result,
        }

    def _build_tce_lite(
        self,
        *,
        doc_type: str,
        owner_entity: str,
        owner_id: str,
        stored_file: Path,
        parsed_fields: dict,
        pipeline_result,
        doc_def,
    ) -> dict:
        preprocess_steps = []
        ocr_engines = []

        for page in getattr(pipeline_result, "ocr_pages", []):
            preprocess_steps.extend(page.get("preprocess_steps", []))
            if page.get("engine"):
                ocr_engines.append(page.get("engine"))

        issue_date = (
            parsed_fields.get("passport.issue_date")
            or parsed_fields.get("seaman_book.issue_date")
            or parsed_fields.get("certificate.tonnage.issue_date")
        )
        expiry_date = (
            parsed_fields.get("passport.expiry_date")
            or parsed_fields.get("seaman_book.expiry_date")
            or parsed_fields.get("certificate.tonnage.expiry_date")
        )

        return {
            "WHAT": {
                "document_type": doc_type,
                "declared_type": doc_def.code,
                "field_keys": sorted(parsed_fields.keys()),
            },
            "WHO": {
                "owner_entity": owner_entity or "unlinked",
                "owner_id": owner_id or "",
            },
            "WHEN": {
                "imported_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "issue_date": issue_date,
                "expiry_date": expiry_date,
            },
            "WHERE": {
                "source_file": str(stored_file),
                "document_store": str(stored_file.parent),
            },
            "HOW": {
                "ocr_engine": getattr(self.pipeline, "ocr_engine", ""),
                "ocr_engines_observed": sorted(set(ocr_engines)),
                "classification": getattr(getattr(pipeline_result, "classification", None), "document_type", None),
                "preprocess_enabled": True,
                "preprocess_steps": preprocess_steps,
                "warnings": list(getattr(pipeline_result, "warnings", []) or []),
            },
            "WHY": {
                "operational_reason": f"Portalis import for {doc_def.label}",
                "target_use": "document_registry_and_review",
            },
        }

    def _merge_tce_delta(self, base_tce: dict, delta: dict) -> dict:
        merged = {
            "WHAT": dict(base_tce.get("WHAT", {})),
            "WHO": dict(base_tce.get("WHO", {})),
            "WHEN": dict(base_tce.get("WHEN", {})),
            "WHERE": dict(base_tce.get("WHERE", {})),
            "HOW": dict(base_tce.get("HOW", {})),
            "WHY": dict(base_tce.get("WHY", {})),
        }

        for section in ("WHAT", "WHO", "WHEN", "WHERE", "HOW", "WHY"):
            merged[section].update(delta.get(section, {}))

        return merged
