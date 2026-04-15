"""Middleware that assigns a correlation ID to every request."""
import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from app.core.logging_config import request_id_var

HEADER = "X-Request-ID"


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        # Accept caller-supplied ID (useful for tracing between services)
        request_id = request.headers.get(HEADER) or str(uuid.uuid4())[:8]
        token = request_id_var.set(request_id)
        try:
            response = await call_next(request)
            response.headers[HEADER] = request_id
            return response
        finally:
            request_id_var.reset(token)
