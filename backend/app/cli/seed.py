"""Stand up a database somebody can actually use.

One command between a blank Neon project and a working shop: the schema, a
catalogue with stock behind it, and an administrator to sign in as.

    python -m app.cli.seed --admin you@example.com --password 'something long'

Safe to run again. Migrations are skipped if they have already run, products
are matched on their slug and updated rather than duplicated, and an account
that already exists is promoted rather than replaced — a re-run never resets a
password or touches anybody's orders.

It deliberately creates no sale. A sale is a decision about what is on offer
and when, which belongs to whoever is running the shop; the admin pages exist
for exactly that. Seeding one would also age badly, since a sale is only
running between its own start and end times and would be over by the time
anyone visited.
"""

import argparse
import subprocess
import sys
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.cli.import_catalogue import fetch, store
from app.core.security import hash_password
from app.db.session import get_session_factory
from app.models import Inventory, Product, User, UserRole
from app.services.auth import normalise_email

# The project root, where alembic.ini sits.
BACKEND = Path(__file__).resolve().parents[2]


def migrate() -> None:
    """Bring the schema up to date, whatever state it starts in."""
    print("Applying migrations...")
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND,
        check=True,
    )


def fill_catalogue(db: Session, limit: int) -> None:
    print(f"Fetching up to {limit} products...")
    added, updated = store(db, fetch(limit))
    db.commit()
    print(f"  {added} added, {updated} updated.")


def make_admin(db: Session, email: str, password: str, name: str) -> User:
    """The account whoever runs the shop signs in as.

    Registration only ever creates customers, so the first administrator has to
    be made here. An account that already exists is promoted and left otherwise
    alone: re-running the seed must not quietly change somebody's password.
    """
    address = normalise_email(email)
    user = db.scalar(select(User).where(User.email == address))

    if user is None:
        user = User(
            name=name,
            email=address,
            password_hash=hash_password(password),
            role=UserRole.ADMIN,
        )
        db.add(user)
        print(f"  Created {address} as an administrator.")
    elif user.role is not UserRole.ADMIN:
        user.role = UserRole.ADMIN
        print(f"  {address} already existed; made it an administrator.")
    else:
        print(f"  {address} is already an administrator; left as it is.")

    db.commit()
    return user


def describe(db: Session) -> None:
    """What is now there, so the run ends with something checkable."""
    products = db.scalar(select(func.count()).select_from(Product)) or 0
    stock = db.scalar(select(func.coalesce(func.sum(Inventory.total_quantity), 0))) or 0
    admins = (
        db.scalar(select(func.count()).select_from(User).where(User.role == UserRole.ADMIN)) or 0
    )
    print(f"\n{products} products, {stock} units of stock, {admins} administrator(s).")
    print("Sign in and open /admin/sales to put a sale on.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Set up a usable FlashCart database.")
    parser.add_argument("--admin", required=True, help="email for the administrator account")
    parser.add_argument("--password", required=True, help="password for that account")
    parser.add_argument("--name", default="Administrator", help="name on the account")
    parser.add_argument("--limit", type=int, default=100, help="how many products to import")
    parser.add_argument(
        "--skip-migrations",
        action="store_true",
        help="assume the schema is already up to date",
    )
    args = parser.parse_args()

    if args.limit < 1:
        print("--limit must be at least 1.", file=sys.stderr)
        return 1
    if len(args.password) < 12:
        print("--password must be at least 12 characters.", file=sys.stderr)
        return 1

    if not args.skip_migrations:
        migrate()

    session = get_session_factory()()
    try:
        fill_catalogue(session, args.limit)
        print("Setting up the administrator...")
        make_admin(session, args.admin, args.password, args.name)
        describe(session)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
