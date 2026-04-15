import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.exc import SQLAlchemyError

from app.api.router import api_router
from app.core.config import settings
from app.db.init_db import init_db

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Initialize database objects and seed basic data on startup."""
    try:
        init_db()
        logger.info("Database initialized successfully.")
    except SQLAlchemyError as exc:
        logger.exception("Database initialization failed during startup: %s", exc)
        if settings.db_init_required:
            raise
        logger.warning("Continue startup without database initialization because DB_INIT_REQUIRED=false")
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": f"{settings.app_name} 已启动"}
