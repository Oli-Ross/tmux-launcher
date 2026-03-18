from __future__ import annotations

import logging
from pathlib import Path

from tmux_launcher import cli


def test_parse_args_counts_verbose_and_quiet_flags() -> None:
    args = cli.parse_args(["-vv", "-q"])

    assert args.verbose == 2
    assert args.quiet == 1


def test_parse_args_parses_config_path() -> None:
    args = cli.parse_args(["--config", "config.toml", "--preset", "editor"])

    assert args.config == Path("config.toml")
    assert args.preset == ["editor"]


def test_parse_args_allows_missing_config() -> None:
    args = cli.parse_args([])

    assert args.config is None
    assert args.preset == []


def test_get_log_level_adjusts_from_default() -> None:
    assert cli.get_log_level(verbose=0, quiet=0) == logging.WARNING
    assert cli.get_log_level(verbose=1, quiet=0) == logging.INFO
    assert cli.get_log_level(verbose=0, quiet=1) == logging.ERROR


def test_get_log_level_is_clamped() -> None:
    assert cli.get_log_level(verbose=10, quiet=0) == logging.DEBUG
    assert cli.get_log_level(verbose=0, quiet=10) == logging.CRITICAL

def test_main_dispatches_launch_command(monkeypatch) -> None:
    handled: list[tuple[object, logging.Logger]] = []

    def fake_handle_launch(args: object, logger: logging.Logger) -> int:
        handled.append((args, logger))
        return 7

    monkeypatch.setattr(cli, "handle_launch", fake_handle_launch)

    exit_code = cli.main(["--config", "config.toml", "--preset", "two"])

    assert exit_code == 7
    assert len(handled) == 1
    assert getattr(handled[0][0], "config") == Path("config.toml")
    assert getattr(handled[0][0], "preset") == ["two"]
