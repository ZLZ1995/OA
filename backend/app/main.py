import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.db.init_db import init_db

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Initialize database objects and seed basic data on startup."""
    try:
        init_db()
        logger.info('Database initialized successfully.')
    except Exception as exc:
        logger.exception('Database initialization failed during startup: %s', exc)
        if settings.db_init_required:
            raise
        logger.warning(
            'Continue startup without database initialization because DB_INIT_REQUIRED is false.'
        )
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/", tags=["health"])
async def root_health():
    """Public root health endpoint for ingress/domain verification."""
    return {"service": "zhongqin-oa-backend", "status": "ok"}


@app.middleware("http")
async def log_request_trace(request: Request, call_next):
    """Log request/response trace for cloud ingress troubleshooting."""
    response = await call_next(request)
    logger.info(
        "trace method=%s path=%s status=%s host=%s origin=%s forwarded_for=%s",
        request.method,
        request.url.path,
        response.status_code,
        request.headers.get("host"),
        request.headers.get("origin"),
        request.headers.get("x-forwarded-for"),
    )
    return response
