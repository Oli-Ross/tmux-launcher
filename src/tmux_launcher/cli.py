from __future__ import annotations

import argparse
import logging
from collections.abc import Sequence
from pathlib import Path

from tmux_launcher.commands.launch import handle_launch

LOGGER_NAME = "tmux_launcher"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tmux-launcher",
        description="tmux-launcher CLI",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase verbosity. Repeat to increase it further.",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="count",
        default=0,
        help="Reduce output. Repeat to make the CLI quieter.",
    )
    parser.add_argument(
        "-c",
        "--config",
        type=Path,
        help="Path to a TOML config file containing presets.",
    )
    parser.add_argument(
        "-p",
        "--preset",
        action="append",
        default=[],
        help="Preset name to launch non-interactively. Repeat to select multiple presets.",
    )
    return parser


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    return build_parser().parse_args(argv)


def get_log_level(verbose: int, quiet: int) -> int:
    level = logging.WARNING - (10 * verbose) + (10 * quiet)
    return min(logging.CRITICAL, max(logging.DEBUG, level))


def configure_logging(args: argparse.Namespace) -> logging.Logger:
    level = get_log_level(args.verbose, args.quiet)
    logging.basicConfig(level=level, format="%(levelname)s %(name)s: %(message)s")
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(level)
    return logger


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    logger = configure_logging(args)
    logger.debug("Parsed args: %s", args)
    return handle_launch(args, logger)
