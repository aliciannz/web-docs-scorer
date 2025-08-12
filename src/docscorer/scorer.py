import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

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


class DocumentScorer:
    def __init__(self, config: Optional[ScorerConfiguration] = None):
        self.config = config if config else ScorerConfiguration()
        self.benchmark_config = self.config.benchmark_config
        self.lang_code_conversion = self.config.lang_code_conversion
        self.lang_families_config = self.config.lang_families_config
        self.interpolation_functions_dir = self.config.interpolation_functions_dir
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

    ## MAIN SCORING FUNCTION

    def score_text(
        self,
        ref_lang: str,
        lang_segments: List[str],
        scores_lang: Optional[List[float]],
        document_text: str,
        script_sys: str,
        id: str,
        raw_score: float,
    ) -> float | List[float]:

        condensed_data = [
            (
                len(re.findall(self.config.word_pattern, segment)),
                len(re.findall(self.config.punctuation_pattern, segment)),
                len(re.findall(self.config.singular_chars_pattern, segment)),
                len(re.findall(self.config.numbers_pattern, segment)),
            )
            for segment in document_text.split("\n")
        ]

        word_chars = [x[0] for x in condensed_data]
        punctuation_chars = [x[1] for x in condensed_data]
        singular_chars = [x[2] for x in condensed_data]
        numbers = [x[3] for x in condensed_data]
        ref_lang = ref_lang[0] if isinstance(ref_lang, list) else ref_lang

        num_singular_chars = sum(singular_chars)
        num_word_chars = sum(word_chars)
        num_punctuation_chars = sum(punctuation_chars)
        num_numbers = sum(numbers)
        language_score = self.lang_scorer.score(
            ref_lang, lang_segments, scores_lang, word_chars, id
        )
        punctuation_score = self.punct_scorer.score(
            ref_lang, num_punctuation_chars, num_word_chars
        )
        singular_chars_score = self.chars_scorer.score(
            ref_lang, num_singular_chars, num_word_chars
        )
        numbers_score = self.numbers_scorer.score(ref_lang, num_numbers, num_word_chars)
        repeated_score = self.repeated_scorer.score(ref_lang, document_text)
        url_score = self.url_scorer.score(ref_lang, document_text, word_chars)
        long_segments_scores = self.long_text_scorer.score(
            ref_lang, lang_segments, word_chars
        )
        informativeness_score = self.info_scorer.score(document_text, script_sys)

        score = (
            language_score * 0.8
            + long_segments_scores[0] / 10
            + long_segments_scores[1] / 10
        ) * custom_mean(
            [
                url_score / 10,
                punctuation_score / 10,
                singular_chars_score / 10,
                numbers_score / 10,
                repeated_score / 10,
                informativeness_score / 10,
            ]
        )

        if raw_score:
            return round(score, 1) if score <= 10 else 10

        final_score: List[Any] = [
            round(score, 1) if score <= 10 else 10,
            round(language_score, 1),
            round(url_score, 1),
            round(punctuation_score, 1),
            round(singular_chars_score, 1),
            round(numbers_score, 1),
            round(repeated_score, 1),
            round(long_segments_scores[0], 1),
            round(long_segments_scores[1], 1),
            round(informativeness_score, 1),
        ]

        if self.config.text_in_output:
            final_score.append(document_text.replace("\n", "\\n"))
        return final_score

    def score_document(
        self, document: Dict[str, Any], raw_score: bool = False
    ) -> float | List[float]:
        return self.score_text(
            ref_lang=f"{document['document_lang']}_{document['script']}",
            lang_segments=document["langs"],
            scores_lang=document["scores"] if "scores" in document else None,
            document_text=document["text"],
            script_sys=document["script"],
            id=document["id"],
            raw_score=raw_score,
        )

    def score_directory(self, input_path: Path, output_path: Path) -> None:
        for json_f in os.listdir(input_path):
            if json_f.endswith(".jsonl"):
                if not re.match("[a-z]{3}_[A-Z][a-z]{3}$", json_f.split(".")[0]):
                    logging.error(
                        f"{json_f} is not a well formed named → eng_Latn.jsonl"
                    )
                    continue
                documents = os.path.join(input_path, json_f)
                file_name = os.path.splitext(os.path.basename(json_f))[0]
                writing_path = os.path.join(output_path, f"{file_name}.csv")
                df = pd.DataFrame(columns=["score"])

                lang_script = json_f.split(".")[0].split("_")
                language = lang_script[0].lower()
                script = lang_script[1].lower()
                script = (
                    self.config.EQUIVALENT_SCRIPTS[script]
                    if script in self.config.EQUIVALENT_SCRIPTS
                    else script
                )

                i = 0
                logging.info(f"Processing: {file_name}")
                with open(documents, "r", encoding="utf-8") as file:
                    n_lines = sum(1 for _ in file)
                    logging.info(f"{file_name} - {n_lines} documents")
                with open(documents, "r", encoding="utf-8") as file:
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

                        document["langs"] = langs_fixed
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
