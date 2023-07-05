import typer
import pandas as pd

from pathlib import Path
from rich.progress import Progress
from typing import NoReturn

from sesg_cli.database.models import SearchStringPerformance
from sesg_cli.database import Session
from sesg_cli.database.util.results_queries import ResultQuery

_AVAILABLE_METRICS = ["st_f1_score", "bsb_recall", "final_recall"]
_DEFAULT_METRICS = ["st_precision", "st_recall"]
_IMPLEMENTED_ALGORITHMS = ["lda", "bt"]

app = typer.Typer(
    rich_markup_mode="markdown", help="Get experiments' results"
)


class InvalidMetric(Exception):
    """The metric passed as a parameter is not valid"""


class InvalidAlgorithm(Exception):
    """The algorithm passed as a parameter is not valid"""


@app.command(help='Creates a Excel file based on the given Path and SLR')
def save(
        path: Path = typer.Argument(
            ...,
            help="Path where the results Excel file should be saved.",
            dir_okay=True,
            exists=True,
        ),
        slr: str = typer.Argument(
            ...,
            help="Name of the SLR the results will be extracted."
        ),
        metrics: list[str] = typer.Option(
            default=None,
            help="Bonus metrics to order the results and generate bonus top 10 lists. "
                 f"Available metrics: {[f'`{i}`' for i in _AVAILABLE_METRICS]} "
                 f"(outside the defaults: {[f'`{i}`' for i in _DEFAULT_METRICS]})",
            show_default=False
        ),
        algorithms: list[str] = typer.Option(
            default=None,
            help=f"Bonus algorithms to generate Excel (outside the defaults: {[f'`{i}`' for i in _IMPLEMENTED_ALGORITHMS]}). "
                 f"Important: a base query for the algorithm need to be previously implemented.",
            hidden=True
        )
):
    verify_metrics_and_algorithms(metrics, algorithms)

    print("Retrieving information from database...")

    results_query: ResultQuery = ResultQuery(slr, metrics, algorithms)

    with Session() as session:
        results = SearchStringPerformance.get_results(results_query, session)

    excel_writer = pd.ExcelWriter(path / f"{slr}.xlsx", engine='xlsxwriter')

    with Progress() as progress:
        saving_progress = progress.add_task(
            "[green]Saving...", total=len(results)
        )
        with excel_writer:
            for i, (key, result) in enumerate(results.items()):
                df = pd.DataFrame(data=result['data'], columns=result['columns'])
                df.to_excel(excel_writer=excel_writer, sheet_name=key, index=False)

                for column in df:
                    max_col_width = max(df[column].astype(str).map(len).max(), len(column))
                    col_idx = df.columns.get_loc(column)
                    excel_writer.sheets[key].set_column(col_idx, col_idx, max_col_width)

                progress.update(
                    saving_progress,
                    description=f"[green]Saving {i + 1} of {len(results)}",
                    advance=1,
                    refresh=True,
                )


def verify_metrics_and_algorithms(metrics: list[str] | None, algorithms: list[str] | None) -> NoReturn:
    if metrics:
        for metric in metrics:
            if metric not in _AVAILABLE_METRICS:
                raise InvalidMetric()

    if algorithms:
        for algorithm in algorithms:
            if algorithm not in _IMPLEMENTED_ALGORITHMS:
                raise InvalidAlgorithm()
