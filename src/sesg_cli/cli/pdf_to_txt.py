import os
from pathlib import Path

import PyPDF2
import typer
from rich.progress import Progress

app = typer.Typer(
    rich_markup_mode="markdown", help="Convert pdfs to txt"
)


@app.command()
def convert(
    slr_folder_path: Path = typer.Argument(
        ...,
        help="Path to pdfs folder to be converted",
        dir_okay=True,
        exists=True,
    )
):
    files: list[str] = os.listdir(f"{slr_folder_path}\\pdfs")

    with Progress() as progress:
        convertion_progress = progress.add_task(
            "[green]Converting...", total=len(files)
        )
        for index, file in enumerate(files):
            paper_id: str = file.strip(".pdf")

            with open(slr_folder_path / f"pdfs\\{file}", "rb") as f:
                try:
                    reader: PyPDF2.PdfReader = PyPDF2.PdfReader(f)
                    text: str = ""

                    for page_num in range(len(reader.pages)):
                        page = reader.pages[page_num]
                        text += page.extract_text()
                except Exception as e:
                    print(f"File: {file}\nError: {e}")

                with open(
                    slr_folder_path / f"txts\\{paper_id}.txt",
                    "w",
                    encoding="utf-8",
                ) as f:
                    f.write(text)

            progress.update(
                convertion_progress,
                description=f"[green]Converting {index+1} of {len(files)}",
                advance=1,
                refresh=True,
            )
