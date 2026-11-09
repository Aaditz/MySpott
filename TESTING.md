# MySpott: Testing

## How to run all automated tests
From the project folder, with the virtual environment active:

    python -m pytest

Tests run against the separate PostgreSQL database `myspott_test`. They erase and recreate its tables
for every test, so never point TEST_DATABASE_URL at a development or production database.
The app refuses to run tests if the database name does not end with `_test`.

## Results log
| Date | Step | Test | Result |
|------|------|------|--------|
| 2026-11-08 | Phase 1, Step 2 | Manual: home page at http://127.0.0.1:5000/ | Passed |
| 2026-11-09 | Phase 2, Step 2 | Automated: `python -m pytest` (24 tests: config, health, User model) | Passed: 24 passed |
| 2026-11-09 | Phase 2, Step 3 | Migrations: init, migrate, upgrade, downgrade, upgrade; table checked in psql | Passed |

## What the automated tests cover so far
- Configuration: environment names, missing or placeholder secrets, database address rules, no password in error messages
- Health endpoint, home page and 404 handling
- User model: defaults, lowercase emails, duplicate emails (any capitalisation), password hashing,
  invalid role rejected by the database, required name, updated_at changes on edit