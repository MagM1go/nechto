import argparse
import logging
import sys
from pathlib import Path
from typing import Final, Any
from collections.abc import Sequence

from deskar import __version__
from deskar.config import Config, config
from deskar.main import process_catalog

CONFIG_FILE_NAME: Final[str] = "config.py"

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def create_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="deskar",
        description="pdf parser",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  deskar                              Use default input/output directories
  deskar --input ./pdfs --output ./xlsx
  deskar -i ./catalogs -o ./results
  deskar --verbose                    Enable verbose output
  deskar --dpi 200                    Use higher DPI for better OCR
""",
    )

    parser.add_argument(
        "-i", "--input",
        type=Path,
        default=None,
        metavar="DIR",
        help="Input directory containing PDF files (default: input)",
    )

    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=None,
        metavar="DIR",
        help="Output directory for Excel files (default: output)",
    )

    parser.add_argument(
        "--dpi",
        type=int,
        default=None,
        metavar="N",
        help="DPI for PDF to image conversion (default: 200, range: 72-600)",
    )

    parser.add_argument(
        "--output-filename",
        type=str,
        default=None,
        metavar="NAME",
        help="Output Excel filename (default: deskar_catalog.xlsx)",
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output",
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    return parser


def apply_cli_overrides(args: argparse.Namespace) -> Config:
    cli_overrides: dict[str, Any] = {}

    if args.input is not None:
        cli_overrides["input_dir"] = args.input

    if args.output is not None:
        cli_overrides["output_dir"] = args.output

    if args.dpi is not None:
        cli_overrides["dpi"] = args.dpi

    if args.output_filename is not None:
        cli_overrides["output_filename"] = args.output_filename

    if args.verbose:
        cli_overrides["verbose"] = True

    config.apply_overrides(cli_overrides)
    return config


def print_startup_info(cfg: Config) -> None:
    logger.info("=" * 60)
    logger.info("Deskar Catalog Parser v%s", __version__)
    logger.info("=" * 60)
    logger.info("")
    logger.info("Configuration:")
    logger.info(f"  Input directory:  {cfg.input_path}")
    logger.info(f"  Output directory: {cfg.output_path}")
    logger.info(f"  Output file:      {cfg.output_file.name}")
    logger.info(f"  DPI:              {cfg.dpi}")
    logger.info(f"  Verbose:          {cfg.verbose}")
    logger.info("")


def validate_config(cfg: Config) -> bool:
    if not cfg.input_path.exists():
        logger.error(f"Input directory not found: {cfg.input_path}")
        logger.error("Please create the directory or specify a different path with --input")
        return False

    pdf_files = cfg.get_pdf_files()
    if not pdf_files:
        logger.error(f"No PDF files found in: {cfg.input_path}")
        logger.error("Please add PDF files to the input directory")
        return False

    return True


def main(argv: Sequence[str] | None = None) -> int:
    parser = create_argument_parser()
    args = parser.parse_args(argv)

    try:
        cfg = apply_cli_overrides(args)

        if cfg.verbose:
            logging.getLogger().setLevel(logging.DEBUG)

        print_startup_info(cfg)

        if not validate_config(cfg):
            return 1

        result = process_catalog()

        logger.info("")
        logger.info("=" * 60)
        logger.info("Processing complete!")
        logger.info(f"  Total pages:    {result['total_pages']}")
        logger.info(f"  Total records:  {result['total_records']}")
        logger.info(f"  Output file:    {cfg.output_file}")

        if result["pages_with_errors"]:
            logger.warning(f"  Pages with errors: {result['pages_with_errors']}")

        return 0

    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        return 1

    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        return 1

    except KeyboardInterrupt:
        logger.info("\nOperation cancelled by user")
        return 130

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        if config.verbose:
            logger.exception("Full traceback:")
        return 1


def run() -> None:
    sys.exit(main())


if __name__ == "__main__":
    run()