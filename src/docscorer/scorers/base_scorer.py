from typing import Any


class BaseScorer:
    def _get_threshold(self, table: Any, language: str) -> Any:
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
