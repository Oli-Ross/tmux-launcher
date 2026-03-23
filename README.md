# tmux-launcher

`tmux-launcher` allows you to predefine `tmux` presets and launch them.

Each workspace specification can include:
- Pane layout
- Working dir (per pane)
- Initial command to run in each pane
- Window title

Presets are stored in a TOML config file and launching is done interactively via `fzf` or via passing a CLI arg.

## AI disclaimer 

The entire repository, except for this Readme, is generated from `codex`.

## Prerequisites

- `uv`
- `tmux`
- `fzf` for interactive preset selection (uses `fzf-tmux`)

## Installation

Clone this repository and install dependencies:

```bash
uv sync
```

For convenient integration, I recommend adding a shortcut to your `tmux.conf` to launch the preset selector:

```
bind-key -n C-n run-shell 'uv --directory /path/to/tmux-launcher run tmux-launcher'
```

## Quick Start

Run the provided sample config (inside `tmux`):

```bash
uv run tmux-launcher -c examples/sample-config.toml 
```

This opens `fzf-tmux` to pick a preset, and adds the corresponding window to the current tmux session.

To launch a specific preset directly, use `-p`:

```bash
uv run tmux-launcher -c examples/sample-config.toml -p dev
```

## Configuration

Configuration files are looked up in this order:

1. Passed directly via `-c/--config`
2. `~/.tmux-launch.toml`
3. Config path set via `TMUX_LAUNCH_CONFIG` environment variable

Configuration details for pane layout are documented in [docs/config.md](docs/config.md), an example is in [examples/sample-config.toml](examples/sample-config.toml).
