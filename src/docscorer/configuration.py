import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Union

import pandas as pd

from docscorer.utils import average, join_utf_blocks


@dataclass
class ScorerConfiguration:
    def __init__(self, args: Optional[Dict[str, Any]] = None):
        base_dir = Path(__file__).resolve().parent

        def get_path(
            default: Union[str, Path],
            arg_key: str,
            args: Optional[Dict[str, Any]] = None,
        ) -> Path:
            if args is not None and arg_key in args and args[arg_key] is not None:
                return Path(args[arg_key])
            else:
                return Path(default)

        self.benchmark_config = get_path(
            base_dir / "configurations/language_adaption/medians_language.csv",
            "--benchmark_config",
        )
        self.info_score_config = get_path(
            base_dir / "configurations/interpolation_functions/", "--info_score_config"
        )
        self.lang_code_conversion = get_path(
            base_dir / "configurations/language_adaption/lang_code_conversion.json",
            "--lang_code_conversion",
        )
        self.lang_families_config = get_path(
            base_dir / "configurations/language_adaption/lang_families_script.csv",
            "--lang_families_config",
        )

        self.text_in_output = (
            args.get("--text_in_output") if args is not None else False
        )
        self.only_final_score = (
            args.get("--only_final_score") if args is not None else False
        )

        for attr in [
            "benchmark_config",
            "info_score_config",
            "lang_code_conversion",
            "lang_families_config",
        ]:
            path = getattr(self, attr)
            if not path.exists():
                raise FileNotFoundError(f"Required config file not found: {path}")

        with open(self.lang_code_conversion, "r", encoding="utf-8") as file:
            self.CODE_2_to_3_CONVERSION = json.load(file)

        ## LANGUAGE ADAPTATION DATA
        df_lang_adaption = pd.read_csv(self.benchmark_config)
        LANGUAGES = df_lang_adaption.language_3_chars.to_list()

        MODELED_LANGS_NUMBERS = {
            f"{line.language_3_chars}_{line.script}": round(line.numbers_score, 1)
            for _, line in df_lang_adaption.iterrows()
        }
        MODELED_LANGS_PUNCTUATION = {
            f"{line.language_3_chars}_{line.script}": round(line.punctuation_score, 1)
            for _, line in df_lang_adaption.iterrows()
        }
        MODELED_LANGS_SINGULAR_CHARS = {
            f"{line.language_3_chars}_{line.script}": round(
                line.singular_chars_score, 1
            )
            for _, line in df_lang_adaption.iterrows()
        }

        ## LANGUAGES_SCRIPTS
        df_families = pd.read_csv(self.lang_families_config)
        df_lang_no_data = df_families[~df_families.language_3_chars.isin(LANGUAGES)]
        df_lang_data = df_families[df_families.language_3_chars.isin(LANGUAGES)]
        df_lang_adaption = pd.merge(
            df_lang_data,
            df_lang_adaption,
            on=["language_3_chars", "script"],
            how="inner",
        )  # language families + medians in the same df

        for _, line in df_lang_no_data.iterrows():
            familiars = df_lang_adaption[
                (df_lang_adaption.genus == line.genus)
                & (df_lang_adaption.script == line.script)
            ]
            if familiars.empty:
                familiars = df_lang_adaption[
                    (df_lang_adaption.family == line.family)
                    & (df_lang_adaption.script == line.script)
                ]
            if not familiars.empty:
                MODELED_LANGS_NUMBERS[f"{line.language_3_chars}_{line.script}"] = round(
                    average(familiars.numbers_score.to_list()), 2
                )
                MODELED_LANGS_PUNCTUATION[f"{line.language_3_chars}_{line.script}"] = (
                    round(average(familiars.punctuation_score.to_list()), 2)
                )
                MODELED_LANGS_SINGULAR_CHARS[
                    f"{line.language_3_chars}_{line.script}"
                ] = round(average(familiars.singular_chars_score.to_list()), 2)

        del df_lang_adaption
        del df_families

        # equivalent script systems

        self.EQUIVALENT_SCRIPTS = {"hant": "hans"}

        ## REFERENCE RATIO VALUES FOR SPANISH
        # Current values in the provided csv
        ref_punctuation = MODELED_LANGS_PUNCTUATION["spa_Latn"]
        ref_numbers = MODELED_LANGS_NUMBERS["spa_Latn"]
        ref_singular_chars = MODELED_LANGS_SINGULAR_CHARS["spa_Latn"]

        # Menu
        menu_length = 25

        # Punctuation
        punct_max = 25
        punct_bad = [13, 0.5]
        punct_semibad = [9, 0.3]
        punct_desired_max = 2.5
        punct_desired_min = 0.9

        # Singular chars
        singular_chars_max = 10
        singular_chars_bad = 6
        singular_chars_semibad = 2
        singular_chars_desired = 1

        # Numbers
        numbers_max = 30
        numbers_bad = 15
        numbers_semibad = 10
        numbers_desired = 1

        # Long text
        long_text_min = 250
        long_text_max = 1000

        ## MENUS ADAPTATION
        self.MENUS_AVERAGE_LENGTH = {
            lang: round(ref_punctuation * menu_length / val)
            for lang, val in MODELED_LANGS_PUNCTUATION.items()
        }
        self.MENUS_AVERAGE_LENGTH["standard"] = average(
            list(self.MENUS_AVERAGE_LENGTH.values())
        )

        ## PUNCTUATION SCORING
        self.PUNCTUATION_PERCENT_MAX = {
            lang: (
                round(val * punct_max / ref_punctuation, 1)
                if val * punct_max / ref_punctuation < 100
                else 100.0
            )
            for lang, val in MODELED_LANGS_PUNCTUATION.items()
        }
        self.PUNCTUATION_PERCENT_MAX["standard"] = average(
            list(self.PUNCTUATION_PERCENT_MAX.values())
        )

        self.PUNCTUATION_PERCENT_BAD = {
            lang: (
                round(val * punct_bad[0] / ref_punctuation, 1),
                round(val * punct_bad[1] / ref_punctuation, 1),
            )
            for lang, val in MODELED_LANGS_PUNCTUATION.items()
        }
        self.PUNCTUATION_PERCENT_BAD["standard"] = (
            average([x[0] for x in list(self.PUNCTUATION_PERCENT_BAD.values())]),
            average([x[1] for x in list(self.PUNCTUATION_PERCENT_BAD.values())]),
        )

        self.PUNCTUATION_PERCENT_SEMIBAD = {
            lang: (
                round(val * punct_semibad[0] / ref_punctuation, 1),
                round(val * punct_semibad[1] / ref_punctuation, 1),
            )
            for lang, val in MODELED_LANGS_PUNCTUATION.items()
        }
        self.PUNCTUATION_PERCENT_SEMIBAD["standard"] = (
            average([x[0] for x in list(self.PUNCTUATION_PERCENT_SEMIBAD.values())]),
            average([x[1] for x in list(self.PUNCTUATION_PERCENT_SEMIBAD.values())]),
        )

        self.PUNCTUATION_PERCENT_DESIRED_MAX = {
            lang: round(val * punct_desired_max / ref_punctuation, 1)
            for lang, val in MODELED_LANGS_PUNCTUATION.items()
        }
        self.PUNCTUATION_PERCENT_DESIRED_MAX["standard"] = average(
            list(self.PUNCTUATION_PERCENT_DESIRED_MAX.values())
        )

        self.PUNCTUATION_PERCENT_DESIRED_MIN = {
            lang: round(val * punct_desired_min / ref_punctuation, 1)
            for lang, val in MODELED_LANGS_PUNCTUATION.items()
        }
        self.PUNCTUATION_PERCENT_DESIRED_MIN["standard"] = average(
            list(self.PUNCTUATION_PERCENT_DESIRED_MIN.values())
        )

        ## SINGULAR CHARS SCORING
        self.SINGULAR_CHARS_PERCENT_MAX = {
            lang: (
                round(val * singular_chars_max / ref_singular_chars, 1)
                if val * singular_chars_max / ref_singular_chars < 100
                else 100.0
            )
            for lang, val in MODELED_LANGS_SINGULAR_CHARS.items()
        }
        self.SINGULAR_CHARS_PERCENT_MAX["standard"] = average(
            list(self.SINGULAR_CHARS_PERCENT_MAX.values())
        )

        self.SINGULAR_CHARS_PERCENT_BAD = {
            lang: round(val * singular_chars_bad / ref_singular_chars, 1)
            for lang, val in MODELED_LANGS_SINGULAR_CHARS.items()
        }
        self.SINGULAR_CHARS_PERCENT_BAD["standard"] = average(
            list(self.SINGULAR_CHARS_PERCENT_BAD.values())
        )

        self.SINGULAR_CHARS_PERCENT_SEMIBAD = {
            lang: round(val * singular_chars_semibad / ref_singular_chars, 1)
            for lang, val in MODELED_LANGS_SINGULAR_CHARS.items()
        }
        self.SINGULAR_CHARS_PERCENT_SEMIBAD["standard"] = average(
            list(self.SINGULAR_CHARS_PERCENT_SEMIBAD.values())
        )

        self.SINGULAR_CHARS_PERCENT_DESIRED = {
            lang: round(val * singular_chars_desired / ref_singular_chars, 1)
            for lang, val in MODELED_LANGS_SINGULAR_CHARS.items()
        }
        self.SINGULAR_CHARS_PERCENT_DESIRED["standard"] = average(
            list(self.SINGULAR_CHARS_PERCENT_DESIRED.values())
        )

        ## NUMBERS SCORING
        self.NUMBERS_PERCENT_MAX = {
            lang: (
                round(val * numbers_max / ref_numbers, 1)
                if val * numbers_max / ref_numbers < 100
                else 100.0
            )
            for lang, val in MODELED_LANGS_NUMBERS.items()
        }
        self.NUMBERS_PERCENT_MAX["standard"] = average(
            list(self.NUMBERS_PERCENT_MAX.values())
        )

        self.NUMBERS_PERCENT_BAD = {
            lang: (
                round(val * numbers_bad / ref_numbers, 1)
                if val * numbers_max / ref_numbers < 100
                else 100.0
            )
            for lang, val in MODELED_LANGS_NUMBERS.items()
        }
        self.NUMBERS_PERCENT_BAD["standard"] = average(
            list(self.NUMBERS_PERCENT_BAD.values())
        )

        self.NUMBERS_PERCENT_SEMIBAD = {
            lang: round(val * numbers_semibad / ref_numbers, 1)
            for lang, val in MODELED_LANGS_NUMBERS.items()
        }
        self.NUMBERS_PERCENT_SEMIBAD["standard"] = average(
            list(self.NUMBERS_PERCENT_SEMIBAD.values())
        )

        self.NUMBERS_PERCENT_DESIRED = {
            lang: round(val * numbers_desired / ref_numbers, 1)
            for lang, val in MODELED_LANGS_NUMBERS.items()
        }
        self.NUMBERS_PERCENT_DESIRED["standard"] = average(
            list(self.NUMBERS_PERCENT_DESIRED.values())
        )

        ## LONG SEGMENTS SCORING
        self.LONG_TEXT_MAX = {
            lang: round(ref_punctuation * long_text_max / val)
            for lang, val in MODELED_LANGS_PUNCTUATION.items()
        }
        self.LONG_TEXT_MAX["standard"] = average(list(self.LONG_TEXT_MAX.values()))

        self.LONG_TEXT_MIN = {
            lang: round(ref_punctuation * long_text_min / val)
            for lang, val in MODELED_LANGS_PUNCTUATION.items()
        }
        self.LONG_TEXT_MIN["standard"] = average(list(self.LONG_TEXT_MIN.values()))

        # Number of long texts that means a 10 score
        self.DESIRED_LONG_TEXTS = 10

        ## CHARS DETECTION
        # Regex unicode codes for char-type count
        SINGULAR_CHARS = [
            "0023-0026",
            "002A-002B",
            "002F-002F",
            "003C-003E",
            "0040-0040",
            "005C-005C",
            "007C-007C",
            "007E-007E",
            "00A2-00B3",
            "00B8-00BE",
            "00D7-00D7",
            "00F7-00F7",
            "02B0-0385",
            "0483-0489",
            "0559-055F",
            "2010-2D00",
            "2DE0-2E52",
            "10000-1FFFF",
            "A670-A67F",
            "3200-33FF",
        ]
        PUNCTUATION_CHARS = [
            "0021-0022",
            "0027-0029",
            "002C-002E",
            "003A-003B",
            "003F-003F",
            "005B-005B",
            "005D-005D",
            "0060-0060",
            "00A1-00A1",
            "00B4-00B5",
            "00B7-00B7",
            "00BF-00BF",
            "0589-05C7",
            "0600-061F",
            "066A-066D",
            "06D4-06ED",
            "0700-070F",
            "1360-1368",
            "1800-180A",
            "1AB0-1AFF",
            "1C78-1C7F",
            "1CC0-1CC7",
            "1FBD-1FC1",
            "1FCD-1FCF",
            "1FDD-1FDF",
            "1FED-1FEF",
            "1FFD-2027",
            "3000-303F",
            "4DC0-4DFF",
            "A6F0-A6F7",
            "FE10-FE6F",
        ]
        NUMBERS = [
            "0030-0039",
            "0660-0669",
            "06F0-06F9",
            "0964-096F",
            "09F2-09F9",
            "0B66-0B77",
            "0BE6-0BFA",
            "0C66-0C6F",
            "0C78-0C7E",
            "0CE6-0CEF",
            "0D66-0D79",
            "0DE6-0DEF",
            "0E50-0E5B",
            "0EC0-0ED9",
            "1040-1049",
            "1090-1099",
            "1369-137C",
            "17E0-17E9",
            "1810-1819",
            "19D0-19DA",
            "1A80-1A99",
            "1B50-1B59",
            "1C40-1C49",
            "1C50-1C59",
            "A830-A839",
            "A8D0-A8D9",
            "AA50-AA59",
        ]
        SPACES = ["0000-0020", "007F-00A0", "2B7E-2B7E", "008A-008A", "0088-0088"]

        self.numbers_pattern = join_utf_blocks(NUMBERS)
        self.singular_chars_pattern = join_utf_blocks(SINGULAR_CHARS)
        self.punctuation_pattern = join_utf_blocks(PUNCTUATION_CHARS)
        self.word_pattern = join_utf_blocks(
            SINGULAR_CHARS + PUNCTUATION_CHARS + NUMBERS + SPACES, inverse=True
        )
