from flask.cli import with_appcontext
from app.database.seed.seed_users import seed as seed_users
from app.database.seed.seed_jobs import seed as seed_jobs
from app.database.seed.seed_candidates import seed as seed_candidates
from app.extensions import db

import click

@click.command("seed-all")
@with_appcontext
def seed_all():
    """Run all database seeders."""
    click.echo("🌱 Seeding database...")
    seed_users()
    seed_jobs()
    seed_candidates()
    click.echo("✅ All seeders completed!")
