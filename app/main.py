from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.redirect import router as redirect_router
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import AppException, app_exception_handler
from app.core.logging import configure_logging, get_logger
from app.database.session import dispose_database_engine
from app.middleware.logging_middleware import StructuredLoggingMiddleware

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    logger.info("application_starting", app_name=settings.app_name, environment=settings.app_env)
    yield
    await dispose_database_engine()
    logger.info("application_stopped")


app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(StructuredLoggingMiddleware)
app.add_exception_handler(AppException, app_exception_handler)
app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/", tags=["Root"])
async def root() -> dict[str, str]:
    return {"service": settings.app_name, "status": "running"}


app.include_router(redirect_router)
