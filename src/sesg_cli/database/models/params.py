from itertools import product
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    UniqueConstraint,
    select,
)
from sqlalchemy.orm import (
    Mapped,
    Session,
    mapped_column,
    relationship,
)

from sesg_cli.config import Config
from sesg_cli.topic_extraction_strategies import TopicExtractionStrategy

from .base import Base
from .bertopic_params import BERTopicParams
from .formulation_params import FormulationParams
from .lda_params import LDAParams


if TYPE_CHECKING:
    from .experiment import Experiment
    from .search_string import SearchString


class Params(Base):
    __tablename__ = "params"

    id: Mapped[int] = mapped_column(primary_key=True, init=False)

    experiment_id: Mapped[int] = mapped_column(
        ForeignKey("experiment.id"),
        nullable=False,
    )
    experiment: Mapped["Experiment"] = relationship(
        back_populates="params_list",
        default=None,
        init=False,
    )

    formulation_params_id: Mapped[int] = mapped_column(
        ForeignKey("formulation_params.id"),
    )
    formulation_params: Mapped["FormulationParams"] = relationship(
        back_populates="params",
    )

    lda_params_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("lda_params.id"),
        nullable=True,
        default=None,
    )
    lda_params: Mapped[Optional["LDAParams"]] = relationship(
        back_populates="params",
        default=None,
    )

    bertopic_params_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("bertopic_params.id"),
        nullable=True,
        default=None,
    )
    bertopic_params: Mapped[Optional["BERTopicParams"]] = relationship(
        back_populates="params",
        default=None,
    )

    search_string_id: Mapped[int] = mapped_column(
        ForeignKey("search_string.id"),
        nullable=False,
        init=False,
    )
    search_string: Mapped["SearchString"] = relationship(
        back_populates="params_list",
        init=False,
    )

    __table_args__ = (
        CheckConstraint("lda_params_id is not null or bertopic_params_id is not null"),
        UniqueConstraint("experiment_id", "formulation_params_id", "lda_params_id"),
        UniqueConstraint(
            "experiment_id", "formulation_params_id", "bertopic_params_id"
        ),
    )

    @classmethod
    def get_one_or_none(
        cls,
        experiment_id: int,
        formulation_params_id: int,
        session: Session,
        bertopic_params_id: int | None = None,
        lda_params_id: int | None = None,
    ):
        stmt = select(Params).where(
            Params.experiment_id == experiment_id,
            Params.formulation_params_id == formulation_params_id,
        )

        if bertopic_params_id is not None:
            stmt = stmt.where(Params.bertopic_params_id == bertopic_params_id)

        if lda_params_id is not None:
            stmt = stmt.where(Params.lda_params_id == lda_params_id)

        return session.execute(stmt).scalar_one_or_none()

    @classmethod
    def create_with_lda_params(
        cls,
        formulation_params_list: list[FormulationParams],
        lda_params_list: list[LDAParams],
        experiment_id: int,
    ):
        return [
            Params(
                experiment_id=experiment_id,
                lda_params=lda_params,
                lda_params_id=lda_params.id,
                formulation_params=formulation_params,
                formulation_params_id=formulation_params.id,
            )
            for lda_params, formulation_params in product(
                lda_params_list,
                formulation_params_list,
            )
        ]

    @classmethod
    def create_with_bertopic_params(
        cls,
        formulation_params_list: list[FormulationParams],
        bertopic_params_list: list[BERTopicParams],
        experiment_id: int,
    ):
        return [
            Params(
                experiment_id=experiment_id,
                bertopic_params=bertopic_params,
                bertopic_params_id=bertopic_params.id,
                formulation_params=formulation_params,
                formulation_params_id=formulation_params.id,
            )
            for bertopic_params, formulation_params in product(
                bertopic_params_list,
                formulation_params_list,
            )
        ]

    @classmethod
    def create_with_strategy(
        cls,
        strategy: "TopicExtractionStrategy",
        config: Config,
        experiment_id: int,
        session: Session,
    ):
        formulation_params_list = FormulationParams.get_or_save_from_params_product(
            n_similar_words_per_word_list=config.formulation_params.n_similar_words_per_word,
            n_words_per_topic_list=config.formulation_params.n_words_per_topic,
            session=session,
        )

        if strategy == TopicExtractionStrategy.bertopic:
            model_params_list = (
                BERTopicParams.get_or_save_from_params_product(  # noqa: E501
                    kmeans_n_clusters_list=config.bertopic_params.kmeans_n_clusters,
                    umap_n_neighbors_list=config.bertopic_params.umap_n_neighbors,
                    session=session,
                )
            )

            return cls.create_with_bertopic_params(
                formulation_params_list=formulation_params_list,
                bertopic_params_list=model_params_list,
                experiment_id=experiment_id,
            )

        elif strategy == TopicExtractionStrategy.lda:
            model_params_list = LDAParams.get_or_save_from_params_product(
                n_topics_list=config.lda_params.n_topics,
                min_document_frequency_list=config.lda_params.min_document_frequency,
                session=session,
            )

            return cls.create_with_lda_params(
                formulation_params_list=formulation_params_list,
                lda_params_list=model_params_list,
                experiment_id=experiment_id,
            )
