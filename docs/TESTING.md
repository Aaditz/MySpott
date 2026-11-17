# MySpott: Testing

## How to run all automated tests
From the project folder, with the virtual environment active:

    python -m pytest

Tests run against the separate PostgreSQL database `myspott_test`. They erase and recreate its tables
for every test, so never point TEST_DATABASE_URL at a development or production database.
The app refuses to run tests if the database name does not end with `_test`.
The full run takes a little over a minute, because the rate-limit tests make many real attempts.

## Results log
| Phase | Test | Result |
|-------|------|--------|
| 1 | Manual: home page and /api/v1/health | Passed |
| 2 | Automated: config, health, User model (24 tests); migrations up, down, up | Passed |
| 3 | Automated: login support, email tokens, account service, validation, email sending, pages, access control, admin tools, rate limits, full account journey (189 tests in total) | Passed |
| 3 | Manual: sign up, confirm email, log out, wrong password, forgot/reset password, other device logged out after reset, friendly 404 | Passed |

## What the automated tests cover
- Configuration: environments, secrets, database, email, site address and rate-limit settings
- Database models: User and EmailToken constraints, hashed passwords, lowercase emails
- Account service: registration rules, login checks, one-time tokens, resend waiting time, password reset
- Pages: sign up, log in, log out, confirmation, resend, forgot and reset password, CSRF refusals,
  safe redirects, generic messages that reveal nothing about who has an account
- Access control: owner/admin/confirmed-only pages, 403 and 404 pages (HTML and JSON)
- Sessions: password change and suspension end existing logins
- Command line: create-admin and promote-admin
- Rate limits: login, sign-up, reset, resend, and the 429 page
- One test walking through the whole account journey

## Not covered yet
- Real email delivery over SMTP (only tested against a stand-in server)
- Behaviour behind a hosting proxy and with a shared rate-limit store (deployment, Phase 12)
- Visual layout (Phase 4 onwards)