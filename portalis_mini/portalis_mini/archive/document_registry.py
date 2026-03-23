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
            "created_at": datetime.utcnow().isoformat(),
        }

        registry["documents"].append(entry)

        self._save_registry(registry)

        return doc_id

    def _load_registry(self):

        with open(self.registry_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save_registry(self, registry):

        with open(self.registry_path, "w", encoding="utf-8") as f:
            json.dump(registry, f, indent=2)