import time
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.core.logging import get_logger

logger = get_logger(__name__)


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start_time = time.perf_counter()

        # Skip logging for health checks to keep logs cleaner
        if request.url.path.startswith("/api/v1/health"):
            return await call_next(request)

        # Process the request
        try:
            response = await call_next(request)
            process_time = time.perf_counter() - start_time
            logger.info(
                "request_processed",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                latency_ms=round(process_time * 1000, 2),
                client_ip=self._get_client_ip(request),
            )
            return response
        except Exception as exc:
            process_time = time.perf_counter() - start_time
            logger.error(
                "request_failed",
                method=request.method,
                path=request.url.path,
                latency_ms=round(process_time * 1000, 2),
                client_ip=self._get_client_ip(request),
                error=str(exc),
            )
            raise exc

    def _get_client_ip(self, request: Request) -> str:
        x_forwarded_for = request.headers.get("x-forwarded-for")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.client.host if request.client else "unknown"
