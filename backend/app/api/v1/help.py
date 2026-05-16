import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/help", tags=["help"])

HELP_CONFIG_PATH = Path(__file__).resolve().parents[2] / "data" / "help_items.json"


def _load_help_config() -> dict:
    if not HELP_CONFIG_PATH.exists():
        return {"menu": [], "sections": {}}
    return json.loads(HELP_CONFIG_PATH.read_text(encoding="utf-8"))


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
    return {"section": section_key, **section}


@router.get("/items/{item_key}")
def get_help_item(item_key: str, _: User = Depends(get_current_user)) -> dict:
    data = _load_help_config()
    for section_key, section in data.get("sections", {}).items():
        for item in section.get("items", []):
            if item.get("key") == item_key:
                return {"section": section_key, **item}
    raise HTTPException(status_code=404, detail="帮助项不存在")
