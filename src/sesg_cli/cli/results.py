import typer
import pandas as pd

from pathlib import Path
from sesg_cli.database.models import SearchStringPerformance
from sesg_cli.database import Session
from sesg_cli.database.util.results_queries import ResultQuery
from rich.progress import Progress

_AVAILABLE_METRICS = ["`st_f1_score`", "`bsb_recall`", "`final_recall`"]
_DEFAULT_METRICS = ["`st_precision`", "`st_recall`"]

app = typer.Typer(
    rich_markup_mode="markdown", help="Get experiments' results"
)


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
                 f"Available metrics: {_AVAILABLE_METRICS} (outside the defaults: {_DEFAULT_METRICS})"
        ),
        algorithms: list[str] = typer.Option(
            default=None,
            help="Bonus algorithms to generate Excel tabs such as `lda` or `bt`. Important: a base query for the "
                 "algorithm need to be previously implemented."
        )
):
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
