import click
from secrets import token_urlsafe

from .extensions import db
from .models import StockTransaction, Supply, User
from .services.inventory import add_new_supply, issue_supply, restock_supply

DEFAULT_ADMIN_USERNAME = "admin"


def _upsert_seed_user(*, username, full_name, role, password=None, update_password=False):
    # Seed users are created idempotently so repeated `flask seed` runs update
    # the known accounts instead of duplicating them.
    user = User.query.filter_by(username=username).first()
    if not user:
        user = User(username=username)
        db.session.add(user)

    user.full_name = full_name
    user.role = role
    if password and (update_password or not user.password_hash):
        user.set_password(password)
    return user


def _seed_users(app):
    # Bootstrap seeding creates a single neutral admin account. Operators can
    # add real user accounts through the app after first login.
    configured_admin_password = app.config["SEED_ADMIN_PASSWORD"]
    admin_existing = User.query.filter_by(username=DEFAULT_ADMIN_USERNAME).first()
    admin_password = configured_admin_password or (None if admin_existing else token_urlsafe(12))

    admin = _upsert_seed_user(
        username=DEFAULT_ADMIN_USERNAME,
        full_name="Administrator",
        role="admin",
        password=admin_password,
        update_password=bool(configured_admin_password or not admin_existing),
    )

    db.session.commit()
    return admin, {
        "admin": (admin.username, admin_password),
    }


def _seed_inventory(admin):
    # Inventory seed data provides a realistic first-run catalog plus a small
    # transaction history for dashboard and analytics views.
    if Supply.query.count() > 0:
        return

    pens = add_new_supply(
        item_name="Pilot G2 Gel Pen",
        description="Retractable 0.7mm black gel pens for general office use.",
        category="Writing Instruments",
        unit="boxes",
        quantity=24,
        minimum_quantity=8,
        location="Cabinet A1",
        photo_path="uploads/seed-writing.svg",
        remarks="Initial seed stock",
        created_by=admin,
    )
    paper = add_new_supply(
        item_name="A4 Copy Paper",
        description="80gsm multipurpose copy paper for printers and copiers.",
        category="Paper Products",
        unit="reams",
        quantity=18,
        minimum_quantity=6,
        location="Storage Room",
        photo_path="uploads/seed-paper.svg",
        remarks="Initial seed stock",
        created_by=admin,
    )
    toner = add_new_supply(
        item_name="HP 17A Toner",
        description="Black toner cartridge for finance and admin department printers.",
        category="Printing Supplies",
        unit="cartridges",
        quantity=4,
        minimum_quantity=3,
        location="Printer Bay",
        photo_path="uploads/seed-toner.svg",
        remarks="Initial seed stock",
        created_by=admin,
    )

    issue_supply(
        supply_id=pens.id,
        quantity=5,
        remarks="Issued to onboarding kits",
        performed_by=admin,
    )
    restock_supply(
        supply_id=paper.id,
        category=paper.category,
        quantity=6,
        remarks="Monthly procurement",
        performed_by=admin,
    )
    issue_supply(
        supply_id=toner.id,
        quantity=2,
        remarks="Distributed to accounting team",
        performed_by=admin,
    )


def seed_database(app, force=False):
    # `force=True` is intended for controlled resets during setup or testing.
    if force:
        StockTransaction.query.delete()
        Supply.query.delete()
        User.query.delete()
        db.session.commit()

    admin, credentials = _seed_users(app)
    _seed_inventory(admin)
    return credentials


def register_cli(app):
    # Flask CLI commands mirror the operational tasks IT staff will need during
    # installation and password recovery.
    @app.cli.command("init-db")
    @click.option("--drop", is_flag=True, help="Drop all tables before recreating them.")
    def init_db(drop):
        if drop:
            db.drop_all()
        db.create_all()
        click.echo("Database initialized.")

    @app.cli.command("seed")
    @click.option("--force", is_flag=True, help="Clear existing records before seeding.")
    def seed(force):
        credentials = seed_database(app, force=force)

        credential_parts = []
        generated_accounts = []
        unchanged_accounts = []
        for label, (username, password) in credentials.items():
            if password:
                credential_parts.append(f"{label.title()} login: {username}/{password}")
                if not app.config[f"SEED_{label.upper()}_PASSWORD"]:
                    generated_accounts.append(label.title())
            else:
                credential_parts.append(f"{label.title()} login: {username}/(unchanged)")
                unchanged_accounts.append(label.title())

        guidance_parts = []
        if generated_accounts:
            guidance_parts.append(
                "Generated passwords were used for: " + ", ".join(generated_accounts) + "."
            )
        if unchanged_accounts:
            guidance_parts.append(
                "Existing passwords were kept for: " + ", ".join(unchanged_accounts) + "."
            )
        click.echo(
            "Seed complete. "
            + " | ".join(credential_parts)
            + (" " + " ".join(guidance_parts) if guidance_parts else "")
        )

    @app.cli.command("users")
    def users():
        records = User.query.order_by(User.role.desc(), User.username.asc()).all()
        if not records:
            click.echo("No users found.")
            return

        for user in records:
            click.echo(
                f"{user.id}\t{user.username}\t{user.full_name}\t{user.role}\t{user.created_at.strftime('%Y-%m-%d %H:%M')}"
            )

    @app.cli.command("set-password")
    @click.argument("username")
    @click.argument("password")
    def set_password(username, password):
        user = User.query.filter_by(username=username).first()
        if not user:
            raise click.ClickException(f"User '{username}' was not found.")

        user.set_password(password)
        db.session.commit()
        click.echo(f"Password updated for {user.username}.")
