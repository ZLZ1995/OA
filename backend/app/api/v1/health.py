from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["健康检查"])


@router.get("")
def health() -> dict[str, str]:
    return {"status": "ok"}
