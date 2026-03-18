from __future__ import annotations

import subprocess
from collections.abc import Iterable
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

from tmux_launcher.models import PaneGroup, PaneLeaf, PaneNode, Preset

if TYPE_CHECKING:
    from libtmux.server import Server
    from libtmux.pane import Pane, PaneDirection
    from libtmux.session import Session
    from libtmux.window import Window


class PaneLike(Protocol):
    def send_keys(self, cmd: str) -> None: ...

    def split(
        self,
        *,
        attach: bool,
        direction: object,
        start_directory: Path,
    ) -> "PaneLike": ...

    def resize(self, *, height: str | None = None, width: str | None = None) -> "PaneLike": ...


class WindowLike(Protocol):
    @property
    def active_pane(self) -> PaneLike | None: ...


class SessionLike(Protocol):
    name: str | None

    @property
    def active_window(self) -> WindowLike: ...

    def new_window(
        self,
        *,
        window_name: str,
        start_directory: Path,
        attach: bool,
    ) -> WindowLike: ...


class SessionCollectionLike(Protocol):
    def get(self, *, default: object, session_name: str) -> SessionLike | None: ...


class ServerLike(Protocol):
    sessions: SessionCollectionLike


def spawn_presets(session: SessionLike, presets: Iterable[Preset]) -> list[WindowLike]:
    return [spawn_preset(session, preset) for preset in presets]


def get_current_session(server: ServerLike) -> SessionLike:
    result = subprocess.run(
        ["tmux", "display-message", "-p", "#S"],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "failed to resolve current tmux session")

    session_name = result.stdout.strip()
    if not session_name:
        raise RuntimeError("failed to resolve current tmux session")

    session = server.sessions.get(default=None, session_name=session_name)
    if session is None:
        raise RuntimeError(f"current tmux session not found: {session_name}")
    return session


def launch_session(
    server: ServerLike,
    session: SessionLike,
    presets: Iterable[Preset],
) -> list[WindowLike]:
    preset_list = list(presets)
    if not preset_list:
        raise ValueError("at least one preset is required to launch a session")
    return spawn_presets(session, preset_list)


def spawn_preset(session: SessionLike, preset: Preset) -> WindowLike:
    window = session.new_window(
        window_name=preset.window_name,
        start_directory=_pane_start_directory(preset.layout, preset),
        attach=True,
    )
    _spawn_node(_require_active_pane(window), preset.layout, preset)
    return window


def _spawn_node(pane: PaneLike, node: PaneNode, preset: Preset) -> None:
    if isinstance(node, PaneLeaf):
        _configure_pane(pane, node, preset)
        return

    anchor, *siblings = node.children
    _spawn_node(pane, anchor, preset)
    for sibling in siblings:
        sibling_pane = pane.split(
            attach=False,
            direction=_pane_direction(node),
            start_directory=_pane_start_directory(sibling, preset),
        )
        _apply_split_percentage(sibling_pane, node)
        _spawn_node(sibling_pane, sibling, preset)


def _configure_pane(pane: PaneLike, leaf: PaneLeaf, preset: Preset) -> None:
    command = _pane_command(leaf, preset)
    if command:
        pane.send_keys(command)


def _pane_command(node: PaneNode, preset: Preset) -> str:
    if isinstance(node, PaneLeaf) and node.cmd is not None:
        return node.cmd
    if preset.cmd is not None:
        return preset.cmd
    raise RuntimeError(f"preset '{preset.name}' has no command for this pane")


def _pane_working_dir(node: PaneNode, preset: Preset) -> Path:
    if isinstance(node, PaneLeaf) and node.working_dir is not None:
        return node.working_dir
    return preset.working_dir


def _pane_direction(node: PaneGroup) -> PaneDirection:
    from libtmux.pane import PaneDirection

    if node.split == "vertical":
        return PaneDirection.Below
    return PaneDirection.Right


def _apply_split_percentage(pane: PaneLike, node: PaneGroup) -> None:
    if node.percentage is None:
        return

    sibling_percentage = 100 - node.percentage
    if node.split == "vertical":
        pane.resize(height=f"{sibling_percentage}%")
        return
    pane.resize(width=f"{sibling_percentage}%")


def _require_active_pane(window: WindowLike) -> PaneLike:
    pane = window.active_pane
    if pane is None:
        raise RuntimeError("tmux window has no active pane")
    return pane


def _pane_start_directory(node: PaneNode, preset: Preset) -> Path:
    if isinstance(node, PaneLeaf):
        return _pane_working_dir(node, preset)
    return _pane_start_directory(node.children[0], preset)
