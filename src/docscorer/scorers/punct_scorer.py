from docscorer.configuration import ScorerConfiguration
from docscorer.scorers.base_scorer import BaseScorer


class PunctScorer(BaseScorer):
    MAX_SCORE = 10.0
    MIN_SCORE = 0.0

    def __init__(self, config: ScorerConfiguration):
        self.config = config

    def score(
        self, ref_language: str, num_punctuation_chars: int, num_word_chars: int
    ) -> float:
        if num_word_chars == 0:
            return 0.0

        percent_max = self._get_threshold(
            self.config.PUNCTUATION_PERCENT_MAX, ref_language
        )
        percent_bad = self._get_threshold(
            self.config.PUNCTUATION_PERCENT_BAD, ref_language
        )
        percent_semibad = self._get_threshold(
            self.config.PUNCTUATION_PERCENT_SEMIBAD, ref_language
        )
        percent_desired_max = self._get_threshold(
            self.config.PUNCTUATION_PERCENT_DESIRED_MAX, ref_language
        )
        percent_desired_min = self._get_threshold(
            self.config.PUNCTUATION_PERCENT_DESIRED_MIN, ref_language
        )

        ratio = round((num_punctuation_chars / num_word_chars) * 100, 1)

        if percent_desired_min <= ratio <= percent_desired_max:
            return self.MAX_SCORE
        elif ratio >= percent_bad[0]:
            ratio = min(ratio, percent_max)
            return self._scale(ratio, percent_max, percent_bad[0], self.MIN_SCORE, 5.0)
        elif ratio >= percent_semibad[0]:
            return self._scale(ratio, percent_bad[0], percent_semibad[0], 5.0, 7.0)
        elif ratio > percent_desired_max:
            return self._scale(
                ratio, percent_semibad[0], percent_desired_max, 7.0, self.MAX_SCORE
            )
        elif ratio >= percent_semibad[1]:
            return self._scale(
                ratio, percent_semibad[1], percent_desired_min, 5.0, self.MAX_SCORE
            )
        else:
            return self._scale(ratio, 0.0, percent_semibad[1], self.MIN_SCORE, 5.0)
