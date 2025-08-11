from docscorer.scorers.base_scorer import BaseScorer
from docscorer.configuration import ScorerConfiguration


class CharsScorer(BaseScorer):
    def __init__(self, config: ScorerConfiguration):
        self.config = config

    def score(
        self, ref_language: str, num_singular_chars: int, num_word_chars: int
    ) -> float:
        if num_word_chars == 0:
            return 0

        percent_max = self._get_threshold(self.config.SINGULAR_CHARS_PERCENT_MAX, ref_language)
        percent_bad = self._get_threshold(self.config.SINGULAR_CHARS_PERCENT_BAD, ref_language)
        percent_semibad = self._get_threshold(
            self.config.SINGULAR_CHARS_PERCENT_SEMIBAD, ref_language
        )
        percent_desired = self._get_threshold(
            self.config.SINGULAR_CHARS_PERCENT_DESIRED, ref_language
        )

        ratio = round((num_singular_chars / num_word_chars) * 100, 1)

        if ratio <= percent_desired:
            return 10.0
        elif ratio >= percent_bad:
            ratio = min(ratio, percent_max)
            return self._scale(ratio, percent_max, percent_bad, 0.0, 5.0)
        elif ratio >= percent_semibad:
            return self._scale(ratio, percent_bad, percent_semibad, 5.0, 7.0)
        else:
            return self._scale(ratio, percent_semibad, percent_desired, 7.0, 10.0)
