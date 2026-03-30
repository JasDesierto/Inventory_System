# Office Inventory System

Flask-based office supplies inventory system with login, stock-in and stock-out workflows, transaction history, analytics, image capture/upload, and a responsive Jinja frontend.

## Run

```bash
pip install -r requirements.txt
flask --app run:app init-db
flask --app run:app seed
python run.py
```

Set `SECRET_KEY` before running outside local development.

`flask seed` now prints the generated credentials it creates. To keep predictable seed passwords, set:

- `SEED_ADMIN_PASSWORD`
- `SEED_ERLA_PASSWORD`
- `SEED_APRIL_PASSWORD`

## Production Checklist

Set these environment variables before deployment:

- `APP_ENV=production`
- `SECRET_KEY` to a unique value with at least 32 characters
- `SESSION_COOKIE_SECURE=1`
- `TRUSTED_HOSTS` to a comma-separated allowlist such as `inventory.example.gov,internal.example.gov`

Recommended deployment settings:

- `ALLOW_SELF_SIGNUP=0` to prevent public account creation
- `PROXY_FIX_X_FOR=1` and `PROXY_FIX_X_PROTO=1` when running behind a reverse proxy that sets forwarded headers
- `DATABASE_URL` to your production database connection string

### Supabase

For Supabase-hosted Postgres, use the `Session pooler` connection from the Supabase dashboard on port `5432` unless your deployment target supports IPv6 direct connections. The SQLAlchemy URL for this app should look like:

```bash
DATABASE_URL=postgresql+psycopg2://postgres.<project-ref>:<url-encoded-db-password>@aws-0-<region>.pooler.supabase.com:5432/postgres?sslmode=require
```

Notes:

- The repo now includes `psycopg2-binary` for PostgreSQL connectivity
- URL-encode the database password before placing it in `DATABASE_URL` if it contains special characters such as `@`, `:`, `/`, or `?`
- `flask --app run:app init-db` creates the schema in the target Supabase database
- On hosts without shell access, set `AUTO_SEED_ON_START=1` to seed the initial accounts automatically when the database is empty
- Existing data in `instance/inventory.db` is not migrated automatically

Production behavior now enforces these guardrails:

- The app refuses to start in production with the default or short `SECRET_KEY`
- The app refuses to start in production without secure session cookies
- The app refuses to start in production without `TRUSTED_HOSTS`
- Self-service signup is disabled by default in production unless explicitly re-enabled

Operational notes:

- Use HTTPS end to end
- Keep `instance/uploads` outside any public static file server path
- Run `flask seed` only for initial controlled setup, not as a recurring deployment step
- Back up the database and protected upload directory together

## Deployment Packaging

This repo now includes:

- `wsgi.py` for production WSGI serving
- `.env.example` as the deployment environment template
- `Dockerfile` for container packaging
- `.dockerignore` to keep local state out of image builds
- `RELEASE_CHECKLIST.md` for go-live and rollback steps

### Direct production serve

Install dependencies, load your production environment variables, initialize the database, then serve with Waitress:

```bash
pip install -r requirements.txt
flask --app run:app init-db
flask --app run:app seed
waitress-serve --listen=0.0.0.0:8000 wsgi:app
```

If your deployment uses a reverse proxy, set the `PROXY_FIX_*` variables in `.env.example` to match the forwarded headers you trust.

### Docker

Build the image:

```bash
docker build -t office-inventory .
```

Run the container with a persistent instance volume:

```bash
docker run --env-file .env \
  -p 8000:8000 \
  -v office_inventory_instance:/app/instance \
  office-inventory
```

Initialize the database and seed the first accounts before first traffic:

```bash
docker run --rm --env-file .env \
  -v office_inventory_instance:/app/instance \
  office-inventory flask --app run:app init-db

docker run --rm --env-file .env \
  -v office_inventory_instance:/app/instance \
  office-inventory flask --app run:app seed
```

Container notes:

- The container runs as a non-root user
- Waitress serves the app on `PORT` with a default of `8000`
- Persist `/app/instance` so the SQLite database and protected uploads survive restarts
- `GET /healthz` returns `200` when the app and database session are available
