import click

from .extensions import db
from .models import StockTransaction, Supply, User
from .services.inventory import add_new_supply, issue_supply, restock_supply


def _seed_users(app):
    admin = User.query.filter_by(username=app.config["SEED_ADMIN_USERNAME"]).first()
    staff = User.query.filter_by(username=app.config["SEED_STAFF_USERNAME"]).first()

    if not admin:
        admin = User(
            username=app.config["SEED_ADMIN_USERNAME"],
            full_name="Jas Desierto",
            role="admin",
        )
        admin.set_password(app.config["SEED_ADMIN_PASSWORD"])
        db.session.add(admin)
    else:
        admin.full_name = "Jas Desierto"

    if not staff:
        staff = User(
            username=app.config["SEED_STAFF_USERNAME"],
            full_name="staff",
            role="staff",
        )
        staff.set_password(app.config["SEED_STAFF_PASSWORD"])
        db.session.add(staff)
    else:
        staff.full_name = "staff"

    db.session.commit()
    return admin, staff


def _seed_inventory(admin, staff):
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
        performed_by=staff,
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
        performed_by=admin,
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

        admin, staff = _seed_users(app)
        _seed_inventory(admin, staff)

        click.echo(
            "Seed complete. Admin login: "
            f"{app.config['SEED_ADMIN_USERNAME']}/{app.config['SEED_ADMIN_PASSWORD']} | "
            f"Staff login: {app.config['SEED_STAFF_USERNAME']}/{app.config['SEED_STAFF_PASSWORD']}"
        )
