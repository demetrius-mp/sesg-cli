from typing import TYPE_CHECKING

from sqlalchemy import (
    ForeignKey,
    Text,
    select,
)
from sqlalchemy.orm import (
    Mapped,
    Session,
    mapped_column,
    relationship,
)

from .association_tables import experiment_qgs
from .base import Base


if TYPE_CHECKING:
    from .params import Params
    from .similar_words_cache import SimilarWordsCache
    from .slr import SLR
    from .study import Study


class Experiment(Base):
    __tablename__ = "experiment"

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    name: Mapped[str] = mapped_column(Text(), unique=True)

    slr_id: Mapped[int] = mapped_column(ForeignKey("slr.id"))
    slr: Mapped["SLR"] = relationship(
        back_populates="experiments",
        init=False,
    )

    qgs: Mapped[list["Study"]] = relationship(
        secondary=experiment_qgs,
        back_populates="experiments",
        default_factory=list,
    )

    params_list: Mapped[list["Params"]] = relationship(
        back_populates="experiment",
        default_factory=list,
    )

    similar_words_cache: Mapped[list["SimilarWordsCache"]] = relationship(
        back_populates="experiment",
        default_factory=list,
    )

    @classmethod
    def get_by_name(
        cls,
        name: str,
        session: Session,
    ):
        stmt = select(Experiment).where(Experiment.name == name)

        return session.execute(stmt).scalar_one()

    @classmethod
    def get_or_create_by_name(
        cls,
        name: str,
        session: Session,
        slr_id: int,
    ):
        stmt = select(Experiment).where(Experiment.name == name)

        experiment = session.execute(stmt).scalar_one_or_none()

        if experiment is None:
            experiment = Experiment(
                name=name,
                slr_id=slr_id,
            )

        return experiment

    def get_search_strings_without_performance(
        self,
        session: Session,
    ):
        from .params import Params
        from .search_string import SearchString
        from .search_string_performance import SearchStringPerformance

        stmt = (
            select(SearchString)
            .join(SearchString.performance, isouter=True)
            .where(SearchStringPerformance.id.is_(None))
            .join(SearchString.params_list)
            .where(Params.experiment_id == self.id)
        )

        results = session.execute(stmt).scalars().all()

        unique_results: dict[str, SearchString] = {}
        for r in results:
            unique_results[r.string] = r

        return list(unique_results.values())

    def get_docs(self):
        from sesg.topic_extraction.create_docs import create_docs

        docs = create_docs(
            [
                {
                    "abstract": s.abstract,
                    "keywords": s.keywords,
                    "title": s.title,
                }
                for s in self.qgs
            ]
        )

        return docs

    def get_enrichment_text(self):
        from sesg.similar_words.bert_strategy import BertSimilarWordsGenerator

        enrichment_text = BertSimilarWordsGenerator.create_enrichment_text(
            [
                {
                    "abstract": s.abstract,
                    "title": s.title,
                }
                for s in self.qgs
            ]
        )

        return enrichment_text
