from __future__ import annotations

import argparse
import logging
from pathlib import Path

import pytest

from tmux_launcher.commands import launch as launch_command
from tmux_launcher.models import Config, Preset


def test_handle_launch_uses_interactive_selection(monkeypatch: pytest.MonkeyPatch) -> None:
    config = Config(
        presets=(
            Preset(name="editor", window_name="editor", cmd="nvim", working_dir=Path("/tmp")),
            Preset(name="shell", window_name="shell", cmd="zsh", working_dir=Path("/tmp")),
        )
    )
    launched: list[tuple[object, object, tuple[Preset, ...]]] = []
    fake_session = type("Session", (), {"name": "shell"})()

    monkeypatch.setattr(launch_command, "resolve_config_path", lambda _: Path("config.toml"))
    monkeypatch.setattr(launch_command, "load_config", lambda _: config)
    monkeypatch.setattr(launch_command, "choose_preset_interactively", lambda presets: "shell")
    monkeypatch.setattr(launch_command.libtmux, "Server", lambda: object())
    monkeypatch.setattr(launch_command, "get_current_session", lambda server: fake_session)
    monkeypatch.setattr(
        launch_command,
        "launch_session",
        lambda server, session, presets: launched.append((server, session, tuple(presets))),
    )

    args = argparse.Namespace(
        config=Path("config.toml"),
        preset=[],
    )

    exit_code = launch_command.handle_launch(args, logging.getLogger("test"))

    assert exit_code == 0
    assert [preset.name for preset in launched[0][2]] == ["shell"]
    assert launched[0][1] is fake_session


def test_handle_launch_returns_zero_on_interactive_cancel(monkeypatch: pytest.MonkeyPatch) -> None:
    config = Config(
        presets=(Preset(name="editor", window_name="editor", cmd="nvim", working_dir=Path("/tmp")),)
    )
    launch_called = False

    monkeypatch.setattr(launch_command, "resolve_config_path", lambda _: Path("config.toml"))
    monkeypatch.setattr(launch_command, "load_config", lambda _: config)
    monkeypatch.setattr(launch_command, "choose_preset_interactively", lambda presets: None)
    monkeypatch.setattr(launch_command.libtmux, "Server", lambda: object())

    def fail_launch(*args: object, **kwargs: object) -> None:
        nonlocal launch_called
        launch_called = True

    monkeypatch.setattr(launch_command, "launch_session", fail_launch)

    args = argparse.Namespace(
        config=Path("config.toml"),
        preset=[],
    )

    exit_code = launch_command.handle_launch(args, logging.getLogger("test"))

    assert exit_code == 0
    assert launch_called is False


def test_handle_launch_uses_explicit_presets_without_interactive_selection(monkeypatch: pytest.MonkeyPatch) -> None:
    config = Config(
        presets=(
            Preset(name="editor", window_name="editor", cmd="nvim", working_dir=Path("/tmp")),
            Preset(name="shell", window_name="shell", cmd="zsh", working_dir=Path("/tmp")),
        )
    )
    interactive_called = False
    launched: list[tuple[str, ...]] = []

    monkeypatch.setattr(launch_command, "resolve_config_path", lambda _: Path("config.toml"))
    monkeypatch.setattr(launch_command, "load_config", lambda _: config)

    def fail_interactive(*args: object, **kwargs: object) -> None:
        nonlocal interactive_called
        interactive_called = True

    monkeypatch.setattr(launch_command, "choose_preset_interactively", fail_interactive)
    monkeypatch.setattr(launch_command.libtmux, "Server", lambda: object())
    monkeypatch.setattr(launch_command, "get_current_session", lambda server: type("Session", (), {"name": "shell"})())
    monkeypatch.setattr(
        launch_command,
        "launch_session",
        lambda server, session, presets: launched.append(tuple(preset.name for preset in presets)),
    )

    args = argparse.Namespace(
        config=Path("config.toml"),
        preset=["shell"],
    )

    exit_code = launch_command.handle_launch(args, logging.getLogger("test"))

    assert exit_code == 0
    assert interactive_called is False
    assert launched == [("shell",)]


def test_resolve_config_path_prefers_cli_argument() -> None:
    args = argparse.Namespace(config=Path("cli.toml"))

    assert launch_command.resolve_config_path(args) == Path("cli.toml")


def test_resolve_config_path_uses_default_file_before_env(monkeypatch: pytest.MonkeyPatch) -> None:
    args = argparse.Namespace(config=None)
    default_path = Path("/tmp/default.toml")
    monkeypatch.setenv("TMUX_LAUNCH_CONFIG", "/tmp/from-env.toml")
    monkeypatch.setattr(launch_command, "DEFAULT_CONFIG_PATH", default_path)
    monkeypatch.setattr(Path, "exists", lambda self: self == default_path)

    assert launch_command.resolve_config_path(args) == default_path


def test_resolve_config_path_uses_env_when_default_file_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    args = argparse.Namespace(config=None)
    default_path = Path("/tmp/default.toml")
    monkeypatch.setenv("TMUX_LAUNCH_CONFIG", "/tmp/from-env.toml")
    monkeypatch.setattr(launch_command, "DEFAULT_CONFIG_PATH", default_path)
    monkeypatch.setattr(Path, "exists", lambda self: False)

    assert launch_command.resolve_config_path(args) == Path("/tmp/from-env.toml")


def test_resolve_config_path_raises_when_no_source_available(monkeypatch: pytest.MonkeyPatch) -> None:
    args = argparse.Namespace(config=None)
    default_path = Path("/tmp/default.toml")
    monkeypatch.delenv("TMUX_LAUNCH_CONFIG", raising=False)
    monkeypatch.setattr(launch_command, "DEFAULT_CONFIG_PATH", default_path)
    monkeypatch.setattr(Path, "exists", lambda self: False)

    with pytest.raises(
        ValueError,
        match="no config file found; use --config, create ~/.tmux-launch.toml, or set TMUX_LAUNCH_CONFIG",
    ):
        launch_command.resolve_config_path(args)
