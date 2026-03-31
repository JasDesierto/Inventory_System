# Office Inventory System

Office Inventory System is a Flask application for tracking office supplies, stock movement, and basic account administration. It includes login, item registration, issue and restock workflows, printable stock cards, transaction history, analytics, and protected image uploads.

## What The App Does

- Maintains a current inventory catalog with quantity, minimum stock, location, category, and photo
- Records every stock-in and stock-out movement in an auditable transaction table
- Provides dashboard and analytics views for low-stock, stock-out, and usage trends
- Supports user login, profile maintenance, password changes, and admin-only user management
- Stores uploaded item photos in `instance/uploads`, outside the public static path

## Technology Summary

- Backend: Flask, Flask-Login, Flask-SQLAlchemy, SQLAlchemy
- Frontend: Jinja templates, vanilla JavaScript, Chart.js
- Default database: SQLite in the `instance` folder
- Optional production database: PostgreSQL via `psycopg2-binary`
- Production serving: Waitress or any WSGI-compatible host using `wsgi.py`

## Security Features

- Session-backed CSRF protection is enforced for every `POST`, `PUT`, `PATCH`, and `DELETE` request
- Content Security Policy uses a per-request nonce and the app also sends hardening headers such as `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`, and related cross-origin protections
- Production startup fails fast if `SECRET_KEY`, `SESSION_COOKIE_SECURE`, or `TRUSTED_HOSTS` are missing or weak
- Authentication now includes lightweight throttling for repeated failed sign-in attempts and repeated signup attempts
- Session cookies are `HttpOnly`, use `SameSite=Lax`, and are marked `Secure` in production
- Post-login redirects are restricted to same-origin targets
- Uploaded images are validated by extension and file signature before storage
- User-uploaded images are stored under `instance/uploads` and served through an authenticated route instead of a public static path
- Waitress/container deployment runs as a non-root user in the provided Docker image
- Password resets from the CLI use a secure prompt by default or `--password-env`, avoiding command-line password leakage

Documenting these controls does not expose the app by itself. The actual risk comes from publishing secrets, real hostnames, production environment values, or internal-only operational details, which should stay out of version control and public docs.

## Project Layout

- `app/__init__.py`: application factory, security headers, extension wiring, startup bootstrapping
- `app/auth.py`: login, signup, and logout routes
- `app/inventory.py`: dashboard, inventory, profile, issue, restock, history, analytics, and API routes
- `app/services/inventory.py`: stock business rules and shared inventory queries
- `app/models.py`: database models for users, supplies, and stock transactions
- `app/utils/uploads.py`: upload validation, protected file storage, and migration of old public uploads
- `run.py`: local Flask entry point
- `wsgi.py`: production WSGI entry point
- `.env.example`: local-office environment template
- `.env.render.example`: hosted deployment template

## Core Data Flow

1. `create_app()` in `app/__init__.py` loads configuration, initializes extensions, applies security middleware, and registers blueprints.
2. Inventory operations go through the service layer in `app/services/inventory.py`.
3. When a supply is added, restocked, or issued, the app updates the `supplies` table and also creates a `stock_transactions` record.
4. Dashboard, stock cards, history, and analytics read from those transaction records to present current state and historical movement.
5. Uploaded images are validated and stored under `instance/uploads`, then served through an authenticated route.

## Requirements

- Python 3.11+ recommended
- `pip`
- For production with PostgreSQL: a reachable Postgres instance and a valid SQLAlchemy connection string

Install dependencies:

```bash
pip install -r requirements.txt
```

## Local Development Setup

Use `.env.example` as the starting point for a local office or developer install.
It is a development template and should not be reused for production deployment.

This project reads settings directly from process environment variables. It does not load `.env` files automatically in Python code, so for local use you must either:

- Export the variables in your shell before starting the app
- Use your IDE or process manager to inject them
- Use a launcher that reads `.env.example` and sets the environment before running Flask or Waitress

Recommended values in local use:

- `APP_ENV=development`
- `DATABASE_URL=sqlite:///inventory.db`
- `SESSION_COOKIE_SECURE=0`
- `AUTO_SEED_ON_START=1` for first boot only
- `ALLOW_SELF_SIGNUP=1` only if staff should create their own accounts

Initialize and run:

```bash
flask --app run:app init-db
flask --app run:app seed
python run.py
```

Alternative local serve with Waitress:

```bash
waitress-serve --listen=127.0.0.1:8000 wsgi:app
```

Local storage locations:

- Database: `instance/inventory.db`
- Protected uploads: `instance/uploads`

Notes:

