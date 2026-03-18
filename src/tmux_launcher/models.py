from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

PaneSplit = Literal["horizontal", "vertical"]


@dataclass(frozen=True)
class PaneLeaf:
    cmd: str | None = None
    working_dir: Path | None = None


@dataclass(frozen=True)
class PaneGroup:
    split: PaneSplit
    children: tuple["PaneNode", ...]
    percentage: int | None = None


PaneNode = PaneLeaf | PaneGroup


@dataclass(frozen=True)
class Preset:
    name: str
    window_name: str
    cmd: str | None
    working_dir: Path
    layout: PaneNode = field(default_factory=PaneLeaf)


@dataclass(frozen=True)
class Config:
    presets: tuple[Preset, ...]

    def select_presets(self, selected_names: tuple[str, ...] | list[str]) -> tuple[Preset, ...]:
        if not selected_names:
            return self.presets

        available_names = {preset.name for preset in self.presets}
        missing = [name for name in selected_names if name not in available_names]
        if missing:
            raise ValueError(f"unknown preset(s): {', '.join(missing)}")

        selected_name_set = set(selected_names)
        return tuple(preset for preset in self.presets if preset.name in selected_name_set)
