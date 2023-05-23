from enum import Enum
from pathlib import Path

import typer
from rich import print
from sesg.graph import create_citation_graph, edges_to_adjacency_list

from sesg_cli.database import Session
from sesg_cli.database.models import SLR, SearchString


class SourceChoices(str, Enum):
    slr = "slr"
    search_string = "search-string"


app = typer.Typer(
    rich_markup_mode="markdown",
    help="Render citation graphs. A node represents a paper, and the directed edge `A -> B` means that paper `A` **references** paper `B` (or that paper `B` is **cited by** paper `A`).",  # noqa: E501
)


@app.command()
def render_slr(
    out_path: Path = typer.Argument(
        ...,
        exists=False,
        file_okay=False,
        dir_okay=False,
        help="Path to the output file, without any extensions",
    ),
    slr_name: str = typer.Argument(
        ...,
        help="Name of the Systematic Literature Review",
    ),
):
    with Session() as session:
        slr = SLR.get_by_name(slr_name, session)
        edges: list[tuple[int, int]] = list()
        for s in slr.gs:
            edges.extend((s.node_id, ref.node_id) for ref in s.references)

        if len(edges) == 0:
            print("[red]Snowballing was never executed for this SLR.")
            raise typer.Abort()

        g = create_citation_graph(
            adjacency_list=edges_to_adjacency_list(edges=edges),
            tooltips={s.node_id: s.title for s in slr.gs},
        )

        g.render(
            filename=out_path.stem + ".dot",
            directory=out_path.parent,
            format="pdf",
            view=True,
        )


@app.command()
def render_search_string(
    out_path: Path = typer.Argument(
        ...,
        exists=False,
        file_okay=False,
        dir_okay=False,
        help="Path to the output file, without any extensions",
    ),
    slr_name: str = typer.Argument(
        ...,
        help="Name of the Systematic Literature Review",
    ),
    search_string_id: int = typer.Argument(
        ...,
        help="Id of the search string to render",
    ),
):
    with Session() as session:
        search_string = SearchString.get_by_id(search_string_id, session)
        performance = search_string.performance

        if performance is None:
            print("The search string was not searched.")
            raise typer.Abort()

        slr = SLR.get_by_name(slr_name, session)
        edges: list[tuple[int, int]] = list()
        for s in slr.gs:
            edges.extend((s.node_id, ref.node_id) for ref in s.references)

        if len(edges) == 0:
            print("[red]Snowballing was never executed for this SLR.")
            raise typer.Abort()

        g = create_citation_graph(
            adjacency_list=edges_to_adjacency_list(edges=edges),
            tooltips={s.id: s.title for s in slr.gs},
            results_list=[s.id for s in performance.gs_in_sb],
        )

        g.attr(label=r"Dashed -> Not found\nBold -> Snowballing\nFilled -> Search")

        g.render(
            filename=out_path.stem + ".dot",
            directory=out_path.parent,
            format="pdf",
            view=True,
        )
