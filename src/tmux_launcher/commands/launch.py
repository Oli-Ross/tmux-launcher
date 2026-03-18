from __future__ import annotations

import argparse
import logging
import os
from typing import cast
from pathlib import Path

import libtmux

from tmux_launcher.config_loader import load_config
from tmux_launcher.selector import choose_preset_interactively
from tmux_launcher.tmux import ServerLike, get_current_session, launch_session

DEFAULT_CONFIG_PATH = Path("~/.tmux-launch.toml").expanduser()


def handle_launch(args: argparse.Namespace, logger: logging.Logger) -> int:
    config_path = resolve_config_path(args)
    config = load_config(config_path)
    logger.info("Loaded %d preset(s) from %s", len(config.presets), config_path)
    selected_names = list(args.preset)
    if not selected_names:
        selected_name = choose_preset_interactively(config.presets)
        if selected_name is None:
            logger.info("Interactive preset selection cancelled")
            return 0
        selected_names = [selected_name]
        logger.info("Selected preset %s", selected_name)

    presets = config.select_presets(selected_names)
    server = cast(ServerLike, libtmux.Server())
    session = get_current_session(server)
    launch_session(
        server,
        session,
        presets,
    )
    logger.info(
        "Added %d preset window(s) to current tmux session %s",
        len(presets),
        session.name,
    )
    return 0


def resolve_config_path(args: argparse.Namespace) -> Path:
    if args.config is not None:
        return args.config.expanduser()

    if DEFAULT_CONFIG_PATH.exists():
        return DEFAULT_CONFIG_PATH

    env_path = os.environ.get("TMUX_LAUNCH_CONFIG")
    if env_path:
        return Path(env_path).expanduser()

    raise ValueError(
        "no config file found; use --config, create ~/.tmux-launch.toml, or set TMUX_LAUNCH_CONFIG"
    )
