from dataclasses import dataclass

from sesg.similar_words.bert_strategy import BertSimilarWordsGenerator
from sesg.similar_words.protocol import SimilarWordsGenerator
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from sesg_cli.database.models import SimilarWord, SimilarWordsCache
from sesg_cli.strategies_implementations.llm_similar_words_generator import (
    LlmSimilarWordsGenerator,
)


@dataclass
class SimilarWordsGeneratorCache(SimilarWordsGenerator):
    similar_word_generator: BertSimilarWordsGenerator | LlmSimilarWordsGenerator
    session: Session
    experiment_id: int

    def get_from_cache(self, key: str) -> list[str] | None:
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

    def save_on_cache(self, key: str, value: list[str]) -> None:
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

    def __call__(self, word: str) -> list[str]:
        if (similar_words := self.get_from_cache(word)) is not None:
            return similar_words

        similar_words = self.similar_word_generator(word)

        self.save_on_cache(word, similar_words)

        return similar_words
