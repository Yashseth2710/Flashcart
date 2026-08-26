# FlashCart

Buy before it's gone. Built to handle the rush.

FlashCart is a flash-sale storefront for limited stock. The shop is the easy part. The hard
part is what happens when four hundred people reach for fifty units in the same second:
fifty of them must get one, three hundred and fifty must be told straight away, and the
number sold must be fifty. Not fifty-one.

That guarantee is the whole project. Everything else here exists to make it visible.

## How overselling is prevented

Two independent things stop it, and they fail differently on purpose.

**A row lock decides the order.** Every request that wants the same item queues at the same
row. Whoever holds it reads counters that already include every hold placed before them,
rather than a snapshot taken before the queue formed.

```
                    ┌─────────────────────────────────────────┐
   400 requests     │  BEGIN                                  │
   for 50 units     │                                         │
        │           │  SELECT … FOR UPDATE   ← one at a time  │
        ├──────────►│         │                               │
        ├──────────►│         ▼                               │
        ├──────────►│  reserved + sold + wanted <= allocated? │
        ├──────────►│         │                               │
        │           │    ┌────┴────┐                          │
       ...          │   yes        no                         │
        │           │    │          │                         │
        ├──────────►│  reserved   409 Sold out                │
        └──────────►│  += wanted    │                         │
                    │    │          │                         │
                    │  COMMIT ──────┴──► lock released        │
                    └─────────────────────────────────────────┘
                              50 succeed. 350 are told.
```

**A CHECK constraint is the last word.** `reserved + sold <= allocated` lives in PostgreSQL.
If the lock were ever removed, or a new code path forgot it, the database still refuses to
write an impossible number. The application cannot overrule it.

The suite proves both. Removing `.with_for_update()` fails nine of the fourteen concurrency
tests — and the five that still pass are the single-unit cases the constraint catches on its
own, which is exactly why those tests are parametrised over several stock levels.

## What a hold is

Reserving is not buying. It puts one unit aside and starts a clock.

```
   place ──► ACTIVE ──── checkout ────► COMPLETED   the unit is sold
               │
               ├──────── let go ──────► CANCELLED   back on the shelf
               │
               └──────── time up ─────► EXPIRED     back on the shelf
```

Expiry is read from the clock rather than swept into place, so a hold whose time has passed
is already expired to everyone who looks — no scheduler has to have run first. Sale status
works the same way: `UPCOMING`, `ACTIVE` and `ENDED` are computed from start and end times,
never stored, so they can never go stale.

## Buying twice is impossible

Checkout is idempotent, guarded twice over. An idempotency key is claimed *before* the card
is charged, so a retry arriving mid-payment cannot charge again. And a unique index on
`orders.reservation_id` means that even if two requests somehow got past the key, the second
insert is refused by the database — and the loser returns the winner's order, because that
is the order the person is owed.

Twenty concurrent retries of one checkout produce one order, and all twenty responses carry
its id.

## Stack

Next.js 16 and TypeScript on the front. FastAPI, SQLAlchemy 2 and Alembic behind it. Neon
PostgreSQL underneath, reached through its pooled endpoint. Pytest and Playwright for tests,
Ruff and ESLint for lint, GitHub Actions on every push.

The backend is layered: `api → services → repositories → models`. Routes decide nothing;
services hold the rules; repositories own the SQL. The row lock lives in exactly one place,
[`repositories/reservation.py`](backend/app/repositories/reservation.py), which is the file
to read first.

## Running it

You need Python 3.12, Node 22, and a PostgreSQL connection string. Neon's free tier is what
this was built against.

**Backend**

```bash
cd backend
python -m venv .venv && .venv/Scripts/activate     # source .venv/bin/activate on macOS/Linux
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env                                # then fill in DATABASE_URL and JWT_SECRET
python -m app.cli.seed --admin you@example.com --password 'a-long-enough-password'
python -m uvicorn app.main:app --reload --port 8000
```

The seed applies migrations, imports a catalogue with stock behind it, and makes an
administrator. It is safe to run again: products are matched on their slug and updated in
place, and an account that already exists is promoted rather than having its password reset.

It deliberately creates no sale. What is on offer and when is a decision for whoever runs the
shop, and a seeded sale would be over by the time anyone visited. Sign in and open
`/admin/sales` to put one on.

**Frontend**

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

**Tests**

```bash
cd backend
pytest -m "not crowd"     # fast: everything but the concurrency suite
pytest                    # everything, including twenty threads racing for real stock
```

The concurrency tests commit for real on separate connections, because two threads sharing
one uncommitted transaction are not two shoppers — neither can see what the other wrote, and
the contention the code exists to handle never happens. See
[`backend/tests/README.md`](backend/tests/README.md) for how to check they still bite.

## Deploying

Both halves run as one Vercel project, using
[Services](https://vercel.com/docs/services): the storefront and the API are built
separately from their own directories and served from a single domain. `vercel.json` at the
repository root declares them and routes `/api/*` to the backend, everything else to the
storefront.

Because there is one domain, the API is same-origin. Nothing is cross-site, so the session
cookie stays `SameSite=Lax` and no CORS configuration is needed at all.

Environment variables on the project:

```
DATABASE_URL             Neon's POOLED connection string
MIGRATION_DATABASE_URL   Neon's DIRECT string — a transaction pooler mangles DDL
JWT_SECRET               python -c "import secrets; print(secrets.token_urlsafe(48))"
COOKIE_SECURE            true
ENVIRONMENT              production
NEXT_PUBLIC_API_URL      leave empty, so the browser calls /api/v1 on this same domain
```

Then run the seed once against the deployed database, sign in, and create a sale at
`/admin/sales`.

**One honest caveat.** Serverless runs each concurrent request in its own process, so the
connection pool this project tunes for a rush does not apply there — the app detects Vercel
and holds no pool of its own, leaving the pooling to Neon. Overselling is still impossible,
because the lock and the constraint live in the database. What a serverless deployment cannot
show off is the queue behaviour under a genuine stampede; for that, run it as a normal
long-lived server and point `pytest -m crowd` at it.
