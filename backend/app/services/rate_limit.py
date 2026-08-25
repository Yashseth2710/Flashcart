from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import TooManyAttempts
from app.repositories.rate_limit import RateLimitRepository, window_containing


def now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True)
class Allowance:
    """What one caller has left of one limit."""

    limit: int
    used: int
    retry_after_seconds: int

    @property
    def remaining(self) -> int:
        return max(self.limit - self.used, 0)

    @property
    def exceeded(self) -> bool:
        return self.used > self.limit


class RateLimitService:
    """Refuses a caller going faster than a person plausibly could.

    This is not part of the oversell guarantee and must never be mistaken for
    it. Stock is protected by the row lock and the check constraint, which hold
    whatever arrives; a limit only keeps one caller from spending the whole
    sale's capacity on retries nobody asked for.

    Counting is deliberately kept off the request's own transaction. A refused
    or failed request rolls its work back, and if the tally rolled back with it
    a caller could fail forever at no cost — which is precisely the caller worth
    limiting. Attempts are recorded on a session of their own and committed
    immediately, so they stand regardless of how the request ends.
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self.counts = RateLimitRepository(db)

    def check(self, subject: str, action: str, limit: int) -> Allowance:
        """Counts this attempt, and refuses it if the caller is over.

        The count is written and committed before the decision is made, so an
        attempt that is about to be refused has already been paid for. That
        ordering is the whole point: it is what stops a caller who is over the
        limit from retrying for free.
        """
        moment = now()
        used = self.counts.count_attempt(subject, action, moment)
        self.db.commit()

        allowance = Allowance(limit=limit, used=used, retry_after_seconds=_seconds_left(moment))
        if allowance.exceeded:
            raise TooManyAttempts(allowance.retry_after_seconds)
        return allowance

    def sweep(self, keep_minutes: int | None = None) -> int:
        """Removes windows nothing will read again."""
        minutes = (
            keep_minutes
            if keep_minutes is not None
            else get_settings().request_count_retention_minutes
        )
        removed = self.counts.forget_older_than(
            window_containing(now()) - timedelta(minutes=minutes)
        )
        self.db.commit()
        return removed


def _seconds_left(moment: datetime) -> int:
    """How long until the window turns over and the tally starts again."""
    next_window = window_containing(moment) + timedelta(minutes=1)
    return max(int((next_window - moment).total_seconds()), 1)
