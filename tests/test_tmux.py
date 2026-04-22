from __future__ import annotations

from pathlib import Path
from typing import cast

from libtmux.pane import PaneDirection

from tmux_launcher import tmux
from tmux_launcher.config import PaneGroup, PaneLeaf, Preset
from tmux_launcher.tmux import (
    ServerLike,
    SessionLike,
    get_current_session,
    launch_session,
    spawn_preset,
    spawn_presets,
)


class FakePane:
    def __init__(self, name: str) -> None:
        self.name = name
        self.cmd_calls: list[dict[str, object]] = []
        self.split_calls: list[dict[str, object]] = []
        self.resize_calls: list[dict[str, object]] = []
        self.children: list[FakePane] = []

    def cmd(self, cmd: str, *args: object, target: str | int | None = None) -> "FakeCommandResult":
        self.cmd_calls.append({"cmd": cmd, "args": args, "target": target})
        return FakeCommandResult()

    def split(
        self,
        *,
        attach: bool,
        direction: str,
        start_directory: Path,
        shell: str | None = None,
    ) -> "FakePane":
        child = FakePane(f"{self.name}.{len(self.children) + 1}")
        self.children.append(child)
        self.split_calls.append(
            {
                "attach": attach,
                "direction": direction,
                "start_directory": start_directory,
                "shell": shell,
                "pane": child,
            }
        )
        return child

    def resize(self, *, height: str | None = None, width: str | None = None) -> "FakePane":
        self.resize_calls.append({"height": height, "width": width})
        return self


class FakeWindow:
    def __init__(self) -> None:
        self.active_pane = FakePane("root")
        self.select_calls = 0

    def select(self) -> "FakeWindow":
        self.select_calls += 1
        return self


class FakeCommandResult:
    def __init__(self, stderr: str = "") -> None:
        self.stderr = stderr


class FakeSession:
    def __init__(self, window: FakeWindow | None = None) -> None:
        self.new_window_calls: list[dict[str, object]] = []
        self.active_window = window or FakeWindow()
        self.windows: list[FakeWindow] = []

    def new_window(
        self,
        *,
        window_name: str,
        start_directory: Path,
        attach: bool,
        window_shell: str | None = None,
    ) -> FakeWindow:
        window = FakeWindow()
        self.windows.append(window)
        self.new_window_calls.append(
            {
                "window_name": window_name,
                "start_directory": start_directory,
                "attach": attach,
                "window_shell": window_shell,
            }
        )
        return window


class FakeServer:
    def __init__(self) -> None:
        self.session = FakeSession(window=FakeWindow())
        self.sessions = FakeSessions(self.session)


class FakeSessions:
    def __init__(self, session: FakeSession) -> None:
        self.session = session
        self.get_calls: list[dict[str, object]] = []

    def get(self, *, default: FakeSession | None, session_name: str) -> FakeSession | None:
        self.get_calls.append({"default": default, "session_name": session_name})
        if session_name == "dev-session":
            return self.session
        return default


def test_spawn_preset_creates_window_and_runs_default_pane_command() -> None:
    session = FakeSession()
    preset = Preset(
        name="dev",
        window_name="editor",
        cmd="nvim",
        working_dir=Path("/tmp/project with spaces"),
    )

    window = spawn_preset(cast(SessionLike, session), preset)

    assert window is session.windows[0]
    assert session.new_window_calls == [
        {
            "window_name": "editor",
            "start_directory": Path("/tmp/project with spaces"),
            "attach": False,
            "window_shell": None,
        }
    ]
    assert session.windows[0].select_calls == 1
    assert session.windows[0].active_pane.cmd_calls == [
        {
            "cmd": "respawn-pane",
            "args": (
                "-k",
                "-c/tmp/project with spaces",
                tmux._pane_shell_command("nvim"),
            ),
            "target": None,
        }
    ]


