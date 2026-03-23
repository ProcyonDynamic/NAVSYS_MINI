import hashlib
import os
import shutil
import uuid
from datetime import datetime, timezone


def make_import_id() -> str:
    now = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%SZ")
    short_id = uuid.uuid4().hex[:8].upper()
    return f"IMP_{now}_{short_id}"


def ensure_dir(path: str) -> str:
    os.makedirs(path, exist_ok=True)
    return path


def file_sha256(path: str, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def copy_into_import_store(src_path: str, dst_dir: str) -> str:
    ensure_dir(dst_dir)
    base_name = os.path.basename(src_path)
    dst_path = os.path.join(dst_dir, base_name)
    shutil.copy2(src_path, dst_path)
    return dst_path