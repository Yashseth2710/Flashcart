"""Structured logs, and the thread of a single request running through them.

Every line is JSON because logs are read by machines long before anyone opens
them by hand: a flash sale produces far too many to skim, and the questions
worth asking of them — how many were refused, how long checkout took, which
caller was throttled — are queries rather than searches.

Every line also carries the request it belongs to. Under load the lines from
one purchase are scattered among hundreds of others, and without a shared id
there is no way to put one person's story back together.
"""

import json
import logging
import sys
import time
import uuid
from contextvars import ContextVar
from typing import Any

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

REQUEST_ID_HEADER = "X-Request-ID"

# A context variable rather than an argument threaded through every call: the
# id is needed by log lines several layers below the request, and passing it
# down by hand would put plumbing in every signature it crossed.
current_request_id: ContextVar[str] = ContextVar("current_request_id", default="")


class JsonLines(logging.Formatter):
    """One JSON object per line, with whatever the call site attached."""

    def format(self, record: logging.LogRecord) -> str:
        line: dict[str, Any] = {
            "at": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname.lower(),
            "logger": record.name,
            "message": record.getMessage(),
        }
        request_id = current_request_id.get()
        if request_id:
            line["request_id"] = request_id
        if record.exc_info:
            line["error"] = self.formatException(record.exc_info)
        # Anything passed as extra= belongs in the line: that is the whole point
        # of structured logging over a formatted sentence.
        line.update(getattr(record, "fields", {}))
        return json.dumps(line, default=str)


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonLines())

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)

    # Uvicorn writes its own access line in its own shape, which would be a
    # second, less useful record of what the middleware below already logs.
    logging.getLogger("uvicorn.access").handlers = []
    logging.getLogger("uvicorn.access").propagate = False


logger = logging.getLogger("flashcart.request")


class RequestLogging(BaseHTTPMiddleware):
    """Gives each request an id, then says what happened to it.

    An id supplied by the caller is kept rather than replaced, so a trace that
    starts in the browser stays one trace across the boundary. It is echoed back
    on the response so someone reporting a problem has the exact string that
    finds their request in the logs.
    """

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER) or uuid.uuid4().hex
        token = current_request_id.set(request_id)
        # Also on the request itself, because the handler that turns an
        # unexpected failure into a 500 runs further in and does not see this
        # middleware's context. The id matters most in exactly that answer: it
        # is the only thing the person on the other end can quote back.
        request.state.request_id = request_id
        started = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception:
            # Logged here because the handler turns this into a 500 and the
            # detail would otherwise be lost between the two.
            logger.exception(
                "request failed",
                extra={"fields": _about(request, started)},
            )
            current_request_id.reset(token)
            raise

        response.headers[REQUEST_ID_HEADER] = request_id
        logger.info(
            "request served",
            extra={"fields": {**_about(request, started), "status": response.status_code}},
        )
        current_request_id.reset(token)
        return response


def _about(request: Request, started: float) -> dict[str, Any]:
    return {
        "method": request.method,
        "path": request.url.path,
        "took_ms": round((time.perf_counter() - started) * 1000, 1),
    }
