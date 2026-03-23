from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any


class DocumentRegistry:

    def __init__(self, root_dir: Path):

        self.root_dir = root_dir
        self.registry_path = root_dir / "registry" / "document_registry.json"

        self.registry_path.parent.mkdir(parents=True, exist_ok=True)

        if not self.registry_path.exists():
            self._save_registry({"documents": []})

    def register_document(
        self,
        doc_type: str,
        owner_entity: str,
        owner_id: str,
        source_file: Path,
        parsed_fields: Dict[str, Any],
        confidence: float,
        review_required: bool = False,
        review_reasons: list[str] | None = None,
        warnings: list[str] | None = None,
    ) -> str:
        
        registry = self._load_registry()

        doc_id = f"DOC_{len(registry['documents'])+1:06d}"

        entry = {
            "document_id": doc_id,
            "doc_type": doc_type,
            "owner_entity": owner_entity,
            "owner_id": owner_id,
            "source_file": str(source_file),
            "parsed_fields": parsed_fields,
            "confidence": confidence,
            "review_required": review_required,
            "review_reasons": review_reasons or [],
            "warnings": warnings or [],
            "created_at": datetime.utcnow().isoformat(),
        }

        registry["documents"].append(entry)

        self._save_registry(registry)

        return doc_id

    def _load_registry(self):

        if not self.registry_path.exists():
            return {"documents": []}

        with open(self.registry_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            return {"documents": []}

        if "documents" not in data or not isinstance(data["documents"], list):
            data["documents"] = []

        return data
    
    def _save_registry(self, registry):

        with open(self.registry_path, "w", encoding="utf-8") as f:
            json.dump(registry, f, indent=2, ensure_ascii=False)
            
    def list_documents(self) -> list[Dict[str, Any]]:
        registry = self._load_registry()
        return registry.get("documents", [])
    
    def get_document(self, document_id: str) -> Dict[str, Any] | None:
        registry = self._load_registry()

        for entry in registry.get("documents", []):
            if entry.get("document_id") == document_id:
                return entry

        return None