
from pathlib import Path
class Configuration:
    def __init__(self, args: dict):
        base_dir = Path(__file__).resolve().parent
        def get_path(default, arg_key):
            return Path(args.get(arg_key) or default)

        self.benchmark_config = get_path(base_dir / "configurations/language_adaption/medians_language.csv", "--benchmark_config")
        self.info_score_config = get_path(base_dir / "configurations/interpolation_functions/", "--info_score_config")
        self.lang_code_conversion = get_path(base_dir / "configurations/language_adaption/lang_code_conversion.json", "--lang_code_conversion")
        self.lang_families_config = get_path(base_dir / "configurations/language_adaption/lang_families_script.csv", "--lang_families_config")

        self.text_in_output = args.get("--text_in_output", False)
        self.only_final_score = args.get("--only_final_score", False)

        for attr in ['benchmark_config', 'info_score_config', 'lang_code_conversion', 'lang_families_config']:
            path = getattr(self, attr)
            if not path.exists():
                raise FileNotFoundError(f"Required config file not found: {path}")