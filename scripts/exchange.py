"""Portable local exchange setup and Docker management; no secret values are printed."""

from __future__ import annotations

import argparse
import base64
import os
import secrets
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def setup(path: Path) -> None:
    if not path.is_file():
        raise ValueError("Create the project .env from .env.example first")
    text = path.read_text(encoding="utf-8")
    values = dict(
        line.split("=", 1)
        for line in text.splitlines()
        if "=" in line and not line.lstrip().startswith("#")
    )
    generated = {
        "EXCHANGE_PORT": "8085",
        "EXCHANGE_ENCRYPTION_KEY": base64.urlsafe_b64encode(secrets.token_bytes(32)).decode(),
        "EXCHANGE_OPERATOR_TOKEN": secrets.token_urlsafe(32),
    }
    for key, value in generated.items():
        if values.get(key, "").strip().strip("\"'"):
            continue
        lines = text.splitlines()
        lines = [line for line in lines if not line.startswith(key + "=")]
        text = "\n".join(lines) + "\n" + key + "=" + value + "\n"
    path.write_text(text, encoding="utf-8", newline="\n")
    if os.name != "nt":
        path.chmod(0o600)
    print("Exchange configuration ready. Existing keys were preserved. Credentials remain in .env.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["setup", "up", "stop", "status", "logs"])
    args = parser.parse_args()
    if args.command == "setup":
        setup(ROOT / ".env")
        return
    commands = {
        "up": ["up", "--build", "-d", "--wait", "exchange"],
        "stop": ["stop", "exchange"],
        "status": ["ps", "exchange"],
        "logs": ["logs", "--tail", "60", "exchange"],
    }
    subprocess.run(["docker", "compose", *commands[args.command]], cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
