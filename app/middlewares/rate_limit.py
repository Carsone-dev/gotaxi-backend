import time
from collections import defaultdict
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-process rate limiter par IP. Pour la prod, utiliser Redis."""

    LIMITS: dict[str, tuple[int, int]] = {
        "/api/v1/auth/login": (10, 60),
        "/api/v1/auth/otp/send": (5, 300),
        "/api/v1/auth/password/forgot": (3, 300),
        "/api/v1/chauffeurs/me/position": (20, 60),
    }

    def __init__(self, app):
        super().__init__(app)
        self._counters: dict[str, list[float]] = defaultdict(list)

    def _get_client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        limit_conf = self.LIMITS.get(path)
        if limit_conf is None:
            return await call_next(request)

        max_requests, window_seconds = limit_conf
        ip = self._get_client_ip(request)
        key = f"{ip}:{path}"
        now = time.time()

        self._counters[key] = [t for t in self._counters[key] if now - t < window_seconds]
        if len(self._counters[key]) >= max_requests:
            return JSONResponse(
                status_code=429,
                content={"error": {"code": "RATE_LIMIT", "message": "Trop de requêtes. Réessayez plus tard."}},
                headers={"Retry-After": str(window_seconds)},
            )

        self._counters[key].append(now)
        return await call_next(request)