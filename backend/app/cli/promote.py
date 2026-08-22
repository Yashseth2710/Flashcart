"""Grant or revoke admin rights on an account.

Registration only ever creates customers, so the first administrator has to be
made here.

    python -m app.cli.promote someone@example.com
    python -m app.cli.promote someone@example.com --revoke
"""

import argparse
import sys

from app.db.session import get_session_factory
from app.models import UserRole
from app.repositories.user import UserRepository
from app.services.auth import normalise_email


def main() -> int:
    parser = argparse.ArgumentParser(description="Grant or revoke admin rights.")
    parser.add_argument("email", help="the account to change")
    parser.add_argument("--revoke", action="store_true", help="make the account a customer again")
    args = parser.parse_args()

    role = UserRole.CUSTOMER if args.revoke else UserRole.ADMIN
    session = get_session_factory()()
    try:
        user = UserRepository(session).get_by_email(normalise_email(args.email))
        if user is None:
            print(f"No account for {args.email}.", file=sys.stderr)
            return 1

        if user.role is role:
            print(f"{user.email} is already {role.value}.")
            return 0

        user.role = role
        session.commit()
        print(f"{user.email} is now {role.value}.")
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
