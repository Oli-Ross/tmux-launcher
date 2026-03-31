from __future__ import annotations

from pathlib import Path

import pytest

from tmux_launcher.models import PaneGroup, PaneLeaf, Preset
from tmux_launcher.selector import build_fzf_command, build_fzf_input, choose_preset_interactively


class CompletedProcess:
    def __init__(self, returncode: int, stdout: str = "", stderr: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_build_fzf_input_contains_relevant_preset_columns() -> None:
    presets = [
        Preset(
            name="editor",
            window_name="edit",
            cmd="nvim some-file.txt && ls -la",
            working_dir=Path("/workspace/app"),
            layout=PaneGroup(
                split="vertical",
                children=(
                    PaneLeaf(),
                    PaneLeaf(cmd="tail -f app.log"),
                ),
            ),
        )
    ]

    assert (
        build_fzf_input(presets)
        == "editor\tedit\tworkspace/app\tnvim [] && ls []\tvsplit\n"
    )


def test_build_fzf_input_shows_blank_command_as_none() -> None:
    presets = [
        Preset(name="blank", window_name="blank", cmd="", working_dir=Path("/tmp")),
    ]

    assert build_fzf_input(presets) == "blank\tblank\t/tmp\t(none)\tsingle\n"


def test_build_fzf_command_uses_preview_window() -> None:
    command = build_fzf_command()

    assert command[0] == "fzf-tmux"
    assert "--preview" in command
    assert "--preview-window" in command
    assert "--border" in command
    assert "--margin=1" in command
    assert "--padding=1" in command
    assert "--layout=reverse" in command
    assert command[command.index("--with-nth") + 1] == "1"
    assert command[command.index("--preview-window") + 1] == "right:60%:wrap"
    assert command[command.index("--bind") + 1] == "space:accept"
    assert command[command.index("--preview") + 1].endswith(" sh {1} {2} {3} {4} {5}")


def test_choose_preset_interactively_returns_selected_name(monkeypatch: pytest.MonkeyPatch) -> None:
    presets = [
        Preset(name="editor", window_name="edit", cmd="nvim", working_dir=Path("/tmp")),
        Preset(name="shell", window_name="shell", cmd="zsh -i", working_dir=Path("/tmp")),
    ]
    calls: list[tuple[list[str], str]] = []

    def fake_run(command: list[str], *, input: str, text: bool, capture_output: bool, check: bool) -> CompletedProcess:
        calls.append((command, input))
        return CompletedProcess(returncode=0, stdout="shell\tshell\t/tmp\tzsh\n")

    monkeypatch.setattr("tmux_launcher.selector.subprocess.run", fake_run)

    assert choose_preset_interactively(presets) == "shell"
    assert calls[0][0][0] == "fzf-tmux"
    assert "editor\tedit\t/tmp\tnvim\tsingle\n" in calls[0][1]


def test_choose_preset_interactively_returns_none_on_cancel(monkeypatch: pytest.MonkeyPatch) -> None:
    presets = [Preset(name="editor", window_name="edit", cmd="nvim", working_dir=Path("/tmp"))]

    def fake_run(*_: object, **__: object) -> CompletedProcess:
        return CompletedProcess(returncode=130)

    monkeypatch.setattr("tmux_launcher.selector.subprocess.run", fake_run)

    assert choose_preset_interactively(presets) is None


def test_choose_preset_interactively_raises_on_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    presets = [Preset(name="editor", window_name="edit", cmd="nvim", working_dir=Path("/tmp"))]

    def fake_run(*_: object, **__: object) -> CompletedProcess:
        return CompletedProcess(returncode=1, stderr="boom")

    monkeypatch.setattr("tmux_launcher.selector.subprocess.run", fake_run)

    with pytest.raises(RuntimeError, match="boom"):
        choose_preset_interactively(presets)
