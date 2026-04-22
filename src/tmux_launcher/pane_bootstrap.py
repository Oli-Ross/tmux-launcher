from __future__ import annotations

import os
import subprocess
from collections.abc import Sequence


def main(argv: Sequence[str] | None = None) -> int:
    command = argv[0] if argv else None
    shell = os.environ.get("SHELL") or "/bin/sh"

    if command not in {None, ""}:
        subprocess.run([shell, "-lc", command], check=False)

    os.execvp(shell, [shell, "-i"])
    raise AssertionError("os.execvp should not return")
