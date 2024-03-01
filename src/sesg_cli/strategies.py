from enum import Enum


class TopicExtractionStrategy(str, Enum):
    """Enum defining the available topic extraction strategies.

    Examples:
        >>> lda_strategy = TopicExtractionStrategy.lda
        >>> lda_strategy.value
        'lda'
    """

    lda = "lda"
    bertopic = "bertopic"


class SimilarWordGeneratorStrategy(str, Enum):
    """Enum defining the available similar word generation strategies.

    Examples:
        >>> bert_strategy = SimilarWordGeneratorStrategy.bert
        >>> bert_strategy.value
        'bert'
    """
    bert = "bert"
    llm = "llm"