- `flask seed` prints the generated admin credential when the bootstrap account did not already exist
- After the first successful startup, set `AUTO_SEED_ON_START=0` unless automatic startup seeding is still required
- Use `127.0.0.1` if the app should only be accessible on one machine
- Use `0.0.0.0` only when the app must be reachable from other devices on the local network

## Environment Variables

Important settings used by this project:

- `APP_ENV`: `development` or `production`
- `SECRET_KEY`: required in all non-trivial environments; production requires at least 32 characters
- `DATABASE_URL`: SQLAlchemy database URL; defaults to local SQLite
- `SESSION_COOKIE_SECURE`: must be `1` in production
- `TRUSTED_HOSTS`: required in production
- `ALLOW_SELF_SIGNUP`: controls whether new staff can register from the login page
- `AUTO_SEED_ON_START`: seeds the bootstrap admin account and sample data when the database is empty
- `PROXY_FIX_X_FOR`, `PROXY_FIX_X_PROTO`, `PROXY_FIX_X_HOST`, `PROXY_FIX_X_PORT`, `PROXY_FIX_X_PREFIX`: trusted reverse-proxy header counts
- `AUTH_RATE_LIMIT_ATTEMPTS`, `AUTH_RATE_LIMIT_WINDOW_SECONDS`: failed sign-in threshold and lockout window
- `SIGNUP_RATE_LIMIT_ATTEMPTS`, `SIGNUP_RATE_LIMIT_WINDOW_SECONDS`: signup-attempt threshold and lockout window
- `SEED_ADMIN_PASSWORD`: optional password for the bootstrap `admin` account
- `PORT`: listening port used by Waitress and container deployments

Examples:

- `TRUSTED_HOSTS=inventory.company.local`
- `TRUSTED_HOSTS=inventory.company.local,inventory`
- `DATABASE_URL=sqlite:///inventory.db`
- `DATABASE_URL=postgresql+psycopg2://user:password@db-host:5432/inventory`
- `AUTH_RATE_LIMIT_ATTEMPTS=5`
- `SIGNUP_RATE_LIMIT_ATTEMPTS=5`

## Default Accounts And Seeding

The app includes CLI support for first-run setup.

Available commands:

- `flask --app run:app init-db`
- `flask --app run:app seed`
- `flask --app run:app users`
- `flask --app run:app set-password <username>`
- `flask --app run:app set-password <username> --password-env ADMIN_PASSWORD`

Seeding behavior:

- Creates or updates the bootstrap `admin` account
- Adds sample supplies only when the inventory table is empty
- Prints the generated admin password when one was not supplied through environment variables

Password reset behavior:

- `set-password` now prompts securely by default instead of accepting the password as a positional command-line argument
- On automated hosts, use `--password-env <ENVVAR>` so the password comes from environment injection rather than shell history

For predictable bootstrap credentials, define:

- `SEED_ADMIN_PASSWORD`

## Production Deployment

Use `.env.render.example` as the production template, then adjust it for your host.

In a normal office deployment, IT owns the server, DNS, TLS certificate, firewall rules, service registration, and environment variables. The application only needs the final hostname(s) reflected in `TRUSTED_HOSTS`.

Minimum production requirements:

- `APP_ENV=production`
- `SECRET_KEY` set to a unique 32+ character value
- `SESSION_COOKIE_SECURE=1`
- `TRUSTED_HOSTS` set to the exact allowed hostnames
- HTTPS enabled at the edge or reverse proxy

Recommended production settings:

- `ALLOW_SELF_SIGNUP=0`
- `AUTO_SEED_ON_START=0` after initial provisioning
- `PROXY_FIX_X_FOR=1` and `PROXY_FIX_X_PROTO=1` when running behind a reverse proxy that sets forwarded headers correctly
- `AUTH_RATE_LIMIT_ATTEMPTS=5`
- `AUTH_RATE_LIMIT_WINDOW_SECONDS=900`
- `SIGNUP_RATE_LIMIT_ATTEMPTS=5`
- `SIGNUP_RATE_LIMIT_WINDOW_SECONDS=3600`

Typical internal example:

```env
APP_ENV=production
SECRET_KEY=replace-with-a-32-plus-character-random-secret
DATABASE_URL=sqlite:///inventory.db
SESSION_COOKIE_SECURE=1
TRUSTED_HOSTS=inventory.company.local
ALLOW_SELF_SIGNUP=0
AUTO_SEED_ON_START=0
PROXY_FIX_X_FOR=1
PROXY_FIX_X_PROTO=1
AUTH_RATE_LIMIT_ATTEMPTS=5
AUTH_RATE_LIMIT_WINDOW_SECONDS=900
SIGNUP_RATE_LIMIT_ATTEMPTS=5
SIGNUP_RATE_LIMIT_WINDOW_SECONDS=3600
SEED_ADMIN_PASSWORD=replace-with-a-strong-admin-password
PORT=8000
```

