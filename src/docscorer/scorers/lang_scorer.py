from typing import List

from docscorer.configuration import ScorerConfiguration
from docscorer.scorers.base_scorer import BaseScorer


class LangScorer(BaseScorer):
    def __init__(self, config: ScorerConfiguration):
        self.config = config

    def score(
        self,
        ref_language: str,
        lang_segments: List[str],
        scores_lang: List[float],
        word_chars: List[int],
        id: str,
    ) -> float:
        if scores_lang and (
            len(lang_segments) != len(scores_lang)
            or len(scores_lang) != len(word_chars)
        ):
            return 10  # Errors from unmatched scores
        menu_length = self._get_threshold(
            self.config.MENUS_AVERAGE_LENGTH, ref_language
        )
        correct_lang_chars = 0
        wrong_lang_chars = 0
        available_chars = False
        for n in range(len(lang_segments)):
            if word_chars[n] <= menu_length:
                if lang_segments[n] == ref_language:
                    available_chars = True
                continue
            elif lang_segments[n] == ref_language:
                correct_lang_chars += word_chars[n]
            elif not scores_lang or scores_lang[n] > 0.2:
                wrong_lang_chars += word_chars[n]
        if correct_lang_chars == 0:
            if not available_chars:
                print(
                    f"Doc_name: '{id}' - No available segments have been found on "
                    "the target language\n"
                    f"- Language: '{ref_language}' - Segment_languages: "
                    f"{set(lang_segments)}"
                )

            else:
                print(
                    f"Doc_name: '{id}' - "
                    "Only too short segments have been found on the target language"
                )
            return 0
        results = correct_lang_chars / (correct_lang_chars + wrong_lang_chars) * 10
        return results if results <= 10 else 10
