from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.api.deps import require_roles
from app.core.config import settings

router = APIRouter(prefix="/desktop-updates", tags=["桌面更新"])

ALLOWED_FILENAMES = {
    "latest.yml",
    "release.json",
    "中勤评估业务OA系统 Setup 0.2.0.exe",
    "中勤评估业务OA系统 Setup 0.2.0.exe.blockmap",
}


def _stable_update_dir() -> Path:
    root = Path(settings.desktop_update_root_dir)
    target = root / "win" / "stable"
    target.mkdir(parents=True, exist_ok=True)
    return target


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_desktop_update_file(
    upload: UploadFile = File(...),
    _: set[str] = Depends(require_roles("ADMIN")),
) -> dict:
    filename = (upload.filename or "").strip()
    if not filename:
        raise HTTPException(status_code=400, detail="缺少文件名")
    if filename not in ALLOWED_FILENAMES:
        raise HTTPException(
            status_code=400,
            detail="仅允许上传 latest.yml、release.json、0.2.0 安装包和对应 blockmap",
        )

    target_path = _stable_update_dir() / filename
    content = await upload.read()
    if not content:
        raise HTTPException(status_code=400, detail="上传文件为空")

    target_path.write_bytes(content)

    return {
        "fileName": filename,
        "size": len(content),
        "path": str(target_path),
        "publicUrl": f"/desktop-updates/win/stable/{filename}",
    }
