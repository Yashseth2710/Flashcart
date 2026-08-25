"""Remove rate-limit windows that have passed.

Every caller leaves a row per action per minute, and none of them mean anything
once their minute is over. Nothing reads them, but they would accumulate for as
long as the shop is open, so something has to clear them out.

Run on a timer — hourly is plenty, since a window is a minute long and the
retention setting keeps an hour of them.

    python -m app.cli.sweep_counts
    python -m app.cli.sweep_counts --keep-minutes 30
"""

import argparse

from app.core.config import get_settings
from app.db.session import get_session_factory
from app.services.rate_limit import RateLimitService


def main() -> int:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Clear rate-limit windows that have passed.")
    parser.add_argument(
        "--keep-minutes",
        type=int,
        default=settings.request_count_retention_minutes,
        help="how much history to keep (default: %(default)s)",
    )
    args = parser.parse_args()

    session = get_session_factory()()
    try:
        removed = RateLimitService(session).sweep(keep_minutes=args.keep_minutes)
    finally:
        session.close()

    print(f"Cleared {removed} window{'s' if removed != 1 else ''}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
