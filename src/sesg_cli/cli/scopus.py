from functools import partial, wraps
from pathlib import Path

import trio
import typer
from rich import print
from rich.progress import BarColumn, Progress, TaskProgressColumn, TextColumn
from sesg.scopus import ScopusClient, SuccessResponse
from sesg.scopus.client import InvalidStringError

from sesg_cli.config import Config
from sesg_cli.database.connection import Session
from sesg_cli.database.models import (
    Experiment,
)
from sesg_cli.database.models.search_string_performance import (
    SearchStringPerformanceFactory,
)


class AsyncTyper(typer.Typer):
    def async_command(self, *args, **kwargs):
        def decorator(async_func):
            @wraps(async_func)
            def sync_func(*_args, **_kwargs):
                return trio.run(partial(async_func, *_args, **_kwargs))

            self.command(*args, **kwargs)(sync_func)
            return async_func

        return decorator


app = AsyncTyper(rich_markup_mode="markdown", help="Perform Scopus searches.")


@app.async_command()
async def search(
    experiment_name: str = typer.Argument(
        ...,
        help="Name of the experiment to retrieve the search strings from.",
    ),
    config_file_path: Path = typer.Option(
        Path.cwd() / "config.toml",
        "--config-file-path",
        "-c",
        help="Path to the `config.toml` file.",
    ),
):
    """Searches the strings of the experiment on Scopus."""
    with Session() as session:
        experiment = Experiment.get_by_name(experiment_name, session)
        slr = experiment.slr

        config = Config.from_toml(config_file_path)

        print("Retrieving experiment search strings...")
        search_strings_list = experiment.get_search_strings_without_performance(session)

        search_string_performance_factory = SearchStringPerformanceFactory(
            qgs=experiment.qgs,
            gs=slr.gs,
        )

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
                total=len(search_strings_list),
            )

            for search_string in search_strings_list:
                progress_task = progress.add_task(
                    "Paginating",
                )

                results: list[SuccessResponse.Entry] = []

                try:
                    async for page in client.search(search_string.string):
                        progress.update(
                            progress_task,
                            total=page.n_pages,
                            advance=1,
                        )

                        results.extend(page.entries)

                except InvalidStringError:
                    print("The following string raised an InvalidStringError")
                    print(search_string.string)

                progress.remove_task(progress_task)

                performance = search_string_performance_factory.create(
                    search_string=search_string,
                    scopus_studies_list=results,
                )

                session.add(performance)
                session.commit()

                progress.advance(overall_task)

            progress.remove_task(overall_task)
