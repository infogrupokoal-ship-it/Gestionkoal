# Repository Guidelines

## Project Structure & Module Organization
`backend/` hosts the Flask app factory, blueprints, and DB models; `templates/` and `static/` serve the UI; `scripts/` includes automation helpers such as `run_local.ps1`; `migrations/` stores Alembic history; `tests/` holds all pytest suites; `docs/` captures architectural notes, and `schema.sql` plus `instance/` support local SQLite bootstrap. Keep uploads in `uploads/` and long‑lived data (e.g., Render disks) under paths configured via env vars.

## Build, Test & Development Commands
- `.\scripts\run_local.ps1` — one-step setup: creates `.venv`, installs `requirements.txt`, runs migrations/seeds, and starts the dev server on `http://127.0.0.1:5000`.
- `python -m venv .venv && .\.venv\Scripts\activate` — manual virtualenv bootstrap (macOS/Linux: `source .venv/bin/activate`).
- `pip install -r requirements.txt` — sync Python deps (rerun after touching `requirements.lock`).
- `flask db upgrade && flask seed` — align schema with Alembic and load starter data before exercising WhatsApp flows.
- `python -m flask run --debug` — serve the app with live reload; health check lives at `/health`.
- `pytest -q` — run the suite (adds repo root to `PYTHONPATH` via `pyproject.toml`).

## Coding Style & Naming Conventions
Format Python with `black` (line length 88, py311 target) and lint with `ruff` (rules E,F,W,I,UP,B; `E501` ignored because Black governs wrapping). Use snake_case for modules/functions, PascalCase for classes, and descriptive blueprint names (e.g., `whatsapp.routes`). Keep template blocks aligned with Jinja defaults and place static assets under `static/<feature>/`. Prefer dependency-injected helpers over globals; secrets live in `.env.local`, never hardcoded.

## Testing Guidelines
Pytest fixtures (`tests/conftest.py`) spin up an in-memory SQLite schema using `schema.sql`; stay compatible by keeping migrations synchronized with that file. Name test files `test_<feature>.py`, mirror blueprint routes, and assert HTTP status plus security headers (CSRF, HSTS) for critical endpoints such as `/whatsapp/webhook`. When adding features, extend fixtures or seed data through SQL scripts rather than ORM calls to keep tests deterministic. Aim to keep WhatsApp, auth, and dashboard coverage intact; add regression cases for rate limiting or CSP whenever touching middleware.

## Commit & Pull Request Guidelines
Follow the log style: concise imperative summaries (`WhatsApp logs: pagination + CSV export`) or scoped prefixes (`test(whatsapp): ...`). Reference issue IDs when applicable, and batch related schema + code changes together. PRs should describe intent, setup steps, and screenshots/GIFs for UI deltas; list env vars touched (`WHATSAPP_DRY_RUN=1`, `ENABLE_CSP=1`). Always mention test evidence (`pytest -q`, manual webhook replay) and note any follow-up tasks.

## Security & Config Tips
Copy `.env.example` to `.env.local`, then set secrets such as `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_APP_SECRET`, and `GEMINI_API_KEY`; never commit the resulting file. For prod-like runs, toggle `WHATSAPP_DRY_RUN=0`, `ENABLE_HSTS=1`, and `ENABLE_CSP=1`. Keep API signatures verified via `X-Hub-Signature-256`, and ensure new endpoints respect CSRF expectations (HTML forms auto-inject tokens; JSON clients must send `X-CSRF-Token`). When persisting files, route them through `UPLOAD_FOLDER` and avoid storing sensitive exports inside the repo.
