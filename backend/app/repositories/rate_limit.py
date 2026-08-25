from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import RequestCount


def window_containing(moment: datetime) -> datetime:
    """The start of the minute a moment falls in.

    Truncating here rather than in SQL means the boundary is decided the same
    way whoever is asking, and the value can be compared in a test without
    reaching for the database.
    """
    return moment.replace(second=0, microsecond=0)


class RateLimitRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def count_attempt(self, subject: str, action: str, moment: datetime) -> int:
        """Records one attempt and answers how many that caller has made.

        The insert and the increment are one statement, so two requests arriving
        together cannot both read one and both write two. Whichever loses the
        race to the unique pair falls into the update and reads the number the
        winner left, which is what makes the tally correct under exactly the
        load a limit exists for.
        """
        statement = (
            insert(RequestCount)
            .values(subject=subject, action=action, window_start=window_containing(moment), hits=1)
            .on_conflict_do_update(
                constraint="uq_count_subject_window",
                set_={"hits": RequestCount.hits + 1},
            )
            .returning(RequestCount.hits)
        )
        return self.db.scalars(statement).one()

    def hits_in_window(self, subject: str, action: str, moment: datetime) -> int:
        """What the tally stands at without adding to it."""
        found = self.db.scalar(
            select(RequestCount.hits).where(
                RequestCount.subject == subject,
                RequestCount.action == action,
                RequestCount.window_start == window_containing(moment),
            )
        )
        return found or 0

    def forget_older_than(self, cutoff: datetime) -> int:
        """Drops windows nothing will read again.

        Without this the table only grows: every caller leaves a row per minute
        per action, and none of them mean anything once their minute has passed.
        """
        result = self.db.execute(delete(RequestCount).where(RequestCount.window_start < cutoff))
        return result.rowcount or 0
