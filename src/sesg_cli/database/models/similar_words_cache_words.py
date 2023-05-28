from typing import TYPE_CHECKING

from sqlalchemy import (
    ForeignKey,
    Text,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from .base import Base


if TYPE_CHECKING:
    from .similar_words_cache import SimilarWordsCache


class SimilarWord(Base):
    __tablename__ = "similar_word"

    id: Mapped[int] = mapped_column(primary_key=True, init=False)

    word: Mapped[str] = mapped_column(Text())

    similar_words_cache_id: Mapped[int] = mapped_column(
        ForeignKey("similar_words_cache.id"),
        nullable=False,
        default=None,
    )
    similar_words_cache: Mapped["SimilarWordsCache"] = relationship(
        back_populates="similar_words_list",
        default=None,
    )
