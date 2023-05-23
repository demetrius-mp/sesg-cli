from typing import TYPE_CHECKING

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

    scopus_precision: Mapped[float] = mapped_column(Float())
    scopus_recall: Mapped[float] = mapped_column(Float())
    scopus_f1_score: Mapped[float] = mapped_column(Float())

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
