from pathlib import Path

import typer
from rich.progress import BarColumn, Progress, TaskProgressColumn, TextColumn
from sqlalchemy import or_, select
from sqlalchemy.orm import joinedload

from sesg_cli.config import Config
from sesg_cli.database.connection import Session
from sesg_cli.database.models import SearchString, SearchStringPerformance


app = typer.Typer(rich_markup_mode="markdown", help="Create or drop the database.")


@app.command()
async def fix(
    config_file_path: Path = typer.Option(
        Path.cwd() / "config.toml",
        "--config-file-path",
        "-c",
        help="Path to the `config.toml` file.",
    ),
):
    """Fixes invalid strings in the database."""
    from sesg.scopus import InvalidStringError, ScopusClient

    config = Config.from_toml(config_file_path)

    with Session() as session:
        stmt = (
            select(SearchString)
            .options(joinedload(SearchString.performance))
            .where(
                or_(
                    SearchStringPerformance.start_set_precision == 0,
                    SearchStringPerformance.n_scopus_results == 0,
                )
            )
        )

        search_strings = session.execute(stmt).scalars().all()

        client = ScopusClient(config.scopus_api_keys)

        with Progress(
            TextColumn(
                "[progress.description]{task.description}: {task.completed} of {task.total}"  # noqa: E501
            ),
            BarColumn(),
            TaskProgressColumn(),
        ) as progress:
            overall_task = progress.add_task(
                "Overall",
                total=len(search_strings),
            )

            for search_string in search_strings:
                try:
                    async for _ in client.search(search_string.string):
                        pass

                except InvalidStringError:
                    print("The following string raised an InvalidStringError")
                    print(search_string.string)

                    if search_string.performance:
                        search_string.performance.n_scopus_results = -1
                        session.add(search_string.performance)
                        session.commit()

                finally:
                    progress.advance(overall_task)
