# tests/

Python tests live in two roots, and `pytest` from the repository root collects both
(configured in `pyproject.toml`).

| Path | Contents | How to run |
| --- | --- | --- |
| `tests/ml/` | Contract and invariant tests for the ML deliverables: the feature-schema contract, the sample dataset, the dataset CLI, the rule-based fallback, and the Zeek live adapter. Imports `ai.*`. | `pytest tests/ml` |
| `backend/tests/` | Backend unit tests plus HTTP-level tests that drive the real FastAPI app on in-memory SQLite. Imports `app.*`. | `pytest backend/tests` |
| `frontend/` | Type-check standing in for component tests until they exist. | `cd frontend && npm test` |

```bash
./deployment/scripts/run_tests.sh              # both Python suites
./deployment/scripts/run_tests.sh tests/ml     # any pytest argument is forwarded
```

## Conventions

- Backend HTTP tests use the fixtures in `backend/tests/conftest.py`, which build a fresh
  in-memory database per test. PostgreSQL-only behaviour still needs the Alembic
  migrations run against a real database.
- ML tests validate against the committed `docs/api/feature_schema_contract.json`, so a
  contract change must regenerate that file in the same commit.
- Add the test with the change. Every new API route, parser, feature calculator, or screen
  ships with one.

## Known gap

`tests/ml/test_tier5_adversarial_coverage.py` imports cleanly but defines no test
functions, so it currently contributes nothing to the run. It is the ML owner's work in
progress.
