from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.errors import install_error_handlers
from app.core.headers import SafeHeaders
from app.core.logging import REQUEST_ID_HEADER, RequestLogging, configure_logging

configure_logging()

app = FastAPI(title="FlashCart", version="0.1.0")

# Added innermost first: Starlette runs the last one added on the outside, so
# logging wraps everything and sees the status every other layer settled on,
# including a refusal from CORS or a limit.
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_credentials=True,
    # Named rather than wildcarded. Credentials are sent on every request, so a
    # method or header this API does not actually use has no reason to be
    # allowed through from another origin.
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", REQUEST_ID_HEADER],
    expose_headers=[REQUEST_ID_HEADER, "Retry-After"],
    max_age=600,
)
app.add_middleware(SafeHeaders)
app.add_middleware(RequestLogging)

install_error_handlers(app)

app.include_router(api_router)
