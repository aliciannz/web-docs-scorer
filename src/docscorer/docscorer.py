import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from docscorer.configuration import ScorerConfiguration
from docscorer.scorers.chars_scorer import CharsScorer
from docscorer.scorers.informativeness_scorer import InformativenessScorer
from docscorer.scorers.lang_scorer import LangScorer
from docscorer.scorers.long_texts_scorer import LongTextScorer
from docscorer.scorers.numbers_scorer import NumsScorer
from docscorer.scorers.punct_scorer import PunctScorer
from docscorer.scorers.repeated_scorer import RepeatedScorer
from docscorer.scorers.url_scorer import URLScorer
from docscorer.utils import custom_mean


@dataclass
class ScoreResult:
    """Holds all individual scores for a document."""

    language: float
    punctuation: float
    singular_chars: float
    numbers: float
    repeated: float
    url: float
    informativeness: float
    long_segments: Tuple[float, float]  # [short_score, long_score]


class DocumentScorer:
    def __init__(self, config: Optional[ScorerConfiguration] = None):
        self.config = config if config else ScorerConfiguration()
        self.benchmark_config = self.config.benchmark_config
        self.lang_code_conversion = self.config.lang_code_conversion
        self.lang_families_config = self.config.lang_families_config
        self.info_scorer = InformativenessScorer(
            self.config.info_score_config, self.config.interpolation_functions_dir
        )
        self.punct_scorer = PunctScorer(self.config)
        self.url_scorer = URLScorer(self.config)
        self.numbers_scorer = NumsScorer(self.config)
        self.chars_scorer = CharsScorer(self.config)
        self.lang_scorer = LangScorer(self.config)
        self.long_text_scorer = LongTextScorer(self.config)
        self.repeated_scorer = RepeatedScorer(self.config)

    def _extract_features(self, document_text: str) -> dict[str, list[int]]:
        """Extract counts of words, punctuation, sing. chars, and numbers per line."""
        features = [
            (
                len(self.config.word_pattern.findall(segment)),
                len(self.config.punctuation_pattern.findall(segment)),
                len(self.config.singular_chars_pattern.findall(segment)),
                len(self.config.numbers_pattern.findall(segment)),
            )
            for segment in document_text.split("\n")
        ]
        return {
            "word_chars": [f[0] for f in features],
            "punctuation_chars": [f[1] for f in features],
            "singular_chars": [f[2] for f in features],
            "numbers": [f[3] for f in features],
        }

    def _compute_scores(
        self,
        ref_lang: str,
        lang_segments: list[str],
        scores_lang: list[float] | None,
        document_text: str,
        script_sys: str,
        doc_id: str,
        features: dict[str, list[int]],
    ) -> ScoreResult:
        """Compute all scorer outputs and return structured results."""
        num_word_chars = sum(features["word_chars"])
        num_punctuation_chars = sum(features["punctuation_chars"])
        num_singular_chars = sum(features["singular_chars"])
        num_numbers = sum(features["numbers"])

        return ScoreResult(
            language=self.lang_scorer.score(
                ref_lang, lang_segments, scores_lang, features["word_chars"], doc_id
            ),
            punctuation=self.punct_scorer.score(
                ref_lang, num_punctuation_chars, num_word_chars
            ),
            singular_chars=self.chars_scorer.score(
                ref_lang, num_singular_chars, num_word_chars
            ),
            numbers=self.numbers_scorer.score(ref_lang, num_numbers, num_word_chars),
            repeated=self.repeated_scorer.score(ref_lang, document_text),
            url=self.url_scorer.score(ref_lang, document_text, features["word_chars"]),
            long_segments=self.long_text_scorer.score(
                ref_lang, lang_segments, features["word_chars"]
            ),
            informativeness=self.info_scorer.score(document_text, script_sys),
        )

    def _aggregate_scores(self, scores: ScoreResult) -> float:
        """Aggregate individual scores into a single overall score."""
        score = (
            scores.language * 0.8
            + scores.long_segments[0] / 10
            + scores.long_segments[1] / 10
        ) * custom_mean(
            [
                scores.url / 10,
                scores.punctuation / 10,
                scores.singular_chars / 10,
                scores.numbers / 10,
                scores.repeated / 10,
                scores.informativeness / 10,
            ]
        )
        return min(round(score, 1), 10.0)

    def _format_output(
        self,
        overall_score: float,
        scores: ScoreResult,
        document_text: str,
        raw_score: bool,
    ) -> float | List[float | str]:
        """Format the output depending on configuration."""
        if raw_score:
            return overall_score

        final_score: list[float | str] = [
            overall_score,
            round(scores.language, 1),
            round(scores.url, 1),
            round(scores.punctuation, 1),
            round(scores.singular_chars, 1),
            round(scores.numbers, 1),
            round(scores.repeated, 1),
            round(scores.long_segments[0], 1),
            round(scores.long_segments[1], 1),
            round(scores.informativeness, 1),
        ]

        if self.config.text_in_output:
            final_score.append(document_text.replace("\n", "\\n"))

        return final_score

    def score_text(
        self,
        ref_lang: str,
        lang_segments: List[str],
        scores_lang: List[float] | None,
        document_text: str,
        script_sys: str,
        doc_id: str,
        raw_score: bool,
    ) -> float | List[float | str]:
        ref_lang = ref_lang[0] if isinstance(ref_lang, list) else ref_lang
        features = self._extract_features(document_text)
        scores = self._compute_scores(
            ref_lang,
            lang_segments,
            scores_lang,
            document_text,
            script_sys,
            doc_id,
            features,
        )
        overall_score = self._aggregate_scores(scores)
        return self._format_output(overall_score, scores, document_text, raw_score)

    def score_document(
        self, document: Dict[str, Any], raw_score: bool = False
    ) -> float | List[float | str]:
        return self.score_text(
            ref_lang=f"{document['document_lang']}_{document['script']}",
            lang_segments=document["langs"],
            scores_lang=document["scores"] if "scores" in document else None,
            document_text=document["text"],
            script_sys=document["script"],
            doc_id=document["id"],
            raw_score=raw_score,
        )

    def score_directory(self, input_path: Path, output_path: Path) -> None:
        for documents_file in input_path.iterdir():
            documents_filename = documents_file.stem

            if documents_file.suffix == ".jsonl":
                if not re.match(
                    "[a-z]{3}_[A-Z][a-z]{3}$", documents_filename.split(".")[0]
                ):
                    logging.error(
                        f"{documents_file} is not a well formed named → eng_Latn.jsonl"
                    )
                    continue

                writing_path = output_path / f"{documents_filename}.csv"
                df = pd.DataFrame(columns=["score"])

                lang, script = documents_filename.split("_")
                language = lang.lower()
                script = script.lower()
                script = self.config.EQUIVALENT_SCRIPTS.get(script, script)

                i = 0
                logging.info(f"Processing: {documents_file}")
                with open(documents_file, "r", encoding="utf-8") as file:
                    n_lines = sum(1 for _ in file)
                    logging.info(f"{documents_filename} - {n_lines} documents")
                with open(documents_file, "r", encoding="utf-8") as file:
                    for document_file in file:
                        document = json.loads(document_file)
                        document["document_lang"] = language
                        document["script"] = script
                        langs_fixed = []
                        for x in document["langs"]:
                            x = x.lower()
                            # Script added if "langs" includes
                            # language codes w/o script code
                            if re.match("[a-z]{3}$", x):
                                langs_fixed.append(f"{x}_{script}")
                            elif re.match("[a-z]{3}_[a-z]{4}$", x):
                                # Fix for very similar scripts or scripts that
                                # we want to be intended as the same, like Hans - Hant
                                segm_lang_script = x.split("_")
                                segm_script = (
                                    self.config.EQUIVALENT_SCRIPTS[segm_lang_script[1]]
                                    if segm_lang_script[1]
                                    in self.config.EQUIVALENT_SCRIPTS
                                    else segm_lang_script[1]
                                )
                                langs_fixed.append(
                                    f"{segm_lang_script[0]}_{segm_script}"
                                )
                            else:
                                langs_fixed.append(x)

                        document["langs"] = ["eng_latn"]
                        document_score = self.score_document(document=document)
                        docid = document["id"]
                        df.loc[docid] = [document_score]

                        i += 1
                        if i % 10000 == 0:
                            logging.info(f"{document['document_lang']} - {i}/{n_lines}")

                df["wds_score"] = df.score.apply(lambda x: x[0])
                if not self.config.only_final_score:
                    df["language_score"] = df.score.apply(lambda x: x[1])
                    df["url_score"] = df.score.apply(lambda x: x[2])
                    df["punctuation_score"] = df.score.apply(lambda x: x[3])
                    df["singular_chars_score"] = df.score.apply(lambda x: x[4])
                    df["numbers_score"] = df.score.apply(lambda x: x[5])
                    df["repeated_score"] = df.score.apply(lambda x: x[6])
                    df["n_long_segments_score"] = df.score.apply(lambda x: x[7])
                    df["great_segment_score"] = df.score.apply(lambda x: x[8])
                    df["informativeness_score"] = df.score.apply(lambda x: x[9])
                if self.config.text_in_output:
                    df["text"] = df.score.apply(lambda x: x[10])
                df.drop(columns=["score"], inplace=True)
                df.to_csv(writing_path)
                logging.info(f"Saved results in '{writing_path}'")
