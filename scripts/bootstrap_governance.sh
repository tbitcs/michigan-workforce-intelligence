#!/usr/bin/env bash
set -euo pipefail

if ! command -v specify >/dev/null 2>&1; then
  if ! command -v uv >/dev/null 2>&1; then
    echo "Spec Kit is not installed and uv is unavailable. Install uv or specify-cli first." >&2
    exit 1
  fi
  echo "Installing Spec Kit CLI..."
  uv tool install specify-cli
fi

if [ ! -d .specify ]; then
  specify init --here --force --non-interactive --integration codex --script py
else
  echo "Spec Kit artifacts already exist; preserving project governance files."
fi

if ! command -v rtk >/dev/null 2>&1; then
  cat >&2 <<'MSG'
RTK is not installed. Install Rust Token Killer from rtk-ai/rtk, then rerun:
  rtk init --codex
MSG
  exit 1
fi

rtk init --codex
rtk gain || true
