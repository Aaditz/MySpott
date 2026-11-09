# MySpott: Development Log

## 2026-11-08
- Reviewed the combined SRS and playbook; agreed stack: Flask, PostgreSQL, Jinja2/Bootstrap, Expo.
- Launch campus: Kristu Jayanti College.
- Created Flask app factory (`app/__init__.py`), configuration with startup validation (`app/config.py`),
  health endpoint (`/api/v1/health`), placeholder home page, `run.py`.
- Issue: first run failed with "SECRET_KEY is missing" because the `.env` file did not exist.
  Fixed by creating `.env` with a generated key. The startup check worked as designed.
- Added pytest tests for the health endpoint, home page and configuration rules.
- Added project documentation files.
- 
## 2026-11-09
- Installed PostgreSQL locally; created user myspott_user and databases myspott_dev and myspott_test.
- Added database settings with startup validation: DATABASE_URL and TEST_DATABASE_URL are required,
  must be PostgreSQL, and the test database name must end with `_test` so tests can never touch dev data.
- Added `app/extensions.py` (SQLAlchemy, Migrate, constraint naming convention) and the `User` model
  (hashed passwords, lowercase emails, role and status checks, timestamps).
- Added tests for configuration and the User model; all 24 tests passed.
- Issue: tests failed with "TEST_DATABASE_URL is missing" because PowerShell commands had been pasted
  into `.env` instead of settings. Fixed by rewriting `.env` as four plain NAME=value lines.
- Created the first migration ("Create users table"), applied it to myspott_dev, and tested downgrade/upgrade.