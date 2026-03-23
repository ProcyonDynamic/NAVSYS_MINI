from pathlib import Path
import shutil

from .document_registry import DocumentRegistry
from .document_type_registry import get_document_type
from ..intelligence.document_pipeline import DocumentPipeline
from ..intelligence.ocr_service import OCRService
from ..intelligence.document_classifier import DocumentClassifier
from ..intelligence.field_extractor import FieldExtractor
from ..intelligence.canonical_mapper import CanonicalMapper
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
        
        doc_id = self.registry.register_document(
            doc_type=(
                pipeline_result.classification.document_type
                if pipeline_result.classification is not None
                else doc_def.code
            ),
            owner_entity=owner_entity,
            owner_id=owner_id,
            source_file=stored_file,
            parsed_fields=parsed_fields,
            confidence=confidence,
            review_required=pipeline_result.review_required,
            review_reasons=pipeline_result.review_reasons,
            warnings=pipeline_result.warnings,
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
            "review_required": bool(pipeline_result.review_required),
            "review_reasons": list(pipeline_result.review_reasons or []),
            "warnings": list(pipeline_result.warnings or []),
            "crew_record_path": crew_record_path,
            "crew_update_error": crew_update_error,
            "pipeline_result": pipeline_result,
        }