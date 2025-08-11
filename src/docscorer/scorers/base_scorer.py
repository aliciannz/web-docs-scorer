from abc import ABC, abstractmethod
from typing import Dict


class BaseScorer(ABC):
    @abstractmethod
    def score(self):
        pass

    def _get_threshold(self, table: Dict[str, float], language: str) -> float:
        """Fetch a language-specific threshold, falling back to 'standard'."""
        return table.get(language, table["standard"])

    @staticmethod
    def _scale(
        value: float,
        min_value: float,
        max_value: float,
        min_score: float,
        max_score: float,
    ) -> float:
        """Scale a value linearly into a score range."""
        if min_value == max_value:
            return 0.0
        return (value - min_value) / (max_value - min_value) * (
            max_score - min_score
        ) + min_score
