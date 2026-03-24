import click
from secrets import token_urlsafe

from .extensions import db
from .models import StockTransaction, Supply, User
from .services.inventory import add_new_supply, issue_supply, restock_supply


def _upsert_seed_user(*, username, full_name, role, password=None, update_password=False):
    user = User.query.filter_by(username=username).first()
    if not user:
        user = User(username=username)
        db.session.add(user)

    user.full_name = full_name
    user.role = role
    if password and (update_password or not user.password_hash):
        user.set_password(password)
    return user


def _merge_legacy_staff(legacy_user, replacement_user):
    Supply.query.filter_by(created_by=legacy_user.id).update({"created_by": replacement_user.id})
    StockTransaction.query.filter_by(performed_by=legacy_user.id).update(
        {"performed_by": replacement_user.id}
    )
    db.session.delete(legacy_user)


def _seed_users(app):
    configured_admin_password = app.config["SEED_ADMIN_PASSWORD"]
    configured_erla_password = app.config["SEED_ERLA_PASSWORD"]
    configured_april_password = app.config["SEED_APRIL_PASSWORD"]

    admin_existing = User.query.filter_by(username=app.config["SEED_ADMIN_USERNAME"]).first()
    erla_existing = User.query.filter_by(username=app.config["SEED_ERLA_USERNAME"]).first()
    april_existing = User.query.filter_by(username=app.config["SEED_APRIL_USERNAME"]).first()

    admin_password = configured_admin_password or (None if admin_existing else token_urlsafe(12))
    erla_password = configured_erla_password or (None if erla_existing else token_urlsafe(12))
    april_password = configured_april_password or (None if april_existing else token_urlsafe(12))

    admin = _upsert_seed_user(
        username=app.config["SEED_ADMIN_USERNAME"],
        full_name="Jas Desierto",
        role="admin",
        password=admin_password,
        update_password=bool(configured_admin_password or not admin_existing),
    )
    erla = _upsert_seed_user(
        username=app.config["SEED_ERLA_USERNAME"],
        full_name="Erla",
        role="staff",
        password=erla_password,
        update_password=bool(configured_erla_password or not erla_existing),
    )
    april = _upsert_seed_user(
        username=app.config["SEED_APRIL_USERNAME"],
        full_name="April",
        role="staff",
        password=april_password,
        update_password=bool(configured_april_password or not april_existing),
    )

    legacy_staff = User.query.filter_by(username="staff").first()
    if legacy_staff:
        if legacy_staff.id == erla.id:
            legacy_staff.full_name = "Erla"
            legacy_staff.role = "staff"
            legacy_staff.username = app.config["SEED_ERLA_USERNAME"]
            if erla_password and (configured_erla_password or not erla_existing):
                legacy_staff.set_password(erla_password)
            erla = legacy_staff
        else:
            _merge_legacy_staff(legacy_staff, erla)

    db.session.commit()
    return admin, erla, april, {
        "admin": (admin.username, admin_password),
        "erla": (erla.username, erla_password),
        "april": (april.username, april_password),
    }


def _seed_inventory(admin, erla, april):
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
        performed_by=erla,
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
        performed_by=april,
    )


def register_cli(app):
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
        if force:
            StockTransaction.query.delete()
            Supply.query.delete()
            User.query.delete()
            db.session.commit()

        admin, erla, april, credentials = _seed_users(app)
        _seed_inventory(admin, erla, april)

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
