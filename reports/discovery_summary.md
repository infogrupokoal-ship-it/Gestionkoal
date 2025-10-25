# Project Discovery Summary

This document summarizes the key configuration and entry points for the "Gestión Koal" project.

## Flask Application
- **Flask Module:** `backend:create_app` (Application Factory Pattern)
- **Default Port:** `5000` (for development)
- **Health Check Route:** `/health`

## Webhooks
- **WhatsApp Webhook Path:** `/webhooks/whatsapp`
- **Expected Headers:** `X-Hub-Signature-256` for payload verification. The corresponding secret is expected in the `WHATSAPP_APP_SECRET` environment variable.

## Scripts
- **`00_setup_venv.bat`**: Creates the virtual environment and installs dependencies from `requirements.txt`.
- **`02_run_dev.bat`**: Runs the Flask development server on `http://127.0.0.1:5000`. This is the primary script for local development.
- **`03_run_prod_waitress.bat`**: Runs the application with a production-like server (Waitress) on port `8000`.
- **`04_init_db.bat`**: Runs a custom `flask init-db` command, likely for seeding or initial setup.
- **`99_diagnose.bat`**: Executes a series of checks on the environment (Python, venv, Flask detection) and saves them to `diagnostico_project.log`.
- **`koal.bat` / `iniciokoal.bat`**: Comprehensive launchers that automate the entire local startup sequence, including setup, DB initialization, and running the server.

## Database & Migrations
- **ORM:** `Flask-SQLAlchemy`
- **Migrations:** `Flask-Migrate` is used. The migration scripts are located in the `migrations/` directory.
- **Database Type:** SQLite for local development.
- **Migration Commands:** Standard `flask db` commands (`current`, `heads`, `upgrade`) are expected to work.

## AI / Gemini Integration
- **Primary Module:** The `ai_chat` blueprint seems to contain the core logic.
- **Invocation:** The integration is enabled if the `GEMINI_API_KEY` is present.
- **Required Variables:** `GEMINI_API_KEY`, `GEMINI_MODEL`.

## Required Environment Variables
This is a list of environment variable **names** used throughout the application for configuration.

- **General & Security:**
  - `SECRET_KEY`
  - `APP_VERSION`
- **Database:**
  - `DATABASE_PATH` (for SQLite)
  - `DATABASE_URL` (likely for production, e.g., PostgreSQL on Render)
- **File Storage:**
  - `UPLOAD_FOLDER`
- **AI & Google Services:**
  - `GEMINI_API_KEY` (or `GOOGLE_API_KEY`)
  - `GEMINI_MODEL`
  - `GOOGLE_CSE_ID`
- **WhatsApp Integration (Meta):**
  - `WHATSAPP_ACCESS_TOKEN`
  - `WHATSAPP_PHONE_NUMBER_ID`
  - `WHATSAPP_VERIFY_TOKEN`
  - `WHATSAPP_APP_SECRET`
- **Monitoring:**
  - `SENTRY_DSN`