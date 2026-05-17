import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from app.api.deps import get_current_user
from app.core.config import settings
from app.models.user import User

router = APIRouter(prefix="/help", tags=["help"])

HELP_CONFIG_PATH = Path(__file__).resolve().parents[2] / "data" / "help_items.json"
HELP_ASSETS_DIR = Path(__file__).resolve().parents[2] / "data" / "help-assets"
HELP_MANUAL_DOC_PATH = Path(__file__).resolve().parents[3] / "docs" / "OA系统内部培训使用手册.docx"


def _load_help_config() -> dict:
    if not HELP_CONFIG_PATH.exists():
        return {"menu": [], "sections": {}}
    return json.loads(HELP_CONFIG_PATH.read_text(encoding="utf-8"))


def _normalize_image_url(image_url: str | None) -> str:
    value = (image_url or "").strip()
    if not value:
        return ""
    if value.startswith("http://") or value.startswith("https://"):
        return value
    public_api_base_url = (settings.public_api_base_url or "").rstrip("/")
    if public_api_base_url and value.startswith("/api/v1/"):
        return f"{public_api_base_url}{value[len('/api/v1'):]}"
    return value


def _normalize_section(section: dict) -> dict:
    items = []
    for item in section.get("items", []):
        normalized_item = dict(item)
        normalized_item["image_url"] = _normalize_image_url(item.get("image_url"))
        items.append(normalized_item)
    return {
        **section,
        "items": items,
    }


@router.get("/menu")
def get_help_menu(_: User = Depends(get_current_user)) -> dict:
    data = _load_help_config()
    return {"items": data.get("menu", [])}


@router.get("/sections/{section_key}")
def get_help_section(section_key: str, _: User = Depends(get_current_user)) -> dict:
    data = _load_help_config()
    section = data.get("sections", {}).get(section_key)
    if not section:
        raise HTTPException(status_code=404, detail="帮助栏目不存在")
    return {"section": section_key, **_normalize_section(section)}


@router.get("/items/{item_key}")
def get_help_item(item_key: str, _: User = Depends(get_current_user)) -> dict:
    data = _load_help_config()
    for section_key, section in data.get("sections", {}).items():
        for item in section.get("items", []):
            if item.get("key") == item_key:
                normalized_item = dict(item)
                normalized_item["image_url"] = _normalize_image_url(item.get("image_url"))
                return {"section": section_key, **normalized_item}
    raise HTTPException(status_code=404, detail="帮助项不存在")


@router.get("/assets/{filename}")
def get_help_asset(filename: str) -> FileResponse:
    path = (HELP_ASSETS_DIR / filename).resolve()
    if not path.exists() or path.parent != HELP_ASSETS_DIR.resolve():
        raise HTTPException(status_code=404, detail="帮助图片不存在")
    return FileResponse(path=str(path), media_type="image/png", filename=path.name)


@router.get("/manual/download")
def download_help_manual(_: User = Depends(get_current_user)) -> FileResponse:
    if not HELP_MANUAL_DOC_PATH.exists():
        raise HTTPException(status_code=404, detail="培训手册不存在")
    return FileResponse(
        path=str(HELP_MANUAL_DOC_PATH),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=HELP_MANUAL_DOC_PATH.name,
    )
