import asyncio
from functools import wraps
from pathlib import Path

import typer
from rich import print
from rich.progress import BarColumn, Progress, TaskProgressColumn, TextColumn
from sesg.scopus.multi_client import create_clients_list

from sesg_cli.config import Config
from sesg_cli.database.connection import Session
from sesg_cli.database.models import (
    Experiment,
)
from sesg_cli.multi_client_scopus_search import (
    MultiClientScopusSearch,
    SearchStringPerformanceFactory,
)


class AsyncTyper(typer.Typer):
    def async_command(self, *args, **kwargs):
        def decorator(async_func):
            @wraps(async_func)
            def sync_func(*_args, **_kwargs):
                return asyncio.run(async_func(*_args, **_kwargs))

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
    timeout: int = typer.Option(
        5,
        "--timeout",
        "-t",
        help="Time in seconds to wait for an API response before retrying.",
    ),
    timeout_retries: int = typer.Option(
        10,
        "--timeout-retries",
        "-r",
        help="How much times in a row to redo a timed out request.",
    ),
    n_clients: int = typer.Option(
        2,
        "--n-clients",
        "-n",
        help="Number of Scopus Clients to use.",
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

        clients_list = create_clients_list(
            api_keys_list=config.scopus_api_keys,
            n_clients=n_clients,
            timeout=timeout,
            timeout_retries=timeout_retries,
        )

        with Progress(
            TextColumn(
                "[progress.description]{task.description}: {task.completed} of {task.total}"  # noqa: E501
            ),
            BarColumn(),
            TaskProgressColumn(),
        ) as progress:
            multi_client_scopus_search = MultiClientScopusSearch(
                clients_list=clients_list,
                db_search_strings_list=search_strings_list,
                search_string_performance_factory=search_string_performance_factory,
                progress=progress,
                session=session,
            )

            await multi_client_scopus_search.start()
