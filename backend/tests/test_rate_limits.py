"""Asking someone to slow down, without ever letting stock be the thing at risk.

A limit is not what stops overselling. The row lock and the check constraint do
that, and they hold whatever arrives. These tests are about a different problem:
one caller spending a whole sale's capacity on retries nobody made by hand.
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import TooManyAttempts
from app.core.security import create_access_token, hash_password
from app.models import RequestCount, User
from app.repositories.rate_limit import RateLimitRepository, window_containing
from app.services import rate_limit as rate_limit_service
from app.services.rate_limit import RateLimitService
from tests.factories import make_sale_product, make_user, make_variant

PASSWORD = "a-long-enough-password"


@pytest.fixture
def subject() -> str:
    """A caller nobody else is counting.

    Reusing one name across tests would make them share a window, and a window
    turns over on the wall clock: a suite that happened to straddle a minute
    boundary would see a tally reset underneath it and fail for a reason that
    has nothing to do with the code.
    """
    return f"user:{uuid.uuid4().hex[:12]}"


@pytest.fixture
def other() -> str:
    """A second caller, for showing that one person's tally is their own."""
    return f"user:{uuid.uuid4().hex[:12]}"


@pytest.fixture
def from_address() -> dict[str, str]:
    """A caller address nobody else is counting.

    The sign-in limit is keyed on where a request came from, and every test
    client arrives from the same loopback address. Without this they would
    share one tally and each would start part-way through whatever the last
    one spent. The app reads this header to find the caller behind a proxy,
    which is exactly the seam a test needs.
    """
    return {"X-Forwarded-For": f"198.51.100.{uuid.uuid4().int % 250 + 1}"}


@pytest.fixture(autouse=True)
def steady_clock(monkeypatch: pytest.MonkeyPatch) -> datetime:
    """Holds the service's clock still for the length of every test here.

    A window turns over on the wall clock, and a test that makes several
    attempts takes long enough to straddle one: each request is a real round
    trip. When the boundary lands mid-test the tally starts again underneath
    it, and an attempt that should have been refused is allowed — a failure
    that says nothing about the code and moves to a different test each run.

    Autouse because every test in this file counts something, and none of them
    wants the window moving while they do. The turnover itself is covered by
    passing an explicit later moment, rather than by waiting for a real minute.
    """
    moment = datetime(2026, 8, 25, 19, 30, 12, tzinfo=UTC)
    monkeypatch.setattr(rate_limit_service, "now", lambda: moment)
    return moment


def signed_in(client: TestClient, db: Session) -> User:
    user = make_user(db)
    user.password_hash = hash_password(PASSWORD)
    db.flush()
    client.cookies.set(get_settings().cookie_name, create_access_token(str(user.id), "CUSTOMER"))
    return user


# Counting


def test_the_first_attempt_counts_as_one(db: Session, subject: str) -> None:
    counts = RateLimitRepository(db)

    assert counts.count_attempt(subject, "holds", datetime.now(UTC)) == 1


def test_attempts_in_the_same_minute_add_up(db: Session, subject: str) -> None:
    counts = RateLimitRepository(db)
    moment = datetime.now(UTC)

    tally = [counts.count_attempt(subject, "holds", moment) for _ in range(4)]

    assert tally == [1, 2, 3, 4]


def test_a_new_minute_starts_again(db: Session, subject: str) -> None:
    """The window is fixed, not rolling: nothing carries over."""
    counts = RateLimitRepository(db)
    moment = datetime.now(UTC)

    counts.count_attempt(subject, "holds", moment)
    counts.count_attempt(subject, "holds", moment)
    next_minute = counts.count_attempt(subject, "holds", moment + timedelta(minutes=1))

    assert next_minute == 1


def test_two_people_are_counted_apart(db: Session, subject: str, other: str) -> None:
    counts = RateLimitRepository(db)
    moment = datetime.now(UTC)

    counts.count_attempt(subject, "holds", moment)
    counts.count_attempt(subject, "holds", moment)

    assert counts.count_attempt(other, "holds", moment) == 1


def test_two_actions_are_counted_apart(db: Session, subject: str) -> None:
    """Someone at their limit for holds can still sign in."""
    counts = RateLimitRepository(db)
    moment = datetime.now(UTC)

    counts.count_attempt(subject, "holds", moment)
    counts.count_attempt(subject, "holds", moment)

    assert counts.count_attempt(subject, "logins", moment) == 1


def test_reading_the_tally_does_not_add_to_it(db: Session, subject: str) -> None:
    counts = RateLimitRepository(db)
    moment = datetime.now(UTC)
    counts.count_attempt(subject, "holds", moment)

    assert counts.hits_in_window(subject, "holds", moment) == 1
    assert counts.hits_in_window(subject, "holds", moment) == 1


