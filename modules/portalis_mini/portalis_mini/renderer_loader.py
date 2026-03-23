from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List

from portalis_models import FieldMappingRule, RendererDefinition


class RegistryLoadError(Exception):
    """Raised when a Portalis registry file cannot be loaded or validated."""


class RendererRegistryLoader:
    """Loads Portalis registry files from the NAVSYS_USB data root."""

    def __init__(self, portalis_data_root: str | Path) -> None:
        self.data_root = Path(portalis_data_root)
        self.field_dictionary_path = self.data_root / "canonical_field_dictionary.json"
        self.renderer_registry_path = self.data_root / "renderer_registry.json"
        self.certificate_alias_registry_path = self.data_root / "certificate_alias_registry.json"

    def load_all(self) -> Dict[str, Any]:
        """Load all core registries required by Portalis."""
        field_dictionary = self._load_json_file(self.field_dictionary_path)
        renderer_registry = self._load_json_file(self.renderer_registry_path)
        certificate_alias_registry = self._load_json_file(self.certificate_alias_registry_path)

        self._validate_field_dictionary(field_dictionary)
        renderers = self._parse_renderer_registry(renderer_registry)
        self._validate_certificate_alias_registry(certificate_alias_registry)

        return {
            "field_dictionary": field_dictionary,
            "renderers": renderers,
            "certificate_alias_registry": certificate_alias_registry,
        }

    def load_renderers(self) -> List[RendererDefinition]:
        renderer_registry = self._load_json_file(self.renderer_registry_path)
        return self._parse_renderer_registry(renderer_registry)

    def _load_json_file(self, path: Path) -> Dict[str, Any]:
        if not path.exists():
            raise RegistryLoadError(f"Registry file not found: {path}")

        try:
            with path.open("r", encoding="utf-8") as handle:
                return json.load(handle)
        except json.JSONDecodeError as exc:
            raise RegistryLoadError(f"Invalid JSON in {path}: {exc}") from exc

    def _validate_field_dictionary(self, payload: Dict[str, Any]) -> None:
        if "fields" not in payload:
            raise RegistryLoadError("canonical_field_dictionary.json is missing 'fields'")

        if not isinstance(payload["fields"], dict):
            raise RegistryLoadError("canonical_field_dictionary.json 'fields' must be an object")

    def _parse_renderer_registry(self, payload: Dict[str, Any]) -> List[RendererDefinition]:
        renderer_items = payload.get("renderers")
        if not isinstance(renderer_items, list):
            raise RegistryLoadError("renderer_registry.json 'renderers' must be a list")

        parsed_renderers: List[RendererDefinition] = []

        for item in renderer_items:
            self._validate_renderer_entry(item)

            mapping_rules = [
                FieldMappingRule(
                    canonical_field=rule["canonical_field"],
                    target_field=rule["target_field"],
                    transform=rule.get("transform"),
                    required=rule.get("required", False),
                    default_value=rule.get("default_value"),
                    notes=rule.get("notes"),
                )
                for rule in item.get("mapping_rules", [])
            ]

            parsed_renderers.append(
                RendererDefinition(
                    renderer_id=item["renderer_id"],
                    display_name=item["display_name"],
                    renderer_type=item["renderer_type"],
                    template_path=item["template_path"],
                    output_extension=item["output_extension"],
                    description=item.get("notes"),
                    required_fields=item.get("required_fields", []),
                    mapping_rules=mapping_rules,
                    port_dependent=item.get("port_dependent", False),
                    voyage_dependent=item.get("voyage_dependent", False),
                    crew_dependent=item.get("crew_dependent", False),
                    certificate_trigger_enabled=item.get("certificate_trigger_enabled", False),
                    active=item.get("active", True),
                )
            )

        return parsed_renderers

    def _validate_renderer_entry(self, item: Dict[str, Any]) -> None:
        required_keys = [
            "renderer_id",
            "display_name",
            "renderer_type",
            "template_path",
            "output_extension",
            "required_fields",
        ]

        missing = [key for key in required_keys if key not in item]
        if missing:
            raise RegistryLoadError(
                f"Renderer entry missing required keys: {', '.join(missing)}"
            )

        if not isinstance(item["required_fields"], list):
            raise RegistryLoadError(
                f"Renderer '{item.get('renderer_id', '<unknown>')}' required_fields must be a list"
            )

    def _validate_certificate_alias_registry(self, payload: Dict[str, Any]) -> None:
        certificate_items = payload.get("certificates")
        if not isinstance(certificate_items, list):
            raise RegistryLoadError(
                "certificate_alias_registry.json 'certificates' must be a list"
            )

        for item in certificate_items:
            if "canonical_certificate_id" not in item:
                raise RegistryLoadError(
                    "Certificate alias entry missing 'canonical_certificate_id'"
                )
            if "aliases" not in item or not isinstance(item["aliases"], list):
                raise RegistryLoadError(
                    f"Certificate alias entry '{item.get('canonical_certificate_id', '<unknown>')}' has invalid aliases"
                )
            if "field_targets" not in item or not isinstance(item["field_targets"], dict):
                raise RegistryLoadError(
                    f"Certificate alias entry '{item.get('canonical_certificate_id', '<unknown>')}' has invalid field_targets"
                )


def get_default_portalis_data_root() -> Path:
    """Best-effort default path for NAVSYS_USB Portalis data root on Windows."""
    return Path(r"D:\NAVSYS_USB\data\PORTALIS")


if __name__ == "__main__":
    loader = RendererRegistryLoader(get_default_portalis_data_root())
    registries = loader.load_all()

    print("Loaded field dictionary entries:", len(registries["field_dictionary"]["fields"]))
    print("Loaded renderers:", len(registries["renderers"]))
    print(
        "Loaded certificate alias entries:",
        len(registries["certificate_alias_registry"]["certificates"]),
    )

    print("\nRenderer IDs:")
    for renderer in registries["renderers"]:
        print("-", renderer.renderer_id)
