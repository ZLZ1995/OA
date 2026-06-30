from __future__ import annotations

import hashlib
import json
import math
import os
import re
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

from app.api.deps import require_roles
from app.core.config import settings

router = APIRouter(prefix="/desktop-updates", tags=["桌面更新"])

SETUP_FILE_PATTERN = re.compile(
    r"^zhongqin-oa-setup-\d+\.\d+\.\d+\.exe(\.blockmap)?$"
)
UPLOAD_METADATA_FILENAME = "session.json"


class UploadSessionCreatePayload(BaseModel):
    file_name: str = Field(..., min_length=1, max_length=255)
    total_size: int = Field(..., gt=0)
    chunk_size: int = Field(..., gt=0, le=16 * 1024 * 1024)
    sha256: str = Field(..., min_length=64, max_length=64)


class UploadSessionCompletePayload(BaseModel):
    upload_id: str = Field(..., min_length=1, max_length=64)


def _is_allowed_filename(filename: str) -> bool:
    if filename in {"latest.yml", "release.json"}:
        return True
    return bool(SETUP_FILE_PATTERN.match(filename))


def _normalize_filename(filename: str) -> str:
    normalized = filename.strip()
    if not normalized:
        raise HTTPException(status_code=400, detail="缺少文件名")
    if not _is_allowed_filename(normalized):
        raise HTTPException(
            status_code=400,
            detail="仅允许上传 latest.yml、release.json 或桌面安装包及对应 blockmap",
        )
    return normalized


def _stable_update_dir() -> Path:
    root = Path(settings.desktop_update_root_dir)
    target = root / "win" / "stable"
    target.mkdir(parents=True, exist_ok=True)
    return target


def _chunk_upload_root() -> Path:
    root = Path(settings.desktop_update_root_dir) / ".uploads"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _session_dir(upload_id: str) -> Path:
    if not re.fullmatch(r"[a-f0-9-]{36}", upload_id):
        raise HTTPException(status_code=400, detail="upload_id 不合法")
    return _chunk_upload_root() / upload_id


def _session_metadata_path(upload_id: str) -> Path:
    return _session_dir(upload_id) / UPLOAD_METADATA_FILENAME


def _load_session_metadata(upload_id: str) -> dict:
    metadata_path = _session_metadata_path(upload_id)
    if not metadata_path.exists():
        raise HTTPException(status_code=404, detail="上传会话不存在")
    try:
        return json.loads(metadata_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail="上传会话元数据损坏") from exc


def _write_session_metadata(upload_id: str, payload: dict) -> None:
    session_dir = _session_dir(upload_id)
    session_dir.mkdir(parents=True, exist_ok=True)
    metadata_path = _session_metadata_path(upload_id)
    metadata_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _chunk_path(upload_id: str, chunk_index: int) -> Path:
    if chunk_index < 0:
        raise HTTPException(status_code=400, detail="chunk_index 必须大于等于 0")
    return _session_dir(upload_id) / f"{chunk_index:08d}.part"


def _calculate_sha256(file_path: Path) -> str:
    digest = hashlib.sha256()
    with file_path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _assemble_uploaded_file(metadata: dict, upload_id: str) -> Path:
    session_dir = _session_dir(upload_id)
    assembled_path = session_dir / metadata["file_name"]
    with assembled_path.open("wb") as target_handle:
        for chunk_index in range(metadata["chunk_count"]):
            part_path = _chunk_path(upload_id, chunk_index)
            if not part_path.exists():
                raise HTTPException(
                    status_code=400,
                    detail=f"缺少分片 {chunk_index}",
                )
            with part_path.open("rb") as source_handle:
                shutil.copyfileobj(source_handle, target_handle)
    return assembled_path


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_desktop_update_file(
    upload: UploadFile = File(...),
    _: set[str] = Depends(require_roles("ADMIN")),
) -> dict:
    filename = _normalize_filename(upload.filename or "")
    content = await upload.read()
    if not content:
        raise HTTPException(status_code=400, detail="上传文件为空")

    target_path = _stable_update_dir() / filename
    target_path.write_bytes(content)

    return {
        "fileName": filename,
        "size": len(content),
        "path": str(target_path),
        "publicUrl": f"/desktop-updates/win/stable/{filename}",
    }