def test_a_caller_never_seen_has_no_tally(db: Session, subject: str) -> None:
    counts = RateLimitRepository(db)

    assert counts.hits_in_window(subject, "holds", datetime.now(UTC)) == 0


@pytest.mark.parametrize(
    "second, expected_window_second",
    [(0, 0), (1, 0), (30, 0), (59, 0)],
)
def test_every_moment_in_a_minute_lands_in_the_same_window(
    second: int, expected_window_second: int
) -> None:
    moment = datetime(2026, 8, 25, 19, 30, second, 123456, tzinfo=UTC)

    window = window_containing(moment)

    assert window.second == expected_window_second
    assert window.microsecond == 0
    assert window.minute == 30


# Deciding


def test_staying_under_the_limit_is_allowed(db: Session, subject: str) -> None:
    limits = RateLimitService(db)

    allowance = limits.check(subject, "holds", limit=3)

    assert allowance.used == 1
    assert allowance.remaining == 2
    assert not allowance.exceeded


def test_the_attempt_that_reaches_the_limit_is_still_allowed(db: Session, subject: str) -> None:
    """A limit of three means three go through, not two."""
    limits = RateLimitService(db)

    for _ in range(2):
        limits.check(subject, "holds", limit=3)
    allowance = limits.check(subject, "holds", limit=3)

    assert allowance.used == 3
    assert allowance.remaining == 0


def test_the_attempt_past_the_limit_is_refused(db: Session, subject: str) -> None:
    limits = RateLimitService(db)
    for _ in range(3):
        limits.check(subject, "holds", limit=3)

    with pytest.raises(TooManyAttempts) as refusal:
        limits.check(subject, "holds", limit=3)

    assert refusal.value.status_code == 429


def test_a_refusal_says_how_long_to_wait(db: Session, subject: str) -> None:
    limits = RateLimitService(db)
    limits.check(subject, "holds", limit=1)

    with pytest.raises(TooManyAttempts) as refusal:
        limits.check(subject, "holds", limit=1)

    wait = refusal.value.headers["Retry-After"]
    assert 1 <= int(wait) <= 60


def test_a_refused_attempt_still_counts(db: Session, subject: str, steady_clock: datetime) -> None:
    """Otherwise failing would be free, and free failure is the whole attack."""
    limits = RateLimitService(db)
    limits.check(subject, "holds", limit=1)

    for _ in range(3):
        with pytest.raises(TooManyAttempts):
            limits.check(subject, "holds", limit=1)

    assert RateLimitRepository(db).hits_in_window(subject, "holds", steady_clock) == 4


# Clearing up


def test_windows_that_are_past_are_swept_away(db: Session, subject: str) -> None:
    counts = RateLimitRepository(db)
    long_ago = datetime.now(UTC) - timedelta(hours=3)
    counts.count_attempt(subject, "holds", long_ago)

    removed = counts.forget_older_than(datetime.now(UTC) - timedelta(hours=1))

    assert removed == 1
    assert counts.hits_in_window(subject, "holds", long_ago) == 0


def test_the_service_sweeps_what_it_is_told_to_keep(db: Session, subject: str) -> None:
    """The retention is an argument rather than a mutated setting, so a sweep
    run by hand cannot change what the running app is counting."""
    counts = RateLimitRepository(db)
    counts.count_attempt(subject, "holds", datetime.now(UTC) - timedelta(hours=3))

    removed = RateLimitService(db).sweep(keep_minutes=60)

    assert removed == 1


def test_the_current_window_survives_a_sweep(db: Session, subject: str) -> None:
    counts = RateLimitRepository(db)
    moment = datetime.now(UTC)
    counts.count_attempt(subject, "holds", moment)

    counts.forget_older_than(datetime.now(UTC) - timedelta(hours=1))

    assert counts.hits_in_window(subject, "holds", moment) == 1


# Through the API


