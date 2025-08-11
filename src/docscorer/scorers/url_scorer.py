from enum import Enum
from typing import List

from docscorer.configuration import ScorerConfiguration
from docscorer.scorers.base_scorer import BaseScorer


class URLThreshold(Enum):
    LOW = 3
    MID = 5
    HIGH = 10


class URLScorer(BaseScorer):
    MAX_SCORE = 10.0
    MIN_SCORE = 0.0

    def __init__(self, config: ScorerConfiguration):
        self.config = config

    def score(self, ref_language: str, document: str, word_chars: List[int]) -> float:
        menu_length = self._get_threshold(
            self.config.MENUS_AVERAGE_LENGTH, ref_language
        )

        # Only consider segments longer than menu_length
        long_segments = [x for x in word_chars if x > menu_length]
        if not long_segments:
            return self.MAX_SCORE

        # Normalization factor based on menu length
        reference_text_length = menu_length * 100
        ratio_respect_reference = sum(word_chars) / reference_text_length or 0.1

        url_count = max(document.count("www"), document.count("http"))
        url_quantity = url_count / ratio_respect_reference

        if url_quantity <= URLThreshold.LOW.value:
            return self.MAX_SCORE
        if url_quantity >= URLThreshold.MID.value:
            return self.MIN_SCORE
        if url_quantity > URLThreshold.HIGH.value:
            return self._scale(url_quantity, 10, 7, 0.0, 5.0)
        # else: between 3 and 5
        return self._scale(url_quantity, 7, 3, 5.0, 10.0)
