from __future__ import annotations

import json
from pathlib import Path
from typing import List, Dict


def ports_root(portalis_root):
    return Path(portalis_root) / "ports"


def _slugify_port_name(name: str) -> str:
    return (
        (name or "")
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("/", "_")
        .replace("\\", "_")
    )


def port_file_path(portalis_root, port_name: str) -> Path:
    return ports_root(portalis_root) / f"{_slugify_port_name(port_name)}.json"


def list_ports(portalis_root) -> List[str]:
    root = ports_root(portalis_root)
    if not root.exists():
        return []

    ports = []
    for p in root.glob("*.json"):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            ports.append(data.get("port_name", p.stem))
        except Exception:
            ports.append(p.stem)

    ports.sort()
    return ports


def load_port_requirement(portalis_root, port_name: str) -> Dict:
    p = port_file_path(portalis_root, port_name)
    if not p.exists():
        return {
            "port_name": port_name,
            "country": "",
            "required_docs": [],
            "non_standard_forms": [],
            "certificate_requirements": [],
            "notes": "",
        }

    return json.loads(p.read_text(encoding="utf-8"))


def save_port_requirement(
    portalis_root,
    *,
    port_name: str,
    country: str,
    required_docs: List[str],
    non_standard_forms: List[str],
    certificate_requirements: List[str],
    notes: str,
) -> None:
    root = ports_root(portalis_root)
    root.mkdir(parents=True, exist_ok=True)

    data = {
        "port_name": port_name.strip(),
        "country": country.strip(),
        "required_docs": [x.strip() for x in required_docs if x.strip()],
        "non_standard_forms": [x.strip() for x in non_standard_forms if x.strip()],
        "certificate_requirements": [x.strip() for x in certificate_requirements if x.strip()],
        "notes": notes.strip(),
    }

    p = port_file_path(portalis_root, port_name)
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")