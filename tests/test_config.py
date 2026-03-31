from __future__ import annotations

import textwrap
import tomllib
from pathlib import Path

import pytest

from tmux_launcher.config import Config, PaneGroup, PaneLeaf, Preset, load_config, parse_config


def test_parse_config_builds_presets_and_layout_tree() -> None:
    raw = tomllib.loads(
        textwrap.dedent(
            """
            [[presets]]
            name = "dev"
            window_name = "editor"
            cmd = "nvim"
            working_dir = "~/projects/demo"

            [[presets]]
            name = "stack"
            window_name = "services"
            cmd = "echo root"
            working_dir = "/tmp"

            [presets.layout]
            split = "vertical"
            percentage = 80

            [[presets.layout.children]]
            cmd = "server"
            working_dir = "/srv/app"

            [[presets.layout.children]]
            split = "horizontal"
            percentage = 60

            [[presets.layout.children.children]]
            cmd = "logs"

            [[presets.layout.children.children]]
            cmd = "shell"
            """
        )
    )

    config = parse_config(raw)

    assert isinstance(config, Config)
    assert len(config.presets) == 2
    assert config.presets[0] == Preset(
        name="dev",
        window_name="editor",
        cmd="nvim",
        working_dir=Path("~/projects/demo").expanduser(),
        layout=PaneLeaf(),
    )

    layout = config.presets[1].layout
    assert isinstance(layout, PaneGroup)
    assert layout.split == "vertical"
    assert layout.percentage == 80
    assert len(layout.children) == 2
    assert layout.children[0] == PaneLeaf(cmd="server", working_dir=Path("/srv/app"))
    assert isinstance(layout.children[1], PaneGroup)
    assert layout.children[1].percentage == 60


def test_load_config_reads_from_disk(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        textwrap.dedent(
            """
            [[presets]]
            name = "dev"
            window_name = "editor"
            cmd = "nvim"
            working_dir = "/tmp"
            """
        )
    )

    config = load_config(config_path)

    assert config.presets == (
        Preset(
            name="dev",
            window_name="editor",
            cmd="nvim",
            working_dir=Path("/tmp"),
            layout=PaneLeaf(),
        ),
    )


def test_parse_config_rejects_missing_required_fields() -> None:
    raw = tomllib.loads(
        textwrap.dedent(
            """
            [[presets]]
            name = "dev"
            window_name = "editor"
            working_dir = "/tmp"
            """
        )
    )

    with pytest.raises(
        ValueError,
        match="invalid preset 'dev': missing cmd; add preset.cmd or define cmd on every pane leaf in the layout",
    ):
        parse_config(raw)


def test_parse_config_allows_missing_preset_cmd_when_layout_leaves_define_commands() -> None:
    raw = tomllib.loads(
        textwrap.dedent(
            """
            [[presets]]
            name = "dev"
            window_name = "editor"
            working_dir = "/tmp"

            [presets.layout]
            split = "horizontal"
            percentage = 70

            [[presets.layout.children]]
            cmd = "nvim"

            [[presets.layout.children]]
            cmd = "htop"
            """
        )
    )

    config = parse_config(raw)

    assert config.presets[0].cmd is None


def test_parse_config_allows_blank_preset_cmd_for_single_pane() -> None:
    raw = tomllib.loads(
        textwrap.dedent(
            """
            [[presets]]
            name = "blank"
            window_name = "blank"
            cmd = ""
            working_dir = "/tmp"
            """
        )
    )

    config = parse_config(raw)

    assert config.presets[0].cmd == ""


def test_parse_config_allows_blank_leaf_cmd() -> None:
    raw = tomllib.loads(
        textwrap.dedent(
            """
            [[presets]]
            name = "blank"
            window_name = "blank"
            working_dir = "/tmp"

            [presets.layout]
            split = "horizontal"
            percentage = 50

            [[presets.layout.children]]
            cmd = ""

            [[presets.layout.children]]
            cmd = "htop"
            """
        )
    )

    config = parse_config(raw)
    layout = config.presets[0].layout

    assert isinstance(layout, PaneGroup)
    assert layout.children[0] == PaneLeaf(cmd="", working_dir=None)


def test_parse_config_rejects_invalid_split_value() -> None:
    raw = tomllib.loads(
        textwrap.dedent(
            """
            [[presets]]
            name = "dev"
            window_name = "editor"
            cmd = "nvim"
            working_dir = "/tmp"

            [presets.layout]
            split = "diagonal"
            children = []
            """
        )
    )

    with pytest.raises(ValueError, match="split must be 'horizontal' or 'vertical'"):
        parse_config(raw)


def test_parse_config_rejects_invalid_percentage_range() -> None:
    raw = tomllib.loads(
        textwrap.dedent(
            """
            [[presets]]
            name = "dev"
            window_name = "editor"
            cmd = "nvim"
            working_dir = "/tmp"

            [presets.layout]
            split = "vertical"
            percentage = 100

            [[presets.layout.children]]
            cmd = "shell"

            [[presets.layout.children]]
            cmd = "logs"
            """
        )
    )

    with pytest.raises(ValueError, match="percentage must be between 1 and 99"):
        parse_config(raw)


def test_parse_config_rejects_percentage_without_two_children() -> None:
    raw = tomllib.loads(
        textwrap.dedent(
            """
            [[presets]]
            name = "dev"
            window_name = "editor"
            cmd = "nvim"
            working_dir = "/tmp"

            [presets.layout]
            split = "vertical"
            percentage = 80

            [[presets.layout.children]]
            cmd = "shell"
            """
        )
    )

    with pytest.raises(ValueError, match="layout.percentage requires exactly two child panes"):
        parse_config(raw)


def test_load_config_wraps_toml_decode_errors(tmp_path: Path) -> None:
    config_path = tmp_path / "broken.toml"
    config_path.write_text("[[presets]\nname = 'broken'\n")

    with pytest.raises(ValueError, match="invalid TOML in .*broken.toml"):
        load_config(config_path)


def test_config_select_presets_returns_all_when_no_names_are_given() -> None:
    config = Config(
        presets=(
            Preset(name="editor", window_name="editor", cmd="nvim", working_dir=Path("/tmp")),
            Preset(name="shell", window_name="shell", cmd="zsh", working_dir=Path("/tmp")),
        )
    )

    assert config.select_presets([]) == config.presets


def test_config_select_presets_preserves_config_order() -> None:
    config = Config(
        presets=(
            Preset(name="editor", window_name="editor", cmd="nvim", working_dir=Path("/tmp")),
            Preset(name="shell", window_name="shell", cmd="zsh", working_dir=Path("/tmp")),
            Preset(name="logs", window_name="logs", cmd="tail -f app.log", working_dir=Path("/tmp")),
        )
    )

    selected = config.select_presets(["logs", "editor"])

    assert [preset.name for preset in selected] == ["editor", "logs"]


def test_config_select_presets_rejects_unknown_names() -> None:
    config = Config(
        presets=(Preset(name="editor", window_name="editor", cmd="nvim", working_dir=Path("/tmp")),)
    )

    with pytest.raises(ValueError, match="unknown preset\\(s\\): missing"):
        config.select_presets(["missing"])
