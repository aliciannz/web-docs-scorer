from docscorer.scorers.base_scorer import BaseScorer
from docscorer.configuration import ScorerConfiguration

class RepeatedScorer(BaseScorer):
    MAX_SCORE = 10.0
    MIN_SCORE = 0.0

    def __init__(self, config: ScorerConfiguration):
        self.config = config

    def score(self, ref_language: str, document: str) -> float:
        menu_length = self._get_threshold(self.config.MENUS_AVERAGE_LENGTH, ref_language)

        segments = [line for line in document.split("\n") if len(line) >= menu_length]
        if not segments:
            return self.MAX_SCORE

        num_duplicates = len(segments) - len(set(segments))
        repetition_ratio = num_duplicates / len(segments)
        score = (1 - repetition_ratio) * self.MAX_SCORE
        return round(score, 1)
