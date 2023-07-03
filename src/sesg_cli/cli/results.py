import typer
from pathlib import Path
import pandas as pd
from sesg_cli.database.models import SearchStringPerformance
from sesg_cli.database import Session

app = typer.Typer(
    rich_markup_mode="markdown", help="Get experiments' results"
)


@app.command(help='Creates a Excel file based on the given Path and SLR')
def save(
        path: Path = typer.Argument(
            ...,
            help="Path where the results Excel file should be saved.",
            dir_okay=True,
            exists=True
        ),
        slr: str = typer.Argument(
            ...,
            help="Name of the SLR the results will be extracted."
        )
):
    #todo: add progress
    #todo: verification for the slr passed

    print("Retrieving information from database...")
    with Session() as session:
        results = SearchStringPerformance.get_results(slr, session)

    excel_writer = pd.ExcelWriter(path / f"{slr}.xlsx", engine='xlsxwriter')

    # todo: apply some styles
    # excel_writer_book = excel_writer.book
    # header_format = excel_writer_book.add_format({'bold': True, 'bg_color': '#808080'})

    with excel_writer:
        for key, result in results.items():
            df = pd.DataFrame(data=result['data'], columns=result['columns'])
            df.to_excel(excel_writer=excel_writer, sheet_name=key, index=False)

            for column in df:
                max_col_width = max(df[column].astype(str).map(len).max(), len(column))
                col_idx = df.columns.get_loc(column)
                excel_writer.sheets[key].set_column(col_idx, col_idx, max_col_width)