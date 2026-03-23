import os

from flask import Blueprint, jsonify, request

from modules.portalis_mini.import_models import ImportRequest
from modules.portalis_mini.import_service import import_declared_document


portalis_import_bp = Blueprint("portalis_import_bp", __name__)


@portalis_import_bp.route("/api/portalis/import", methods=["POST"])
def api_portalis_import():
    data = request.get_json(force=True) or {}

    source_path = (data.get("source_path") or "").strip()
    document_type = (data.get("document_type") or "").strip().upper()
    declared_entity_kind = (data.get("declared_entity_kind") or "").strip() or None
    declared_entity_id = (data.get("declared_entity_id") or "").strip() or None
    notes = (data.get("notes") or "").strip()
    tags = data.get("tags") or []

    portalis_root = os.path.join("data", "PORTALIS")

    req = ImportRequest(
        source_path=source_path,
        document_type=document_type,
        declared_entity_kind=declared_entity_kind,
        declared_entity_id=declared_entity_id,
        notes=notes,
        tags=tags,
    )

    result = import_declared_document(req, portalis_root=portalis_root)

    return jsonify({
        "ok": result.ok,
        "import_id": result.import_id,
        "manifest_path": result.manifest_path,
        "stored_file_path": None if not result.stored_file else result.stored_file.stored_path,
        "errors": result.errors,
        "warnings": result.warnings,
    })