
## Phase 3: Authentication
- Added Flask-Login (login cookies hold "user id:password fingerprint", so a password change or a
  suspension ends existing logins), Flask-WTF (CSRF protection on every form) and Flask-Limiter.
- Added the EmailToken table and the account service (register, authenticate, tokens, reset, create admin).
  Tokens are random, only a hash is stored, links are one-time and expire (24 hours / 1 hour).
- Added email sending with three modes: console (development), smtp (production), memory (tests).
  Emailed links are built from APP_BASE_URL, never from the incoming request.
- Added the pages: sign up, log in, log out, confirm email, resend, forgot password, reset password.
  Links only SHOW a confirm button; pressing it does the change, so email scanners cannot use up a link.
- Added access checks, friendly error pages, the create-admin / promote-admin commands and rate limits.
- Issues met and fixed:
  - a template was saved in the wrong folder (TemplateNotFound);
  - test requests shared Flask's per-request scratchpad (`g`), reusing a stale CSRF token and a stale
    login; fixed with a reset before each test request;
  - tests opened more and more database connections until PostgreSQL refused new ones; fixed by closing
    them after each test;
  - the sign-up rate-limit test needed the same reset for every browser it creates.
- End of phase: 189 tests passing, including one test that walks through the whole account journey.

## Phase 4: Web UI foundation
- Decided MySpott is for anyone looking to rent, not only students, and not tied to one college.
- Agreed the look (teal and amber, Inter, map-pin logo) and built our own small stylesheet with
  variables instead of Bootstrap, so the mobile apps can reuse the same values.
- Built the page frame (header, phone menu, skip link, footer), restyled the home page and error pages.
- Redesigned the account pages: cards, labelled fields with linked errors, show/hide password,
  "please wait" buttons that ignore double clicks and recover when the Back button is used.
- Built the component kit: closable messages, a confirmation dialog, empty and loading states, the
  property card, and a development-only style guide page.
- Added tests: colour approvals and contrast, page frame, account page structure, component kit, and
  rules checked across every template.
- Issues met and fixed: a test helper created the same test user twice; one test run hung because an
  earlier run had left a database connection open (clearing connections to the test database fixed it).
- End of phase: 223 tests passing.