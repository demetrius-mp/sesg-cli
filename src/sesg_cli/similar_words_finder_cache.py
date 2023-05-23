from dataclasses import dataclass

from sesg.search_string import SimilarWordsFinderCacheProtocol
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from sesg_cli.database.models import SimilarWord, SimilarWordsCache


@dataclass
class Cache(SimilarWordsFinderCacheProtocol):
    session: Session
    experiment_id: int

    def get(self, key: str) -> list[str] | None:
        stmt = (
            select(SimilarWordsCache)
            .options(joinedload(SimilarWordsCache.similar_words_list))
            .where(SimilarWordsCache.experiment_id == self.experiment_id)
            .where(SimilarWordsCache.word == key)
        )

        result = self.session.execute(stmt).unique().scalar_one_or_none()

        if result is None:
            return None

        return [similar.word for similar in result.similar_words_list]

    def set(self, key: str, value: list[str]) -> None:
        s = SimilarWordsCache(
            experiment_id=self.experiment_id,
            word=key,
            similar_words_list=[
                SimilarWord(
                    word=w,
                )
                for w in value
            ],
        )

        self.session.add(s)
        self.session.commit()