The app will refuse to start in production if:

- `SECRET_KEY` is missing, default, or too short
- `SESSION_COOKIE_SECURE` is not enabled
- `TRUSTED_HOSTS` is not configured

### Waitress Deployment

If the app is behind IIS, nginx, Apache, or another reverse proxy on the same server, prefer binding Waitress to `127.0.0.1`. Use `0.0.0.0` only when the app must be reached directly from the LAN.

```bash
pip install -r requirements.txt
flask --app run:app init-db
flask --app run:app seed
waitress-serve --listen=127.0.0.1:8000 wsgi:app
```

First-run note:

- Run `seed` during controlled provisioning only
- After the first successful login, keep `AUTO_SEED_ON_START=0`
- If IT wants predictable bootstrap credentials, set `SEED_ADMIN_PASSWORD` before running `seed`

### Windows / Office IT Pattern

Typical handoff to internal IT looks like this:

1. Pull the repository onto the target server.
2. Create a virtual environment and install `requirements.txt`.
3. Set system or service-level environment variables from `.env.render.example`.
4. Set `TRUSTED_HOSTS` to the office hostname IT created, such as `inventory.company.local`.
5. Run `flask --app run:app init-db`.
6. Run `flask --app run:app seed`.
7. Run Waitress as a Windows service or scheduled startup task using `wsgi:app`.
8. Configure IIS or another reverse proxy to terminate HTTPS and forward traffic to `127.0.0.1:8000`.

PowerShell example for an ad hoc manual start:

```powershell
$env:APP_ENV="production"
$env:SECRET_KEY="replace-with-a-32-plus-character-random-secret"
$env:DATABASE_URL="sqlite:///inventory.db"
$env:SESSION_COOKIE_SECURE="1"
$env:TRUSTED_HOSTS="inventory.company.local"
$env:ALLOW_SELF_SIGNUP="0"
$env:AUTO_SEED_ON_START="0"
$env:PROXY_FIX_X_FOR="1"
$env:PROXY_FIX_X_PROTO="1"
$env:AUTH_RATE_LIMIT_ATTEMPTS="5"
$env:AUTH_RATE_LIMIT_WINDOW_SECONDS="900"
$env:SIGNUP_RATE_LIMIT_ATTEMPTS="5"
$env:SIGNUP_RATE_LIMIT_WINDOW_SECONDS="3600"
$env:SEED_ADMIN_PASSWORD="replace-with-a-strong-admin-password"
waitress-serve --listen=127.0.0.1:8000 wsgi:app
```

### PostgreSQL / Supabase Example

Example SQLAlchemy URL:

```bash
DATABASE_URL=postgresql+psycopg2://postgres.<project-ref>:<url-encoded-password>@aws-0-<region>.pooler.supabase.com:5432/postgres?sslmode=require
```

Notes:

- Use the Supabase session pooler unless your host explicitly supports the direct connection path you need
- URL-encode database passwords that contain reserved characters
- `init-db` creates the schema in the target database
- Existing SQLite data is not migrated automatically

## Docker

Build:

```bash
docker build -t office-inventory .
```

Run:

```bash
docker run --env-file .env -p 8000:8000 -v office_inventory_instance:/app/instance office-inventory
```

Initialize the database and seed the bootstrap admin account before opening the service to users:

```bash
docker run --rm --env-file .env -v office_inventory_instance:/app/instance office-inventory flask --app run:app init-db
docker run --rm --env-file .env -v office_inventory_instance:/app/instance office-inventory flask --app run:app seed
```

Container notes:

- Persist `/app/instance`
- `GET /healthz` returns `200` when the app and database session are healthy
- The container serves through Waitress using `wsgi.py`

## IT Handover Notes

For a stable office deployment, IT should own the following:

- Environment file and secret management
- Injection of environment variables into the Windows service, IIS app pool, container, or host
- Database backups
- Backup of `instance/uploads` together with the database
- DNS record creation for the chosen office hostname
- HTTPS termination and trusted host configuration
- Controlled creation or reset of admin credentials
- Disabling self-signup if public registration is not desired

Recommended operating practice:

- Run `seed` only during controlled setup, not on every deployment
- Keep `AUTO_SEED_ON_START=0` after initial provisioning
- Keep Waitress bound to `127.0.0.1` when a reverse proxy is in front of it
- Remove any accidentally tracked local databases from source control before release
- Test the login flow and a sample upload after each deployment
- Review `RELEASE_CHECKLIST.md` before production rollout or rollback
