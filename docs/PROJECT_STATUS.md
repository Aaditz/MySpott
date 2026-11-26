# MySpott: Project Status

**Last updated:** end of Phase 4 (see `git log` for the date)

## Current phase
Phase 5: Property core (not started)

## Completed
- Phase 0: SRS review, architecture and roadmap agreed
- Phase 1: Foundation (Flask app factory, configuration, health endpoint, tests, docs, Git/GitHub)
- Phase 2: Database foundation (local PostgreSQL, SQLAlchemy, Flask-Migrate, User model, migrations)
- Phase 3: Authentication (sign up, log in/out, email confirmation, password reset, roles, access checks,
  admin tools, rate limiting)
- Phase 4: Web UI foundation
  - Product scope: for anyone looking to rent, not only students; no single campus built in
  - Design system: tokens, typography, spacing, accessible colours, own stylesheet (no Bootstrap)
  - Page frame: header with logo, phone menu, footer, skip link, messages area
  - Account pages redesigned as cards with proper fields, show/hide password, "please wait" buttons
  - Component kit: closable messages, confirmation dialog, empty and loading states, property card
  - Development-only style guide at /dev/style-guide; design guide in docs/DESIGN_GUIDE.md
  - Template rule tests protect future pages (no inline styles/scripts, security tokens, button types, alt text)
  - 223 automated tests passing

## Next
- Phase 5: listings (create, edit, pause, publish), owner dashboard, facilities and house rules basics

## Known limits (tracked in TODO.md)
- The Inter font loads from Google Fonts (needs internet); self-hosting is planned for Phase 12
- Rate-limit counters live in memory; a shared store comes with deployment
- Emails are printed to the Terminal; real SMTP is untested against a real server
- No dark mode