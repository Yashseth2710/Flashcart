# Tests

Everything runs against a real PostgreSQL. The guarantees under test are
database constraints and row locks, and neither survives being stubbed out.

```
pytest                      # everything
pytest -m "not crowd"       # skip the slow concurrency tests
pytest -m crowd             # only those
```

## The two kinds

Most tests use the `db` fixture, which wraps the test in a transaction and rolls
it back at the end. Fast, isolated, and leaves nothing behind.

`test_no_overselling.py` cannot use it. Two threads sharing one uncommitted
transaction are not two shoppers: neither can see what the other wrote, and the
contention that the code exists to handle never happens. Those tests use the
`world` and `sessions` fixtures instead, which commit for real on separate
connections and clean up afterwards by tracking what they made.

That is also why they are slow. Twenty threads doing real round-trips takes
minutes against a remote database, seconds against a local one.

Because they commit, what they write outlives the process. A failing test is
cleaned up by its own fixture, but a run that is killed part-way leaves rows
behind, so the next run sweeps them away before it starts. Both paths match on
the `crowd-` names the fixtures use, and nothing else is ever touched.

## Checking the tests still bite

A concurrency test that passes against broken code is worse than no test. The
way to check is to break the thing on purpose and watch them fail.

Remove `.with_for_update()` from `lock_sale_product` in
`app/repositories/reservation.py`, then:

```
pytest -m crowd
```

Nine of the fourteen should fail, reporting that twenty people all took the same
unit. Restore the line with `git checkout -- app/repositories/reservation.py`
and they should pass again.

Worth knowing: the single-unit case still passes without the lock, because the
`reserved + sold <= allocated` constraint catches it on its own. Only the
multi-unit cases expose the missing lock, which is why that test is
parametrised over several stock levels.

## Rate limits

`test_rate_limits.py` counts against a real table, so the same tests cover the
statement that does the counting and the decision made from it.

Three things there are worth knowing.

Every test takes a caller name from the `subject` fixture rather than sharing
one, and the tests that count by address send an `X-Forwarded-For` of their
own. Without either, two tests share a tally and whichever runs second starts
part-way through what the first spent.

The clock is held still for all of them. A window turns over on the wall clock,
and a test making several requests takes long enough to straddle one: when the
boundary lands mid-test the count starts again underneath it and an attempt
that should have been refused is allowed. That failure moves to a different
test on each run, which is what makes it worth designing out rather than
retrying. Window turnover is still covered — by passing an explicit later
moment, rather than by waiting for a real minute to pass.

To check they still bite, take out the refusal in `check` in
`app/services/rate_limit.py`:

```
pytest tests/test_rate_limits.py
```

Eleven of the thirty should fail. Restore it and they pass again. Note the
counting tests keep passing, which is the point of separating them: counting
correctly and refusing correctly are different claims.
