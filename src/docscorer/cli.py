"""
Document Scoring Tool

Usage:
  cli.py --input=<input_path> [--output=<output_path>] [--benchmark_config=<path>] [--info_score_config=<path>] [--lang_code_conversion=<path>] [--lang_families_config=<path>] [--text_in_output] [--only_final_score]
  cli.py (-h | --help)
  cli.py --version

Options:
  --input=<input_path>               Path to input directory with .jsonl files
  --output=<output_path>             Path to save output .csv files [default: <input_path>/document_scores]
  --benchmark_config=<path>          Path to benchmark CSV
  --info_score_config=<path>         Path to informativeness config dir
  --lang_code_conversion=<path>      Path to lang_code_conversion.json
  --lang_families_config=<path>      Path to lang families CSV
  --text_in_output                   Include original text in output
  --only_final_score                 Only include final score in output
  -h --help                          Show this screen
  --version                          Show version
"""
import logging
import sys
from docopt import docopt
from pathlib import Path
from docscorer.configuration import Configuration
from docscorer.scorer import DocumentScorer

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        stream=sys.stdout
    )

def main():
    setup_logging()
    args = docopt(__doc__, version='DocumentScorer v1.0')

    input_path = Path(args['--input'])
    if not input_path.exists():
        logging.error(f"Input path does not exist: {input_path}")
        sys.exit(1)

    output_path = Path(args.get('--output') or input_path / "document_scores")
    output_path.mkdir(parents=True, exist_ok=True)

    try:
        config = Configuration(args)
    except FileNotFoundError as e:
        logging.error(str(e))
        sys.exit(1)

    scorer = DocumentScorer(config)
    scorer.score_directory(input_path, output_path)
    logging.info("Scoring completed successfully.")

if __name__ == "__main__":
    main()