def test_holds_are_refused_once_the_limit_is_passed(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(get_settings(), "holds_per_minute", 2)
    signed_in(client, db)
    sale_product = make_sale_product(db, allocated=50, max_per_user=50)
    db.flush()

    body = {"sale_product_id": str(sale_product.id), "quantity": 1}
    codes = [client.post("/api/v1/holds", json=body).status_code for _ in range(4)]

    assert codes[:2] == [201, 201]
    assert codes[2:] == [429, 429]


def test_a_refused_hold_says_what_to_do(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(get_settings(), "holds_per_minute", 1)
    signed_in(client, db)
    sale_product = make_sale_product(db, allocated=50, max_per_user=50)
    db.flush()

    body = {"sale_product_id": str(sale_product.id), "quantity": 1}
    client.post("/api/v1/holds", json=body)
    refused = client.post("/api/v1/holds", json=body)

    assert refused.status_code == 429
    assert "Retry-After" in refused.headers
    assert "wait" in refused.json()["detail"].lower()


def test_a_refused_hold_takes_no_stock(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The point of the whole thing: being throttled must not cost anyone stock."""
    monkeypatch.setattr(get_settings(), "holds_per_minute", 1)
    signed_in(client, db)
    sale_product = make_sale_product(db, allocated=50, max_per_user=50)
    db.flush()

    body = {"sale_product_id": str(sale_product.id), "quantity": 1}
    client.post("/api/v1/holds", json=body)
    for _ in range(5):
        client.post("/api/v1/holds", json=body)

    db.refresh(sale_product)
    assert sale_product.reserved_quantity == 1


def test_one_persons_limit_does_not_touch_another(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(get_settings(), "holds_per_minute", 1)
    sale_product = make_sale_product(db, allocated=50, max_per_user=50)
    db.flush()
    body = {"sale_product_id": str(sale_product.id), "quantity": 1}

    signed_in(client, db)
    client.post("/api/v1/holds", json=body)
    assert client.post("/api/v1/holds", json=body).status_code == 429

    signed_in(client, db)
    assert client.post("/api/v1/holds", json=body).status_code == 201


def test_reading_holds_is_never_refused(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Only the calls that take something are counted. Looking is free."""
    monkeypatch.setattr(get_settings(), "holds_per_minute", 1)
    signed_in(client, db)

    codes = [client.get("/api/v1/holds").status_code for _ in range(5)]

    assert codes == [200] * 5


def test_signing_in_is_refused_after_too_many_guesses(
    client: TestClient,
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    from_address: dict[str, str],
) -> None:
    monkeypatch.setattr(get_settings(), "logins_per_minute", 3)
    user = make_user(db)
    user.password_hash = hash_password(PASSWORD)
    db.flush()

    guess = {"email": user.email, "password": "not-the-right-password"}
    codes = [
        client.post("/api/v1/auth/login", json=guess, headers=from_address).status_code
        for _ in range(5)
    ]

    assert codes == [401, 401, 401, 429, 429]


def test_guessing_across_accounts_does_not_reset_the_count(
    client: TestClient,
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    from_address: dict[str, str],
) -> None:
    """Counted by where the guesses come from, which is what makes a list of
    stolen emails no cheaper to work through than one."""
    monkeypatch.setattr(get_settings(), "logins_per_minute", 2)
    people = []
    for _ in range(4):
        person = make_user(db)
        person.password_hash = hash_password(PASSWORD)
        people.append(person)
    db.flush()

    codes = [
        client.post(
            "/api/v1/auth/login",
            json={"email": person.email, "password": "wrong"},
            headers=from_address,
        ).status_code
        for person in people
    ]

    assert codes == [401, 401, 429, 429]


def test_the_right_password_still_works_under_the_limit(
    client: TestClient,
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    from_address: dict[str, str],
) -> None:
    monkeypatch.setattr(get_settings(), "logins_per_minute", 5)
    user = make_user(db)
    user.password_hash = hash_password(PASSWORD)
    db.flush()

    client.post(
        "/api/v1/auth/login", json={"email": user.email, "password": "wrong"}, headers=from_address
    )
    response = client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": PASSWORD},
        headers=from_address,
    )

    assert response.status_code == 200


def test_keeping_is_refused_once_the_limit_is_passed(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(get_settings(), "marks_per_minute", 2)
    signed_in(client, db)
    variants = [make_variant(db) for _ in range(4)]
    db.flush()

    codes = [
        client.post("/api/v1/saved", json={"product_id": str(v.product_id)}).status_code
        for v in variants
    ]

    assert codes[:2] == [201, 201]
    assert codes[2:] == [429, 429]


def test_the_tally_is_kept_per_account_not_per_address(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Two shoppers behind one office router must not share an allowance."""
    monkeypatch.setattr(get_settings(), "marks_per_minute", 1)
    variants = [make_variant(db) for _ in range(3)]
    db.flush()

    signed_in(client, db)
    first = client.post("/api/v1/saved", json={"product_id": str(variants[0].product_id)})
    second = client.post("/api/v1/saved", json={"product_id": str(variants[1].product_id)})

    signed_in(client, db)
    third = client.post("/api/v1/saved", json={"product_id": str(variants[2].product_id)})

    assert [first.status_code, second.status_code, third.status_code] == [201, 429, 201]


def test_what_is_counted_is_recorded_under_the_account(client: TestClient, db: Session) -> None:
    user = signed_in(client, db)
    sale_product = make_sale_product(db, allocated=50, max_per_user=50)
    db.flush()

    client.post(
        "/api/v1/holds",
        json={"sale_product_id": str(sale_product.id), "quantity": 1},
    )

    row = db.query(RequestCount).filter_by(subject=f"user:{user.id}", action="holds").one()
    assert row.hits == 1
