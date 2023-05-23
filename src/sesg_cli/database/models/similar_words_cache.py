from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from .base import Base

if TYPE_CHECKING:
    from .experiment import Experiment
    from .similar_words_cache_words import SimilarWord


class SimilarWordsCache(Base):
    __tablename__ = "similar_words_cache"

    id: Mapped[int] = mapped_column(primary_key=True, init=False)

    experiment_id: Mapped[int] = mapped_column(
        ForeignKey("experiment.id"),
        nullable=False,
    )
    experiment: Mapped["Experiment"] = relationship(
        back_populates="similar_words_cache",
        default=None,
        init=False,
    )

    word: Mapped[str] = mapped_column(Text())

    similar_words_list: Mapped[list["SimilarWord"]] = relationship(
        back_populates="similar_words_cache",
        default_factory=list,
    )

    __table_args__ = (UniqueConstraint("experiment_id", "word"),)
