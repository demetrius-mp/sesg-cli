import typer

from sesg_cli.database.connection import engine
from sesg_cli.database.models.base import Base

app = typer.Typer(rich_markup_mode="markdown", help="Create or drop the database.")


@app.command()
def create():
    """Creates the tables on the database."""
    Base.metadata.create_all(bind=engine)


@app.command()
def drop():
    """Drops the tables from the database."""
    confirmed = typer.confirm(
        "Are you sure you want to drop the database?", default=False
    )

    if not confirmed:
        raise typer.Abort()

    Base.metadata.drop_all(bind=engine)
