"""Where each limit is applied, and to whom.

Kept apart from the routes so the numbers are all readable in one place rather
than scattered across the endpoints they guard.
"""

import uuid
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.dependencies import CurrentUser
from app.db.session import get_session_factory
from app.services.rate_limit import RateLimitService


def counting_session() -> Session:
    """A session of its own for the tally.

    Attempts are committed the moment they are counted, which cannot be done on
    the session serving the request: that one is mid-flight, and committing it
    would write out half-finished work.

    Deliberately not a dependency that yields. FastAPI holds a yielded session
    open until after the response, so every request would occupy two connections
    for its whole life and the pool would run out under exactly the load a limit
    exists for. This hands back a session whose closing is the caller's job, so
    the connection is returned in milliseconds rather than held for the request.

    Overridden in tests to point at the test's own session, so a tally rolls
    back with everything else rather than outliving the test that made it.
    """
    return get_session_factory()()


CountingSession = Annotated[Session, Depends(counting_session)]


def count_against(subject: str, action: str, limit: int, counting: Session) -> None:
    """Counts one attempt, holding the connection only while it does.

    The count is a single statement, so the connection goes back to the pool
    immediately rather than being tied up behind the row lock and the payment
    that follow it. Refusals close it too: being over the limit is the busiest
    moment there is, and leaking a connection there is what would turn a guard
    against hoarding into the thing that takes the sale down.
    """
    try:
        RateLimitService(counting).check(subject, action, limit)
    finally:
        counting.close()


def caller_address(request: Request) -> str:
    """Who to count when there is no account to count.

    A proxy puts the real address in X-Forwarded-For and appends its own, so the
    first entry is the client. This is only as trustworthy as the proxy in front
    of it — a header is easy to write by hand — which is why nothing that
    protects stock is keyed on it. It guards the sign-in pair, where the caller
    has no account yet and there is nothing better to go on.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        first = forwarded.split(",")[0].strip()
        if first:
            return f"ip:{first}"
    client = request.client
    return f"ip:{client.host}" if client else "ip:unknown"


def _account(user_id: uuid.UUID) -> str:
    return f"user:{user_id}"


def limit_holds(user: CurrentUser, counting: CountingSession) -> None:
    """Placing holds is the one worth guarding most closely: a hold takes stock
    out of everyone else's reach for minutes at a time."""
    count_against(_account(user.id), "holds", get_settings().holds_per_minute, counting)


def limit_checkouts(user: CurrentUser, counting: CountingSession) -> None:
    count_against(_account(user.id), "checkouts", get_settings().checkouts_per_minute, counting)


def limit_marks(user: CurrentUser, counting: CountingSession) -> None:
    """Keeps and reminders are cheap and tapped often, so this sits high enough
    to only catch something automated."""
    count_against(_account(user.id), "marks", get_settings().marks_per_minute, counting)


def limit_logins(request: Request, counting: CountingSession) -> None:
    """Counted per address rather than per account, on purpose.

    Someone working through a password list moves across accounts, so counting
    by the account they name would give each guess a fresh allowance. Counting
    where the guesses come from is what actually slows them down.
    """
    count_against(caller_address(request), "logins", get_settings().logins_per_minute, counting)


def limit_registrations(request: Request, counting: CountingSession) -> None:
    count_against(
        caller_address(request),
        "registrations",
        get_settings().registrations_per_minute,
        counting,
    )


LimitHolds = Depends(limit_holds)
LimitCheckouts = Depends(limit_checkouts)
LimitMarks = Depends(limit_marks)
LimitLogins = Depends(limit_logins)
LimitRegistrations = Depends(limit_registrations)

__all__ = [
    "LimitCheckouts",
    "LimitHolds",
    "LimitLogins",
    "LimitMarks",
    "LimitRegistrations",
    "caller_address",
    "counting_session",
]