@router.post("/upload-session", status_code=status.HTTP_201_CREATED)
def create_desktop_update_upload_session(
    payload: UploadSessionCreatePayload,
    _: set[str] = Depends(require_roles("ADMIN")),
) -> dict:
    file_name = _normalize_filename(payload.file_name)
    if file_name in {"latest.yml", "release.json"}:
        raise HTTPException(
            status_code=400,
            detail="latest.yml 和 release.json 请继续使用普通上传接口",
        )

    sha256_value = payload.sha256.strip().lower()
    if not re.fullmatch(r"[a-f0-9]{64}", sha256_value):
        raise HTTPException(status_code=400, detail="sha256 格式不正确")

    upload_id = str(uuid.uuid4())
    chunk_count = math.ceil(payload.total_size / payload.chunk_size)
    metadata = {
        "upload_id": upload_id,
        "file_name": file_name,
        "total_size": payload.total_size,
        "chunk_size": payload.chunk_size,
        "chunk_count": chunk_count,
        "sha256": sha256_value,
    }
    _write_session_metadata(upload_id, metadata)

    return {
        "uploadId": upload_id,
        "fileName": file_name,
        "chunkSize": payload.chunk_size,
        "chunkCount": chunk_count,
        "tempDir": str(_session_dir(upload_id)),
    }


@router.post("/upload-chunk", status_code=status.HTTP_201_CREATED)
async def upload_desktop_update_chunk(
    upload_id: str = Form(...),
    chunk_index: int = Form(...),
    upload: UploadFile = File(...),
    _: set[str] = Depends(require_roles("ADMIN")),
) -> dict:
    metadata = _load_session_metadata(upload_id)
    if chunk_index >= metadata["chunk_count"]:
        raise HTTPException(status_code=400, detail="chunk_index 超出范围")

    content = await upload.read()
    if not content:
        raise HTTPException(status_code=400, detail="上传分片为空")

    expected_size = metadata["chunk_size"]
    if chunk_index == metadata["chunk_count"] - 1:
        expected_size = metadata["total_size"] - metadata["chunk_size"] * chunk_index

    if len(content) != expected_size:
        raise HTTPException(
            status_code=400,
            detail=f"分片大小不正确，期望 {expected_size}，实际 {len(content)}",
        )

    part_path = _chunk_path(upload_id, chunk_index)
    part_path.write_bytes(content)

    return {
        "uploadId": upload_id,
        "chunkIndex": chunk_index,
        "size": len(content),
        "path": str(part_path),
    }


@router.post("/upload-complete", status_code=status.HTTP_201_CREATED)
def complete_desktop_update_upload(
    payload: UploadSessionCompletePayload,
    _: set[str] = Depends(require_roles("ADMIN")),
) -> dict:
    metadata = _load_session_metadata(payload.upload_id)
    session_dir = _session_dir(payload.upload_id)

    assembled_path = _assemble_uploaded_file(metadata, payload.upload_id)
    actual_size = assembled_path.stat().st_size
    if actual_size != metadata["total_size"]:
        raise HTTPException(
            status_code=400,
            detail=f"合并后文件大小不正确，期望 {metadata['total_size']}，实际 {actual_size}",
        )

    actual_sha256 = _calculate_sha256(assembled_path)
    if actual_sha256 != metadata["sha256"]:
        raise HTTPException(status_code=400, detail="文件哈希校验失败")

    target_path = _stable_update_dir() / metadata["file_name"]
    temp_target_path = target_path.with_suffix(target_path.suffix + ".uploading")
    shutil.move(str(assembled_path), str(temp_target_path))
    os.replace(temp_target_path, target_path)
    shutil.rmtree(session_dir, ignore_errors=True)

    return {
        "uploadId": payload.upload_id,
        "fileName": metadata["file_name"],
        "size": actual_size,
        "sha256": actual_sha256,
        "path": str(target_path),
        "publicUrl": f"/desktop-updates/win/stable/{metadata['file_name']}",
    }
