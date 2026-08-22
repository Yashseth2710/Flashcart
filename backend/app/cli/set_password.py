"""Set an account's password from the command line.

For when someone is locked out and there is no reset flow yet:

    python -m app.cli.set_password someone@example.com

The password is asked for rather than passed as an argument, so it does not end
up in the shell history.
"""

import argparse
import getpass
import sys

from app.core.security import hash_password
from app.db.session import get_session_factory
from app.repositories.user import UserRepository
from app.services.auth import normalise_email

MINIMUM_LENGTH = 8


def main() -> int:
    parser = argparse.ArgumentParser(description="Set an account password.")
    parser.add_argument("email", help="the account to change")
    args = parser.parse_args()

    session = get_session_factory()()
    try:
        user = UserRepository(session).get_by_email(normalise_email(args.email))
        if user is None:
            print(f"No account for {args.email}.", file=sys.stderr)
            return 1

        password = getpass.getpass("New password: ")
        if len(password) < MINIMUM_LENGTH:
            print(f"Use at least {MINIMUM_LENGTH} characters.", file=sys.stderr)
            return 1
        if password != getpass.getpass("Again: "):
            print("Those did not match.", file=sys.stderr)
            return 1

        user.password_hash = hash_password(password)
        session.commit()
        print(f"Password set for {user.email}.")
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
