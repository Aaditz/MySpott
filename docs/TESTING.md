# MySpott: Testing

## How to run all automated tests
From the project folder, with the virtual environment active:

    python -m pytest

Tests run against the separate PostgreSQL database `myspott_test`. They erase and recreate its tables
for every test, so never point TEST_DATABASE_URL at a development or production database.
The app refuses to run tests if the database name does not end with `_test`.
The full run takes a little over a minute, because the rate-limit tests make many real attempts.

If a run seems stuck: stop it (Ctrl + C), then close leftover connections to the test database:

    SELECT pg_terminate_backend(pid) FROM pg_stat_activity
    WHERE datname = 'myspott_test' AND pid <> pg_backend_pid();

## Results log
| Phase | Test | Result |
|-------|------|--------|
| 1 | Manual: home page and /api/v1/health | Passed |
| 2 | Automated: config, health, User model; migrations up, down, up | Passed |
| 3 | Automated: account service, pages, access control, admin tools, rate limits, account journey; manual walkthrough | Passed |
| 4 | Automated: design tokens, page frame, account page design, component kit, template rules (223 tests in total) | Passed |
| 4 | Manual: visual check at desktop, tablet and phone width, keyboard, zoom | Pending: change to "Passed" once done |

## What the automated tests cover
- Configuration, database models, account service, pages, access control, sessions, command line, rate limits
- Design system: approved colours, readable text on every background, every variable defined
- Page frame: header, menu, skip link, footer, design files served
- Account pages: labelled fields, errors linked to fields, show/hide password, double-click protection,
  role choice, no inline styles or scripts
- Component kit: dialog on every page, closable messages, style guide, safe macros, development-only rule
- Template rules across every template: no inline styles or scripts, security token in every POST form,
  every button typed, every image with alt text
- One test walking through the whole account journey

## Not covered yet
- Real email delivery over SMTP (only tested against a stand-in server)
- Behaviour behind a hosting proxy and with a shared rate-limit store (deployment, Phase 12)
- The look itself: it is checked by eye, using the style guide page