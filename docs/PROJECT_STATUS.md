# MySpott: Project Status

**Last updated:** end of Phase 3 (see `git log` for the date)

## Current phase
Phase 4: Web UI foundation (not started)

## Completed
- Phase 0: SRS review, architecture and roadmap agreed
- Phase 1: Foundation (Flask app factory, configuration, health endpoint, tests, docs, Git/GitHub)
- Phase 2: Database foundation (local PostgreSQL, SQLAlchemy, Flask-Migrate, User model, migrations)
- Phase 3: Authentication
  - Sign up (seeker or owner), log in, log out; one generic message for every failed login
  - Email confirmation: link opens a button page, one-time links, "send me a new link" with a wait
  - Password reset: same answer for known and unknown addresses, one-time links, weak passwords keep the link
  - Access checks: owner_required, admin_required, roles_required, verified_required
  - A password change logs out every device; suspended accounts are logged out at once
  - Admin accounts only through the command line (create-admin, promote-admin)
  - Rate limiting on login (per address and per account), sign-up, password reset and resend
  - Friendly 403, 404 and 429 pages; JSON errors under /api/
  - 189 automated tests passing

## Next
- Phase 4: MySpott design system, base layout, navigation, restyled sign-up/login pages

## Known limits (tracked in TODO.md)
- Auth pages are deliberately unstyled until Phase 4
- Rate-limit counters live in memory; a shared store comes with deployment
- Behind a hosting proxy, visitor addresses need to be configured (Phase 12)
- The reset form answers slightly slower for existing accounts (background email sending, Phase 12)
- Emails are printed to the Terminal; the real SMTP mode has only been tested against a stand-in server