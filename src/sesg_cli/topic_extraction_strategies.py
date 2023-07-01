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
