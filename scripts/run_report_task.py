"""Run an evidence task with host-group-writable output on Unix Docker hosts."""

from __future__ import annotations

import os
import runpy
import sys
from pathlib import Path


def main() -> None:
    if os.getenv("MIJOBS_HOST_GID") and hasattr(os, "setgid"):
        os.setgid(int(os.environ["MIJOBS_HOST_GID"]))
        os.umask(0o002)
    target = Path(sys.argv[1]).resolve()
    allowed = Path("/workspace/scripts").resolve()
    if target.parent != allowed or not target.name.endswith(".py"):
        raise ValueError("Task must be a workspace report script")
    sys.argv = sys.argv[1:]
    runpy.run_path(str(target), run_name="__main__")


if __name__ == "__main__":
    main()
