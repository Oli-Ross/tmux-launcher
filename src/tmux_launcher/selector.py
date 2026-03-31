from __future__ import annotations

import shlex
import subprocess
from collections.abc import Sequence

from tmux_launcher.models import PaneGroup, PaneLeaf, PaneNode, Preset


def choose_preset_interactively(presets: Sequence[Preset]) -> str | None:
    if not presets:
        raise ValueError("at least one preset is required for interactive selection")

    result = subprocess.run(
        build_fzf_command(),
        input=build_fzf_input(presets),
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode == 130:
        return None
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "fzf-tmux selection failed")

    selected_line = result.stdout.strip()
    if not selected_line:
        return None
    return selected_line.split("\t", 1)[0]


def build_fzf_command() -> list[str]:
    return [
        "fzf-tmux",
        "-p",
        "60%,60%",
        "--border",
        "--margin=1",
        "--padding=1",
        "--layout=reverse",
        "--delimiter",
        "\t",
        "--with-nth",
        "1",
        "--bind",
        "space:accept",
        "--bind",
        "ctrl-d:preview-page-down,ctrl-u:preview-page-up,ctrl-i:backward-kill-word",
        "--prompt",
        "Preset> ",
        "--preview",
        _build_preview_command(),
        "--preview-window",
        "right:60%:wrap",
    ]


def build_fzf_input(presets: Sequence[Preset]) -> str:
    return "".join(
        f"{preset.name}\t{preset.window_name}\t{_preview_path(preset.working_dir)}\t{_preview_cmd(preset.cmd)}\t{_single_line(_layout_summary(preset.layout))}\n"
        for preset in presets
    )


def _build_preview_command() -> str:
    script = (
        'printf "name: %s\\nwindow: %s\\nworking_dir: %s\\ncmd: %s\\nlayout: %s\\n" '
        '"$1" "$2" "$3" "$4" "$5"'
    )
    return "sh -c " + shlex.quote(script) + " sh {1} {2} {3} {4} {5}"


def _layout_summary(node: PaneNode) -> str:
    if isinstance(node, PaneLeaf):
        return "single"
    if node.split == "vertical":
        return "vsplit"
    return "hsplit"


def _single_line(value: str) -> str:
    return " ".join(value.split())


def _preview_path(path: object) -> str:
    parts = str(path).rstrip("/").split("/")
    if len(parts) <= 2:
        return str(path)
    return "/".join(parts[-2:])


def _preview_cmd(command: str | None) -> str:
    if command is None:
        return "(layout)"
    if command == "":
        return "(none)"
    normalized = _single_line(command)
    if len(normalized) <= 20:
        return normalized

    segments: list[str] = []
    current: list[str] = []
    for token in shlex.split(normalized, posix=True):
        if token in {"&&", "||", ";", "|"}:
            if current:
                segments.append(_preview_cmd_segment(current))
                current = []
            segments.append(token)
            continue
        current.append(token)

    if current:
        segments.append(_preview_cmd_segment(current))

    preview = " ".join(segments)
    if len(preview) <= 20:
        return preview
    return preview[:17] + "..."


def _preview_cmd_segment(tokens: list[str]) -> str:
    if len(tokens) == 1:
        return tokens[0]
    return f"{tokens[0]} []"
