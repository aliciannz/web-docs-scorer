import os
import joblib
import zstandard
import re
from docscorer.scorers.base_scorer import BaseScorer
class InformativenessScorer(BaseScorer):
    GROUPS = {
        **dict.fromkeys(["Grek", "Latn", "Cyrl", "Hang", "Jpan"], "GROUP_A"),
        **dict.fromkeys(["Deva", "Beng", "Telu", "Tibt", "Geor", "Gujr", "Khmr", "Knda", "Laoo", "Mlym", "Mymr", "Orya", "Sinh", "Taml", "Thai", "Olck"], "GROUP_B"),
        **dict.fromkeys(["Arab", "Armn", "Ethi", "Guru", "Hebr"], "GROUP_C"),
        **dict.fromkeys(["Hans", "Hant"], "GROUP_D"),
    }

    FUNCTION_FILES = {
        "GROUP_A": "function_group_a.pkl",
        "GROUP_B": "function_group_b.pkl",
        "GROUP_C": "function_group_c.pkl",
        "GROUP_D": "function_group_d.pkl",
    }

    OUTSIDERS_FIX = {
        "GROUP_A": 180_000,
        "GROUP_B": 250_000,
        "GROUP_C": 180_000,
        "GROUP_D": 75_000,
    }

    # Thresholds for score ranges
    TOLERANCE_GOOD = 10
    TOLERANCE_BAD = 20
    TOLERANCE_SEMIBAD = 15

    def __init__(self, config_files: str):
        self.cctx = zstandard.ZstdCompressor()
        self.functions = {
            group: joblib.load(os.path.join(config_files, file))
            for group, file in self.FUNCTION_FILES.items()
        }

    def _get_group(self, script_code: str) -> str:
        # Group A is the default
        return self.GROUPS.get(script_code, "GROUP_A")

    def _calculate_information_score(self, raw_weight: int, compression: float, script_code: str) -> float:
        group = self._get_group(script_code)
        raw_weight = min(raw_weight, self.OUTSIDERS_FIX[group])

        y_pred = float(self.functions[group](raw_weight))
        diff = compression - y_pred

        if abs(diff) <= self.TOLERANCE_GOOD:
            return 10.0
        if abs(diff) >= self.TOLERANCE_BAD:
            return 0.0

        # Below predicted
        if diff < 0:
            if abs(diff) <= self.TOLERANCE_SEMIBAD:
                return self._scale(compression, y_pred - self.TOLERANCE_GOOD, y_pred - self.TOLERANCE_SEMIBAD, 10, 7)
            return self._scale(compression, y_pred - self.TOLERANCE_SEMIBAD, y_pred - self.TOLERANCE_BAD, 7, 0)

        # Above predicted
        if diff <= self.TOLERANCE_SEMIBAD:
            return self._scale(compression, y_pred + self.TOLERANCE_GOOD, y_pred + self.TOLERANCE_SEMIBAD, 10, 7)
        return self._scale(compression, y_pred + self.TOLERANCE_SEMIBAD, y_pred + self.TOLERANCE_BAD, 7, 0)

    def score(self, text: str, script_code: str) -> float:
        text = re.sub(r"\d", "1", text.lower())
        compressed_weight = len(self.cctx.compress(text.encode("utf-8")))
        raw_weight = max(1, len(text.encode("utf-8")))
        compression = round((1 - compressed_weight / raw_weight) * 100, 1)
        return self._calculate_information_score(raw_weight, compression, script_code)