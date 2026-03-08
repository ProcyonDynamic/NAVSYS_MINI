from pathlib import Path
import json
import uuid


def crew_root(portalis_root):
    return Path(portalis_root) / "crew"


def crew_folder(portalis_root, crew_id):
    return crew_root(portalis_root) / crew_id


def crew_record_path(portalis_root, crew_id):
    return crew_folder(portalis_root, crew_id) / "record.json"


def list_crew(portalis_root):
    root = crew_root(portalis_root)

    if not root.exists():
        return []

    crew = []

    for folder in root.iterdir():
        if not folder.is_dir():
            continue

        record = folder / "record.json"
        if record.exists():
            data = json.loads(record.read_text(encoding="utf-8"))
            crew.append({
                "crew_id": folder.name,
                "name": data.get("name", ""),
                "rank": data.get("rank", ""),
                "documents_count": len(data.get("documents", [])),
            })

    crew.sort(key=lambda x: (x["rank"], x["name"]))
    return crew


def load_crew_record(portalis_root, crew_id):
    p = crew_record_path(portalis_root, crew_id)
    if not p.exists():
        raise FileNotFoundError(f"Crew record not found: {crew_id}")
    return json.loads(p.read_text(encoding="utf-8"))


def save_crew_record(portalis_root, crew_id, data):
    p = crew_record_path(portalis_root, crew_id)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def create_crew(portalis_root, name, rank):
    crew_id = f"crew_{uuid.uuid4().hex[:6]}"

    root = crew_root(portalis_root)
    folder = root / crew_id

    folder.mkdir(parents=True, exist_ok=True)
    (folder / "docs").mkdir(exist_ok=True)
    (folder / "parsed").mkdir(exist_ok=True)
    (folder / "history").mkdir(exist_ok=True)

    record = {
        "crew_id": crew_id,
        "name": name,
        "rank": rank,
        "nationality": "",
        "documents": []
    }

    save_crew_record(portalis_root, crew_id, record)
    return crew_id


def add_document_to_crew(
    portalis_root,
    crew_id,
    *,
    doc_type,
    doc_subtype="",
    document_number="",
    country="",
    issue_date="",
    expiry_date="",
    is_primary=False,
    status="ACTIVE",
    source_file="",
    confidence="",
    notes="",
):
    data = load_crew_record(portalis_root, crew_id)

    doc_id = f"{doc_type.lower()}_{uuid.uuid4().hex[:6]}"

    new_doc = {
        "doc_id": doc_id,
        "doc_type": doc_type,
        "doc_subtype": doc_subtype,
        "document_number": document_number,
        "country": country,
        "issue_date": issue_date,
        "expiry_date": expiry_date,
        "is_primary": bool(is_primary),
        "status": status,
        "source_file": source_file,
        "confidence": confidence,
        "notes": notes,
    }

    if is_primary:
        for d in data.get("documents", []):
            if d.get("doc_type") == doc_type:
                d["is_primary"] = False

    data.setdefault("documents", []).append(new_doc)
    save_crew_record(portalis_root, crew_id, data)

    return doc_id