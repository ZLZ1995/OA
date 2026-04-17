from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.core.config import settings


def save_upload_file(upload: UploadFile) -> tuple[str, int]:
    ext = Path(upload.filename or "").suffix
    key = f"{uuid4().hex}{ext}"
    root = Path(settings.local_storage_dir)
    root.mkdir(parents=True, exist_ok=True)
    path = root / key

    content = upload.file.read()
    path.write_bytes(content)
    return key, len(content)
