from __future__ import annotations

import os

import pytest

from tmux_launcher import pane_bootstrap


def test_main_runs_command_then_execs_shell(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, object]] = []

    def fake_run(command: list[str], check: bool) -> None:
        calls.append(("run", command))

    def fake_execvp(file: str, args: list[str]) -> None:
        calls.append(("execvp", (file, args)))
        raise SystemExit(0)

    monkeypatch.setenv("SHELL", "/bin/zsh")
    monkeypatch.setattr(pane_bootstrap.subprocess, "run", fake_run)
    monkeypatch.setattr(os, "execvp", fake_execvp)

    with pytest.raises(SystemExit, match="0"):
        pane_bootstrap.main(["echo hi"])

    assert calls == [
        ("run", ["/bin/zsh", "-lc", "echo hi"]),
        ("execvp", ("/bin/zsh", ["/bin/zsh", "-i"])),
    ]


def test_main_execs_shell_without_running_blank_command(monkeypatch: pytest.MonkeyPatch) -> None:
    run_called = False

    def fake_run(command: list[str], check: bool) -> None:
        nonlocal run_called
        run_called = True

    def fake_execvp(file: str, args: list[str]) -> None:
        raise SystemExit(0)

    monkeypatch.delenv("SHELL", raising=False)
    monkeypatch.setattr(pane_bootstrap.subprocess, "run", fake_run)
    monkeypatch.setattr(os, "execvp", fake_execvp)

    with pytest.raises(SystemExit, match="0"):
        pane_bootstrap.main([""])

    assert run_called is False
