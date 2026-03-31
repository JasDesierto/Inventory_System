# Release Checklist

## Preflight

- Confirm `APP_ENV=production`
- Confirm `SECRET_KEY` is unique and at least 32 characters
- Confirm `SESSION_COOKIE_SECURE=1`
- Confirm `TRUSTED_HOSTS` contains the exact production hostnames
- Confirm `ALLOW_SELF_SIGNUP=0` unless public signup is explicitly required
- Confirm HTTPS is terminated correctly at the edge or proxy
- Confirm `DATABASE_URL` points to the intended production database
- Confirm Supabase connections use the `Session pooler` on port `5432` or an approved direct IPv6 connection
- Confirm `sslmode=require` is present in `DATABASE_URL`
- Confirm persistent storage is mounted for `/app/instance`
- Confirm backups exist for the database and protected uploads

## First Deploy

1. Install dependencies or build the container image.
2. Apply the production environment variables from `.env.render.example`, not `.env.example`.
3. Initialize the database with `flask --app run:app init-db`.
4. Seed the initial accounts with `flask --app run:app seed`.
5. Start the application with Waitress or the container runtime.
6. Verify `GET /healthz` returns `200`.

## Smoke Test

- Open the login page over HTTPS
- Sign in with the admin account
- Verify dashboard loads
- Verify add, restock, issue, history, analytics, and profile pages load
- Upload a profile image and a supply image
- Verify logout works and the session cookie is marked secure
- Verify a staff account cannot access admin-only pages

## Security Validation

- Confirm self-signup is hidden on the login page when disabled
- Confirm the app refuses to start if `SECRET_KEY` is missing or weak in production
- Confirm the app refuses to start if `TRUSTED_HOSTS` is unset in production
- Confirm the app sends HSTS when deployed behind HTTPS
- Confirm protected uploads are not served from a public static path
- Confirm repeated failed logins are throttled
- Confirm signup throttling works when self-signup is enabled
- Confirm password resets are performed through secure prompt or environment injection, not positional CLI arguments

## Rollback

- Keep the previous application image or package available
- Restore the previous environment configuration if changed
- Restore the latest verified backup if the database or upload state becomes inconsistent
- Re-run the smoke test after rollback
