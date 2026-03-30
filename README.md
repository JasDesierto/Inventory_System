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

- `flask seed` prints generated credentials for accounts that did not already exist
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
- `AUTO_SEED_ON_START`: seeds default users and sample data when the database is empty
- `PROXY_FIX_X_FOR`, `PROXY_FIX_X_PROTO`, `PROXY_FIX_X_HOST`, `PROXY_FIX_X_PORT`, `PROXY_FIX_X_PREFIX`: trusted reverse-proxy header counts
- `SEED_ADMIN_USERNAME`, `SEED_ADMIN_PASSWORD`
- `SEED_ERLA_USERNAME`, `SEED_ERLA_PASSWORD`
- `SEED_APRIL_USERNAME`, `SEED_APRIL_PASSWORD`
- `PORT`: listening port used by Waitress and container deployments

## Default Accounts And Seeding

The app includes CLI support for first-run setup.

Available commands:

- `flask --app run:app init-db`
- `flask --app run:app seed`
- `flask --app run:app users`
- `flask --app run:app set-password <username> <password>`

Seeding behavior:

- Creates or updates the configured admin and staff seed users
- Adds sample supplies only when the inventory table is empty
- Prints generated passwords for newly created accounts when a password was not supplied through environment variables

For predictable credentials, define:

- `SEED_ADMIN_PASSWORD`
- `SEED_ERLA_PASSWORD`
- `SEED_APRIL_PASSWORD`

## Production Deployment

Use `.env.render.example` as the production template, then adjust it for your host.

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

The app will refuse to start in production if:

- `SECRET_KEY` is missing, default, or too short
- `SESSION_COOKIE_SECURE` is not enabled
- `TRUSTED_HOSTS` is not configured

### Waitress Deployment

```bash
pip install -r requirements.txt
flask --app run:app init-db
flask --app run:app seed
waitress-serve --listen=0.0.0.0:8000 wsgi:app
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

Initialize the database and seed the first accounts before opening the service to users:

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
- Database backups
- Backup of `instance/uploads` together with the database
- HTTPS termination and trusted host configuration
- Controlled creation or reset of admin credentials
- Disabling self-signup if public registration is not desired

Recommended operating practice:

- Run `seed` only during controlled setup, not on every deployment
- Keep `AUTO_SEED_ON_START=0` after initial provisioning
- Test the login flow and a sample upload after each deployment
- Review `RELEASE_CHECKLIST.md` before production rollout or rollback
