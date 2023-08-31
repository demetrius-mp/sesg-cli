import typer
import pandas as pd

from pathlib import Path
from rich.progress import Progress
from typing import NoReturn

from sesg_cli.database.models import SearchStringPerformance
from sesg_cli.database import Session
from sesg_cli.database.util.results_queries import ResultQuery
from sesg_cli.database.models import SLR

_AVAILABLE_METRICS = ["start_set_f1_score", "bsb_recall", "sb_recall"]
_DEFAULT_METRICS = ["start_set_precision", "start_set_recall"]
_IMPLEMENTED_ALGORITHMS = ["lda", "bt"]

app = typer.Typer(
    rich_markup_mode="markdown", help="Get experiments' results."
)


class InvalidMetric(Exception):
    """The metric passed as a parameter is not valid"""


class InvalidAlgorithm(Exception):
    """The algorithm passed as a parameter is not valid"""


def verify_metrics_and_algorithms(metrics: list[str] | None, algorithms: list[str] | None) -> NoReturn:
    if not set(metrics or []).issubset(set(_AVAILABLE_METRICS)):
        raise InvalidMetric()

    if not set(algorithms or []).issubset(set(_IMPLEMENTED_ALGORITHMS)):
        raise InvalidAlgorithm()


def adjust_max_col_width(df: pd.DataFrame, writer: pd.ExcelWriter, sheet_name: str):
    for column in df:
        max_col_width = max(df[column].astype(str).map(len).max(), len(column))
        col_idx = df.columns.get_loc(column)
        writer.sheets[sheet_name].set_column(col_idx, col_idx, max_col_width)


def graph_tab(slr_name: str, excel_writer: pd.ExcelWriter):
    sheet_name = 'graph_info'

    with Session() as session:
        slr = SLR.get_by_name(slr_name, session)
        number_of_components, mean_degree = slr.get_graph_statistics()

    data = {'number_of_components': number_of_components,
            'mean_degree': round(mean_degree, 3)}

    df = pd.DataFrame().from_dict(data, orient='index')

    df.rename(columns={0: 'values'}, inplace=True)
    df.to_excel(excel_writer=excel_writer, sheet_name=sheet_name)
    excel_writer.sheets[sheet_name].set_column(0, 1, 25)


def save_xlsx(excel_writer: pd.ExcelWriter, results: dict[str, dict], slr: str):
    with Progress() as progress:
        saving_progress = progress.add_task(
            "[green]Saving...", total=len(results)
        )
        with excel_writer:
            for i, (key, result) in enumerate(results.items()):
                df = pd.DataFrame(data=result['data'], columns=result['columns'])

                if 'name' in df.columns:
                    cols = df.columns.tolist()
                    cols.remove('name')
                    cols.insert(0, 'name')
                    df = df[cols]

                df.to_excel(excel_writer=excel_writer, sheet_name=key, index=False)
                adjust_max_col_width(df, excel_writer, key)

                progress.update(
                    saving_progress,
                    description=f"[green]Saving {i + 1} of {len(results)}",
                    advance=1,
                    refresh=True,
                )

            overall_results = {key: value for key, value in results.items() if key in _IMPLEMENTED_ALGORITHMS}
            statistics_tab(overall_results, excel_writer)
            graph_tab(slr, excel_writer)

        progress.remove_task(saving_progress)


def statistics_tab(results: dict[dict], excel_writer: pd.ExcelWriter) -> NoReturn:
    root_cols = ['start_set_precision', 'start_set_recall', 'start_set_f1_score',
                 'bsb_recall', 'sb_recall', 'n_scopus_results']
    max_cols_highlight = ['mean_start_set_precision', 'mean_start_set_recall', 'mean_start_set_f1_score',
                          'mean_bsb_recall', 'mean_sb_recall']

    idx = list()
    for col in root_cols:
        idx.append(f'mean_{col}')
        idx.append(f'stdev_{col}')

    stats_df = pd.DataFrame(columns=_IMPLEMENTED_ALGORITHMS, index=idx)

    for key, result in results.items():
        temp_df = pd.DataFrame(data=result['data'], columns=result['columns'])
        temp_df = temp_df.drop(temp_df[temp_df["n_scopus_results"] == 0].index)

        for col in root_cols:
            stats_df.loc[f'mean_{col}', key] = round(temp_df[col].mean(), 5)
            stats_df.loc[f'stdev_{col}', key] = round(temp_df[col].std(), 5)

    stats_df = stats_df.T

    style_stats = stats_df.style \
        .highlight_max(subset=max_cols_highlight, color='#8aeda4') \
        .highlight_min(subset=['mean_n_scopus_results'], color='#8aeda4')

    stats_df = stats_df.reset_index()
    stats_df.rename(columns={'index': 'algorithm'}, inplace=True)

    style_stats.to_excel(excel_writer=excel_writer, sheet_name='stats')
    adjust_max_col_width(stats_df, excel_writer, 'stats')


@app.command(help='Creates a Excel file based on the given Path and SLR.')
def save(
        path: Path = typer.Argument(
            ...,
            help="Path to the **folder** where the results Excel file should be saved.",
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

    result_query: ResultQuery = ResultQuery(slr, metrics, algorithms)
    queries = result_query.get_queries()

    with Session() as session:
        results = SearchStringPerformance.get_results(queries, result_query.check_review, session)

    excel_writer = pd.ExcelWriter(path / f"{slr}.xlsx", engine='xlsxwriter')

    save_xlsx(excel_writer, results, slr)


@app.command(help='Creates a Excel file with the best `top` '
                  'results from each experiment based on the given Path and SLR.')
def save_by_row(
        path: Path = typer.Argument(
            ...,
            help="Path to the **folder** where the results Excel file should be saved",
            dir_okay=True,
            exists=True,
        ),
        slr: str = typer.Argument(
            ...,
            help="Name of the SLR the results will be extracted."
        ),
        top: int = typer.Option(
            default=10,
            help="Number of best results per experiment to be retrieved.",
        ),
        metrics: list[str] = typer.Option(
            default=None,
            help="Bonus metrics to order the results and generate bonus lists. "
                 f"Available metrics: {[f'`{i}`' for i in _AVAILABLE_METRICS]} "
                 f"(outside the defaults: {[f'`{i}`' for i in _DEFAULT_METRICS]})",
            show_default=False
        ),
        algorithms: list[str] = typer.Option(
            default=None,
            help=f"Bonus algorithms to generate Excel sheets "
                 f"(outside the defaults: {[f'`{i}`' for i in _IMPLEMENTED_ALGORITHMS]}). "
                 f"Important: a base query for the algorithm need to be previously implemented.",
            hidden=True
        )
):
    verify_metrics_and_algorithms(metrics, algorithms)

    print("Retrieving information from database...")

    result_query: ResultQuery = ResultQuery(slr, metrics, algorithms, top)
    queries = result_query.get_queries_by_row()

    with Session() as session:
        results = SearchStringPerformance.get_results(queries, result_query.check_review, session)

    excel_writer = pd.ExcelWriter(path / f"{slr}_top_per_exp.xlsx", engine='xlsxwriter')

    save_xlsx(excel_writer, results, slr)
