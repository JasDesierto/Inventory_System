import click

from .extensions import db
from .models import StockTransaction, Supply, User
from .services.inventory import add_new_supply, issue_supply, restock_supply


def _upsert_seed_user(*, username, full_name, role, password):
    user = User.query.filter_by(username=username).first()
    if not user:
        user = User(username=username)
        db.session.add(user)

    user.full_name = full_name
    user.role = role
    user.set_password(password)
    return user


def _merge_legacy_staff(legacy_user, replacement_user):
    Supply.query.filter_by(created_by=legacy_user.id).update({"created_by": replacement_user.id})
    StockTransaction.query.filter_by(performed_by=legacy_user.id).update(
        {"performed_by": replacement_user.id}
    )
    db.session.delete(legacy_user)


def _seed_users(app):
    admin = _upsert_seed_user(
        username=app.config["SEED_ADMIN_USERNAME"],
        full_name="Jas Desierto",
        role="admin",
        password=app.config["SEED_ADMIN_PASSWORD"],
    )
    erla = _upsert_seed_user(
        username=app.config["SEED_ERLA_USERNAME"],
        full_name="Erla",
        role="staff",
        password=app.config["SEED_ERLA_PASSWORD"],
    )
    april = _upsert_seed_user(
        username=app.config["SEED_APRIL_USERNAME"],
        full_name="April",
        role="staff",
        password=app.config["SEED_APRIL_PASSWORD"],
    )

    legacy_staff = User.query.filter_by(username="staff").first()
    if legacy_staff:
        if legacy_staff.id == erla.id:
            legacy_staff.full_name = "Erla"
            legacy_staff.role = "staff"
            legacy_staff.username = app.config["SEED_ERLA_USERNAME"]
            legacy_staff.set_password(app.config["SEED_ERLA_PASSWORD"])
            erla = legacy_staff
        else:
            _merge_legacy_staff(legacy_staff, erla)

    db.session.commit()
    return admin, erla, april


def _seed_inventory(admin, erla, april):
    if Supply.query.count() > 0:
        return

    pens = add_new_supply(
        item_name="Pilot G2 Gel Pen",
        description="Retractable 0.7mm black gel pens for general office use.",
        category="Writing",
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
        category="Paper",
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
        category="Printing",
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
        quantity=6,
        photo_path="uploads/seed-paper.svg",
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

        admin, erla, april = _seed_users(app)
        _seed_inventory(admin, erla, april)

        click.echo(
            "Seed complete. Admin login: "
            f"{app.config['SEED_ADMIN_USERNAME']}/{app.config['SEED_ADMIN_PASSWORD']} | "
            f"Erla login: {app.config['SEED_ERLA_USERNAME']}/{app.config['SEED_ERLA_PASSWORD']} | "
            f"April login: {app.config['SEED_APRIL_USERNAME']}/{app.config['SEED_APRIL_PASSWORD']}"
        )
