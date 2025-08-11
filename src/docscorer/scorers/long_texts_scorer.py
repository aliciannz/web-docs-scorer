from typing import List, Tuple

from docscorer.configuration import ScorerConfiguration
from docscorer.scorers.base_scorer import BaseScorer


class LongTextScorer(BaseScorer):
    def __init__(self, config: ScorerConfiguration):
        self.config = config

    def score(
        self, ref_language: str, lang_segments: List[str], word_chars: List[int]
    ) -> Tuple[float, float]:
        if len(word_chars) != len(lang_segments):
            lang_segments = [ref_language] * len(word_chars)
            # return (-1000, -1000)

        long_text_min = self._get_threshold(self.config.LONG_TEXT_MIN, ref_language)
        long_text_max = self._get_threshold(self.config.LONG_TEXT_MAX, ref_language)

        long_segments = []
        for n in range(len(word_chars)):
            if lang_segments[n] == ref_language and word_chars[n] > long_text_min:
                useful_chars = (
                    long_text_max if word_chars[n] > long_text_max else word_chars[n]
                )
                score = round(
                    (useful_chars - long_text_min)
                    / (long_text_max - long_text_min)
                    * 10,
                    1,
                )
                long_segments.append(score)

        n_segments = len(long_segments) if len(long_segments) <= 10 else 10
        highter_segments = [x for x in long_segments if x > 5]
        score_very_long_segments = 0.0
        if highter_segments:
            score_very_long_segments = (
                sum(highter_segments) + 0.1 * (len(highter_segments))
            ) / len(highter_segments)

        score_n_segments = n_segments / self.config.DESIRED_LONG_TEXTS * 10
        return (
            score_n_segments if score_n_segments <= 10 else 10,
            score_very_long_segments if score_very_long_segments <= 10 else 10,
        )
