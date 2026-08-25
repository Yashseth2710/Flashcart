"""One shape for everything that goes wrong.

A client should not have to know which layer refused it. Whether a route said
no, a body failed validation, or something broke unexpectedly, the answer has
the same keys — so the frontend has one thing to read and one thing to show.

The shape keeps `detail` as its message because that is what FastAPI's own
errors use and what the frontend already reads. This adds to that rather than
replacing it, so nothing that already worked has to change.
"""

import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import REQUEST_ID_HEADER, current_request_id

logger = logging.getLogger("flashcart.error")


def _request_id(request: Request | None) -> str:
    """The id this request was logged under.

    Read from the request first: the handler for an unexpected failure runs
    inside the middleware that set the context variable, where it is no longer
    visible. That is the one answer the id matters most in.
    """
    from_request = getattr(getattr(request, "state", None), "request_id", "")
    return from_request or current_request_id.get()


def problem(
    status_code: int,
    detail: str,
    *,
    request: Request | None = None,
    headers: dict[str, str] | None = None,
    fields: list[dict[str, str]] | None = None,
) -> JSONResponse:
    body: dict[str, Any] = {"detail": detail, "status": status_code}

    request_id = _request_id(request)
    if request_id:
        body["request_id"] = request_id

    if fields:
        body["fields"] = fields

    answer = JSONResponse(status_code=status_code, content=body, headers=headers)
    if request_id:
        answer.headers[REQUEST_ID_HEADER] = request_id
    return answer


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def refused(request: Request, error: StarletteHTTPException) -> JSONResponse:
        """Everything raised deliberately: the exceptions in core.exceptions,
        plus the 404s and 405s the router raises on its own."""
        detail = error.detail if isinstance(error.detail, str) else "That request was refused."
        return problem(
            error.status_code, detail, request=request, headers=dict(error.headers or {})
        )

    @app.exception_handler(RequestValidationError)
    async def malformed(request: Request, error: RequestValidationError) -> JSONResponse:
        """A body that does not fit the schema.

        Which field was wrong is named, because that is the one thing the person
        filling in a form needs and cannot guess. The value they sent is not
        echoed back: it may be a password.
        """
        fields = [
            {
                "field": ".".join(str(part) for part in problem_at["loc"][1:]) or "body",
                "problem": problem_at["msg"],
            }
            for problem_at in error.errors()
        ]
        return problem(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Some of that was not filled in correctly.",
            request=request,
            fields=fields,
        )

    @app.exception_handler(Exception)
    async def unexpected(request: Request, error: Exception) -> JSONResponse:
        """Anything nobody planned for.

        The cause goes to the logs in full and to the client not at all. A stack
        trace or a database message tells whoever is probing how the inside is
        built, and tells an ordinary shopper nothing they can act on. They get
        the request id instead, which is what turns "it broke" into a line
        somebody can actually look up.

        The wording promises nothing about what did or did not happen. Checkout
        charges before it commits, so a failure in that gap could leave a
        payment taken and no order written; saying "nothing was charged" here
        would be a guess, and the one time it was wrong it would be wrong about
        somebody's money.
        """
        logger.exception("unhandled error", exc_info=error)
        return problem(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Something went wrong on our side. Check your orders before trying again.",
            request=request,
        )
