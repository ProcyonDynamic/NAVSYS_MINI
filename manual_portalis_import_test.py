from pathlib import Path
import json
import sys
from dataclasses import asdict, is_dataclass

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from modules.portalis_mini.archive.import_service import DocumentImportService

def main():
    portalis_root = Path("data/PORTALIS")

    svc = DocumentImportService(portalis_root)

    test_file = Path(r"D:\NAVSYS_USB\data\PORTALIS\test_inputs\sample_passport.pdf")
    owner_entity = "crew"
    owner_id = "crew_test_001"
    doc_type = "CREW_PASSPORT"

    result = svc.import_document(
        doc_type=doc_type,
        source_file=test_file,
        owner_entity=owner_entity,
        owner_id=owner_id,
    )

    print("\n=== PORTALIS IMPORT RESULT ===")
    print(json.dumps(_json_safe(result), indent=2, ensure_ascii=False))


def _json_safe(value):
    if is_dataclass(value):
        return _json_safe(asdict(value))

    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}

    if isinstance(value, list):
        return [_json_safe(v) for v in value]

    if isinstance(value, tuple):
        return [_json_safe(v) for v in value]

    if isinstance(value, Path):
        return str(value)

    return value


if __name__ == "__main__":
    main()