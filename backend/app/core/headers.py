"""Headers that tell a browser what this API is not.

An API that only ever answers JSON has no business being framed, sniffed into
a different content type, or sent as a referrer to somebody else. Each of these
closes off a way a response could be reused as something it was never meant to
be.
"""

from typing import Any

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

SAFE_HEADERS = {
    # Answers are JSON. A browser guessing otherwise is only ever a mistake.
    "X-Content-Type-Options": "nosniff",
    # Nothing here is meant to be displayed inside someone else's page.
    "X-Frame-Options": "DENY",
    # A path can carry an id worth keeping out of another site's logs.
    "Referrer-Policy": "no-referrer",
    # Nothing served here needs a camera, a microphone, or a location.
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    # There is no markup to execute, so nothing needs to be allowed to load.
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
}

# The two pages FastAPI serves as HTML rather than JSON. They pull the script
# and stylesheet that draw them, which the policy above exists to forbid, so
# they are given the rest of the headers and not that one.
BROWSABLE = ("/docs", "/redoc")


class SafeHeaders(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Any) -> Response:
        response = await call_next(request)
        browsable = request.url.path.rstrip("/") in BROWSABLE
        for name, value in SAFE_HEADERS.items():
            if browsable and name == "Content-Security-Policy":
                continue
            response.headers.setdefault(name, value)
        return response