def test_spawn_preset_materializes_nested_layout() -> None:
    session = FakeSession()
    preset = Preset(
        name="stack",
        window_name="services",
        cmd="run-app",
        working_dir=Path("/workspace/app"),
        layout=PaneGroup(
            split="vertical",
            percentage=80,
            children=(
                PaneLeaf(),
                PaneGroup(
                    split="horizontal",
                    percentage=60,
                    children=(
                        PaneLeaf(cmd="tail -f app.log", working_dir=Path("/var/log/app")),
                        PaneLeaf(cmd="pytest -q"),
                    ),
                ),
            ),
        ),
    )

    spawn_preset(cast(SessionLike, session), preset)

    root_pane = session.windows[0].active_pane
    assert root_pane.cmd_calls == [
        {
            "cmd": "respawn-pane",
            "args": (
                "-k",
                "-c/workspace/app",
                tmux._pane_shell_command("run-app"),
            ),
            "target": None,
        }
    ]
    assert len(root_pane.split_calls) == 1

    nested_group_pane = cast(FakePane, root_pane.split_calls[0]["pane"])
    assert root_pane.split_calls[0] == {
        "attach": False,
        "direction": PaneDirection.Below,
        "start_directory": Path("/var/log/app"),
        "shell": None,
        "pane": nested_group_pane,
    }
    assert nested_group_pane.resize_calls == [{"height": "20%", "width": None}]
    assert nested_group_pane.cmd_calls == [
        {
            "cmd": "respawn-pane",
            "args": (
                "-k",
                "-c/var/log/app",
                tmux._pane_shell_command("tail -f app.log"),
            ),
            "target": None,
        }
    ]
    assert len(nested_group_pane.split_calls) == 1
    assert nested_group_pane.split_calls[0]["direction"] == PaneDirection.Right
    assert nested_group_pane.split_calls[0]["start_directory"] == Path("/workspace/app")
    assert nested_group_pane.split_calls[0]["shell"] is None
    second_nested_leaf = cast(FakePane, nested_group_pane.split_calls[0]["pane"])
    assert second_nested_leaf.cmd_calls == [
        {
            "cmd": "respawn-pane",
            "args": (
                "-k",
                "-c/workspace/app",
                tmux._pane_shell_command("pytest -q"),
            ),
            "target": None,
        }
    ]
    assert second_nested_leaf.resize_calls == [{"height": None, "width": "40%"}]


def test_spawn_preset_allows_blank_command() -> None:
    session = FakeSession()
    preset = Preset(
        name="blank",
        window_name="blank",
        cmd="",
        working_dir=Path("/workspace/app"),
    )

    spawn_preset(cast(SessionLike, session), preset)

    assert session.new_window_calls == [
        {
            "window_name": "blank",
            "start_directory": Path("/workspace/app"),
            "attach": False,
            "window_shell": None,
        }
    ]
    assert session.windows[0].select_calls == 1
    assert session.windows[0].active_pane.cmd_calls == []


def test_spawn_presets_creates_one_window_per_preset() -> None:
    session = FakeSession()
    presets = [
        Preset(
            name="editor",
            window_name="editor",
            cmd="nvim",
            working_dir=Path("/workspace/app"),
        ),
        Preset(
            name="shell",
            window_name="shell",
            cmd="zsh",
            working_dir=Path("/workspace/app"),
        ),
    ]

    windows = spawn_presets(cast(SessionLike, session), presets)

    assert len(windows) == 2
    assert len(session.new_window_calls) == 2
    assert [call["window_name"] for call in session.new_window_calls] == ["editor", "shell"]


def test_launch_session_adds_new_windows_to_existing_session() -> None:
    server = FakeServer()
    presets = [
        Preset(
            name="editor",
            window_name="editor",
            cmd="nvim",
            working_dir=Path("/workspace/app"),
        ),
        Preset(
            name="shell",
            window_name="shell",
            cmd="zsh",
            working_dir=Path("/workspace/app"),
        ),
    ]

    session = server.session
    windows = launch_session(cast(ServerLike, server), cast(SessionLike, session), presets)

    assert len(windows) == 2
    assert len(session.new_window_calls) == 2
    assert [call["window_name"] for call in session.new_window_calls] == ["editor", "shell"]


def test_get_current_session_resolves_active_tmux_session(monkeypatch) -> None:
    server = FakeServer()

    class CompletedProcess:
        def __init__(self) -> None:
            self.returncode = 0
            self.stdout = "dev-session\n"
            self.stderr = ""

    monkeypatch.setattr("tmux_launcher.tmux.subprocess.run", lambda *args, **kwargs: CompletedProcess())

    session = get_current_session(cast(ServerLike, server))

    assert session is server.session
    assert server.sessions.get_calls == [{"default": None, "session_name": "dev-session"}]
