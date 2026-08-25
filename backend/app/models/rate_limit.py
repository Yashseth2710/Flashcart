from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import UUIDPrimaryKey


class RequestCount(UUIDPrimaryKey, Base):
    """How many times one caller has tried one thing inside one minute.

    Counting lives in Postgres because that is the only thing every copy of the
    app already shares. A second web process would otherwise keep its own tally
    and let a caller through twice as often, which is the failure that makes an
    in-memory counter worthless the moment the app is scaled.

    A row is a fixed window rather than a rolling one: the counter is stamped
    with the minute it belongs to, so a new minute finds no row and starts from
    nothing. That trades a little precision at the boundary for an increment
    that is a single statement and holds no lock anyone else is waiting on.
    """

    __tablename__ = "request_counts"
    __table_args__ = (
        UniqueConstraint("subject", "action", "window_start", name="uq_count_subject_window"),
        # Sweeping old windows reads by time alone and would otherwise scan.
        Index("ix_request_counts_window_start", "window_start"),
    )

    # Who is being counted: an account id for anything signed in, an address for
    # anything not. Kept as text so both fit without a second nullable column
    # and a constraint to say exactly one of them is filled.
    subject: Mapped[str] = mapped_column(String(128), nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    hits: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    def __repr__(self) -> str:
        return f"<RequestCount {self.action} {self.subject} {self.hits}>"
