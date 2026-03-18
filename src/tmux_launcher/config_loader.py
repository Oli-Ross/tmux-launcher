from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import tomllib

from tmux_launcher.models import Config, PaneGroup, PaneLeaf, PaneNode, PaneSplit, Preset


def load_config(path: Path | str) -> Config:
    config_path = Path(path)
    try:
        with config_path.open("rb") as file:
            data = tomllib.load(file)
    except tomllib.TOMLDecodeError as exc:
        raise ValueError(f"invalid TOML in {config_path}: {exc}") from exc
    return parse_config(data)


def parse_config(data: dict[str, Any]) -> Config:
    raw_presets = _expect_list(data, "presets")
    presets = tuple(parse_preset(item) for item in raw_presets)
    return Config(presets=presets)


def parse_preset(data: dict[str, Any]) -> Preset:
    _expect_dict(data, "preset")
    preset_name = _optional_str(data, "name") or "<unknown>"
    try:
        name = _expect_str(data, "name")
        layout = parse_layout(data.get("layout"))
        cmd = _optional_str(data, "cmd")
        _ensure_preset_has_commands(name, cmd, layout)
        return Preset(
            name=name,
            window_name=_expect_str(data, "window_name"),
            cmd=cmd,
            working_dir=Path(_expect_str(data, "working_dir")).expanduser(),
            layout=layout,
        )
    except ValueError as exc:
        raise ValueError(f"invalid preset '{preset_name}': {exc}") from exc


def parse_layout(data: Any) -> PaneNode:
    if data is None:
        return PaneLeaf()

    _expect_dict(data, "layout")
    if "split" in data:
        split = _expect_split(data, "split")
        percentage = _optional_percentage(data, "percentage")
        raw_children = _expect_list(data, "children")
        children = tuple(parse_layout(child) for child in raw_children)
        if not children:
            raise ValueError("layout.children must contain at least one pane")
        if percentage is not None and len(children) != 2:
            raise ValueError("layout.percentage requires exactly two child panes")
        return PaneGroup(split=split, children=children, percentage=percentage)

    cmd = _optional_str(data, "cmd")
    working_dir_value = _optional_str(data, "working_dir")
    working_dir = Path(working_dir_value).expanduser() if working_dir_value else None
    return PaneLeaf(cmd=cmd, working_dir=working_dir)


def _expect_dict(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{context} must be a table")
    return value


def _expect_list(data: dict[str, Any], key: str) -> list[dict[str, Any]]:
    value = data.get(key)
    if not isinstance(value, list):
        raise ValueError(f"{key} must be a list of tables")
    for item in value:
        if not isinstance(item, dict):
            raise ValueError(f"{key} must be a list of tables")
    return value


def _expect_str(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str):
        raise ValueError(f"{key} must be a string")
    return value


def _optional_str(data: dict[str, Any], key: str) -> str | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{key} must be a string")
    return value


def _expect_split(data: dict[str, Any], key: str) -> PaneSplit:
    value = _expect_str(data, key)
    if value not in {"horizontal", "vertical"}:
        raise ValueError(f"{key} must be 'horizontal' or 'vertical'")
    return cast(PaneSplit, value)


def _optional_percentage(data: dict[str, Any], key: str) -> int | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, int):
        raise ValueError(f"{key} must be an integer")
    if value < 1 or value > 99:
        raise ValueError(f"{key} must be between 1 and 99")
    return value


def _ensure_preset_has_commands(name: str, cmd: str | None, layout: PaneNode) -> None:
    if cmd is not None:
        return
    if _all_leaves_define_cmd(layout):
        return
    raise ValueError(
        "missing cmd; add preset.cmd or define cmd on every pane leaf in the layout"
    )


def _all_leaves_define_cmd(node: PaneNode) -> bool:
    if isinstance(node, PaneLeaf):
        return node.cmd is not None
    return all(_all_leaves_define_cmd(child) for child in node.children)
