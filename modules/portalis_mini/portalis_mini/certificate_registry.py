from __future__ import annotations
import json
from pathlib import Path


def cert_root(portalis_root):
    return Path(portalis_root) / "certificates"


def _slugify(name: str) -> str:
    return name.lower().replace(" ", "_").replace("/", "_")


def cert_file(portalis_root, cert_name):
    return cert_root(portalis_root) / f"{_slugify(cert_name)}.json"


def list_certificates(portalis_root):
    root = cert_root(portalis_root)
    root.mkdir(parents=True, exist_ok=True)

    certs = []
    for f in root.glob("*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            certs.append(data)
        except Exception:
            continue

    return sorted(certs, key=lambda x: x.get("name", ""))


def load_certificate(portalis_root, cert_name):
    f = cert_file(portalis_root, cert_name)

    if not f.exists():
        return {
            "name": cert_name,
            "number": "",
            "issuer": "",
            "issue_date": "",
            "expiry_date": "",
            "notes": "",
        }

    return json.loads(f.read_text(encoding="utf-8"))


def save_certificate(
    portalis_root,
    name,
    number,
    issuer,
    issue_date,
    expiry_date,
    notes,
):
    root = cert_root(portalis_root)
    root.mkdir(parents=True, exist_ok=True)

    data = {
        "name": name,
        "number": number,
        "issuer": issuer,
        "issue_date": issue_date,
        "expiry_date": expiry_date,
        "notes": notes,
    }

    f = cert_file(portalis_root, name)
    f.write_text(json.dumps(data, indent=2), encoding="utf-8")