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
