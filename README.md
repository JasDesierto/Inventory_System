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
