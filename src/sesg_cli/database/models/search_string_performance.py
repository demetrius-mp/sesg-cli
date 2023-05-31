from typing import TYPE_CHECKING

from sesg import graph
from sesg.metrics import Metrics, preprocess_string, similarity_score
from sesg.scopus import (
    Page,
)
from sqlalchemy import (
    Float,
    ForeignKey,
    Integer,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from .association_tables import gs_in_bsb, gs_in_sb, gs_in_scopus, qgs_in_scopus
from .base import Base


if TYPE_CHECKING:
    from .search_string import SearchString
    from .study import Study


class SearchStringPerformance(Base):
    __tablename__ = "search_string_performance"

    id: Mapped[int] = mapped_column(primary_key=True, init=False)

    n_scopus_results: Mapped[int] = mapped_column(Integer())

    n_qgs_in_scopus: Mapped[int]
    qgs_in_scopus: Mapped[list["Study"]] = relationship(
        secondary=qgs_in_scopus,
    )

    n_gs_in_scopus: Mapped[int]
    gs_in_scopus: Mapped[list["Study"]] = relationship(
        secondary=gs_in_scopus,
    )

    n_gs_in_bsb: Mapped[int]
    gs_in_bsb: Mapped[list["Study"]] = relationship(
        secondary=gs_in_bsb,
    )

    n_gs_in_sb: Mapped[int]
    gs_in_sb: Mapped[list["Study"]] = relationship(
        secondary=gs_in_sb,
    )

    start_set_precision: Mapped[float] = mapped_column(Float())
    start_set_recall: Mapped[float] = mapped_column(Float())
    start_set_f1_score: Mapped[float] = mapped_column(Float())

    bsb_recall: Mapped[float] = mapped_column(Float())
    sb_recall: Mapped[float] = mapped_column(Float())

    search_string_id: Mapped[int] = mapped_column(
        ForeignKey("search_string.id"),
        unique=True,
        nullable=False,
    )
    search_string: Mapped["SearchString"] = relationship(
        back_populates="performance",
        init=False,
    )

    @classmethod
    def from_studies_lists(
        cls,
        n_scopus_results: int,
        qgs_in_scopus: list["Study"],
        gs_in_scopus: list["Study"],
        gs_in_bsb: list["Study"],
        gs_in_sb: list["Study"],
        start_set_precision: float,
        start_set_recall: float,
        start_set_f1_score: float,
        bsb_recall: float,
        sb_recall: float,
        search_string_id: int,
    ) -> "SearchStringPerformance":
        return SearchStringPerformance(
            n_scopus_results=n_scopus_results,
            qgs_in_scopus=qgs_in_scopus,
            n_qgs_in_scopus=len(qgs_in_scopus),
            gs_in_scopus=gs_in_scopus,
            n_gs_in_scopus=len(gs_in_scopus),
            gs_in_bsb=gs_in_bsb,
            n_gs_in_bsb=len(gs_in_bsb),
            gs_in_sb=gs_in_sb,
            n_gs_in_sb=len(gs_in_sb),
            start_set_precision=start_set_precision,
            start_set_recall=start_set_recall,
            start_set_f1_score=start_set_f1_score,
            bsb_recall=bsb_recall,
            sb_recall=sb_recall,
            search_string_id=search_string_id,
        )


class SearchStringPerformanceFactory:
    def __init__(
        self,
        qgs: list["Study"],
        gs: list["Study"],
    ) -> None:
        self.qgs = qgs
        self.processed_qgs = [preprocess_string(s.title) for s in qgs]

        self.gs = gs
        self.processed_gs = [preprocess_string(s.title) for s in gs]

        self.study_mapping: dict[int, "Study"] = {}
        citation_edges: list[tuple[int, int]] = []
        for s in gs:
            self.study_mapping[s.id] = s
            citation_edges.extend((s.id, ref.id) for ref in s.references)

        self.directed_adjacency_list = graph.edges_to_adjacency_list(
            edges=citation_edges,
        )
        self.undirected_adjacency_list = graph.edges_to_adjacency_list(
            edges=citation_edges,
            directed=False,
        )

    def create(
        self,
        search_string: "SearchString",
        scopus_studies_list: list[Page.Entry],
    ) -> "SearchStringPerformance":
        processed_scopus_titles = [
            preprocess_string(s.title) for s in scopus_studies_list
        ]

        qgs_in_scopus = similarity_score(
            small_set=self.processed_qgs,
            other_set=processed_scopus_titles,
        )
        qgs_in_scopus = [self.qgs[i] for i, _ in qgs_in_scopus]

        gs_in_scopus = similarity_score(
            small_set=self.processed_gs,
            other_set=processed_scopus_titles,
        )
        gs_in_scopus = [self.gs[i] for i, _ in gs_in_scopus]

        gs_in_bsb = graph.serial_breadth_first_search(
            adjacency_list=self.directed_adjacency_list,
            starting_nodes=[s.id for s in gs_in_scopus],
        )
        gs_in_bsb = [self.study_mapping[s_id] for s_id in gs_in_bsb]

        gs_in_sb = graph.serial_breadth_first_search(
            adjacency_list=self.undirected_adjacency_list,
            starting_nodes=[s.id for s in gs_in_scopus],
        )
        gs_in_sb = [self.study_mapping[s_id] for s_id in gs_in_sb]

        metrics = Metrics(
            gs_size=len(self.gs),
            n_scopus_results=len(scopus_studies_list),
            n_qgs_studies_in_scopus=len(qgs_in_scopus),
            n_gs_studies_in_scopus=len(gs_in_scopus),
            n_gs_studies_in_scopus_and_bsb=len(gs_in_bsb),
            n_gs_studies_in_scopus_and_bsb_and_fsb=len(gs_in_sb),
        )

        return SearchStringPerformance(
            n_qgs_in_scopus=len(qgs_in_scopus),
            n_gs_in_scopus=len(gs_in_scopus),
            n_gs_in_bsb=len(gs_in_bsb),
            n_gs_in_sb=len(gs_in_sb),
            qgs_in_scopus=qgs_in_scopus,
            gs_in_scopus=gs_in_scopus,
            gs_in_bsb=gs_in_bsb,
            gs_in_sb=gs_in_sb,
            n_scopus_results=metrics.n_scopus_results,
            start_set_precision=metrics.scopus_precision,
            start_set_recall=metrics.scopus_recall,
            start_set_f1_score=metrics.scopus_f1_score,
            bsb_recall=metrics.scopus_and_bsb_recall,
            sb_recall=metrics.scopus_and_bsb_and_fsb_recall,
            search_string_id=search_string.id,
        )
