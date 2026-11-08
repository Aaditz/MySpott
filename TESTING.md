# MySpott: Testing

## How to run all automated tests
From the project folder, with the virtual environment active:

    python -m pytest

## Results log
| Date | Step | Test | Result |
|------|------|------|--------|
| 2026-11-08 | Phase 1, Step 2 | Manual: home page at http://127.0.0.1:5000/ | Passed: shows "MySpott is running." |
| 2026-11-08 | Phase 1, Step 3 | Automated: `python -m pytest` (11 tests) | Pending: developer to run and confirm |

## Manual checks (Phase 1)
- Home page shows "MySpott is running."
- /api/v1/health returns status ok
- Removing SECRET_KEY from .env stops the app with a clear error