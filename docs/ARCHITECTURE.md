
## Authentication (added in Phase 3)
- Web login uses Flask-Login sessions. The login cookie holds "user id:password fingerprint"; the user
  loader rejects it if the account is gone, suspended, or the password changed since the login.
- Every form is protected by CSRF tokens (Flask-WTF). Logout is a POST.
- Roles: seeker, owner, admin. Sign-up can create seekers and owners only. Admins are created or promoted
  from the command line (`flask --app run create-admin` / `promote-admin`).
- Access checks live in `app/web/permissions.py`: owner_required, admin_required, roles_required,
  verified_required. They are strict: an admin is not automatically an owner.
- Email: `app/services/email_service.py` with console / smtp / memory modes. Links use APP_BASE_URL.
- One-time tokens (`email_tokens` table): random, stored hashed, single use, only the newest link works.
- Rate limits are declared in one place, `app/web/rate_limits.py`, and applied with Flask-Limiter.
- Errors: friendly HTML pages for 400 (CSRF), 403, 404 and 429; JSON for anything under /api/.
- Mobile apps (Phase 13) will add token login to the same account service; CSRF protection will be
  switched off for those token-authenticated JSON endpoints only.

## Current structure (end of Phase 3)
    app/
      __init__.py, config.py, extensions.py, cli.py
      models/        user.py, email_token.py
      services/      validation.py, auth_service.py, email_service.py
      web/           routes.py, auth.py, permissions.py, rate_limits.py
      api/v1/        health.py
      templates/     base.html, home.html, error.html, auth/...
    tests/           conftest.py, helpers.py and one test file per area
    migrations/      database migrations (committed to Git)
    docs/            status, log, to-do, architecture, testing