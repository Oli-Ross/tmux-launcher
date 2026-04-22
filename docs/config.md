# Config Guide

This project uses TOML config files with a top-level `presets` list.

Each preset maps to one tmux window.

## Minimal Preset

```toml
[[presets]]
name = "dev"
window_name = "editor"
cmd = "python -m http.server"
working_dir = "~/projects/demo"
```

Required fields:
- `name`: internal preset name used by `--preset` and interactive selection
- `window_name`: tmux window title
- `working_dir`: default working directory

Command rules:
- `cmd` is required for single-pane presets unless you intentionally set it to `""` to start with no command
- `cmd` is optional for split layouts if every pane leaf defines its own `cmd`
- when present, `cmd` acts as the default command inherited by pane leaves
- `cmd = ""` is allowed on presets or pane leaves and means "start an idle shell in this pane"

## Layouts

Presets can optionally define a recursive pane layout.

```toml
[[presets]]
name = "stack"
window_name = "services"
cmd = "sh"
working_dir = "~/projects/demo"

[presets.layout]
split = "vertical"
percentage = 80

[[presets.layout.children]]
cmd = "python -m http.server"

[[presets.layout.children]]
split = "horizontal"
percentage = 60

[[presets.layout.children.children]]
cmd = "ls"

[[presets.layout.children.children]]
cmd = "sh"
```

Layout fields:
- `split`: `"vertical"` or `"horizontal"`
- `children`: child panes or nested split groups
- `percentage`: optional integer from `1` to `99`

Rules:
- `percentage` is only valid when a split group has exactly 2 children
- `percentage` defines the size of the first child
- the second child gets the remaining percentage

Semantics:
- `split = "vertical"` stacks panes top-to-bottom
- `split = "horizontal"` places panes side-by-side

## Inheritance

Pane leaves inherit `cmd` and `working_dir` from the parent preset unless they override them.

Examples:

```toml
[[presets]]
name = "editor"
window_name = "editor"
cmd = "python -m http.server"
working_dir = "~/projects/demo"

[presets.layout]
split = "horizontal"
percentage = 75

[[presets.layout.children]]
cmd = "python -m http.server 9000"

[[presets.layout.children]]
cmd = "sh"
```

In that example:
- the first child keeps the preset working directory and overrides only `cmd`
- the second child keeps both the preset working directory and the preset defaults except for its own `cmd`

If every leaf defines a command, the preset-level `cmd` can be omitted:

```toml
[[presets]]
name = "editor"
window_name = "editor"
working_dir = "~/projects/demo"

[presets.layout]
split = "horizontal"
percentage = 75

[[presets.layout.children]]
cmd = "python -m http.server"

[[presets.layout.children]]
cmd = "sh"
```

Environment note:
- `working_dir` values should point to directories that exist on the machine where you run the CLI.
- non-empty `cmd` values are started after the pane layout is created, then control returns to an interactive shell in that pane after the command exits.
- `cmd = ""` starts the pane without running any initial command.
- The tool does not manage `PATH`, install dependencies, or adapt commands to your shell setup.

## Launch Behavior

The CLI launches windows into the current tmux session.

Examples:

```bash
uv run tmux-launcher
uv run tmux-launcher -c examples/sample-config.toml --preset dev
```

Config lookup order:

1. `-c/--config`
2. `~/.tmux-launch.toml`
3. `TMUX_LAUNCH_CONFIG`

If you omit `--preset`, the CLI uses `fzf-tmux` to select a preset interactively. The selector shows:
- the preset name in the list
- a preview pane with window name, working directory, command, and a layout summary

Explicit `--preset` values bypass interactive selection.
There is no mode that launches every preset automatically.

## Examples

Runnable example configs [sample-config.toml](examples/sample-config.toml).
