from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, Integer, text
from sqlalchemy.orm import Mapped, Session, mapped_column, relationship

from .association_tables import gs_in_bsb, gs_in_sb, gs_in_scopus, qgs_in_scopus
from .base import Base


if TYPE_CHECKING:
    from .search_string import SearchString
    from .study import Study


class ReviewDoesNotExist(Exception):
    """The review passed as a param does not exist in the database."""


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

    @staticmethod
    def get_results(
        queries: dict[str, str],
        session: Session
    ) -> dict[str, dict]:
        """
        Responsible for retrieving all the data needed to construct a results Excel file.

        Args:
            queries: all the queries necessary to compose the final Excel file.
            check_review_query: query to ensure the SLR exists.
            session: A db session.

        Returns: a dictionary with the following structure:
            {'{query_name}': {'columns': all the columns that were in the select statement
                            'data': all the Rows resulting of the query}}

        """
        results: dict = {}

        for query_name, query in queries.items():
            cursor = session.execute(text(query))
            exec_results = cursor.fetchall()
            results[query_name] = {'columns': tuple(
                cursor.keys()), 'data': exec_results}

        return results

    @staticmethod
    def get_strategies_used(
        queries: dict[str, str],
        check_review_query: str,
        session: Session
    ) -> dict[str, dict]:
        """_summary_

        Args:
            queries: sql queries to be executed.
            check_review_query: query to check if the review exists.
            session: database connection session.
        Raises:
            ReviewDoesNotExist: If the review does not exist in the database.
        Returns:
            Query results in a dictionary.
        """
        results: dict = {}

        if not bool(session.execute(text(check_review_query)).scalar()):
            raise ReviewDoesNotExist()

        for query_name, query in queries.items():
            cursor = session.execute(text(query))
            exec_results = cursor.fetchall()
            results[query_name] = [*exec_results]

        return results
