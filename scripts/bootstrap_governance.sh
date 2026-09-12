#!/usr/bin/env bash
set -euo pipefail

log() { printf '[governance] %s\n' "$*"; }
fail() { printf '[governance] ERROR: %s\n' "$*" >&2; exit 1; }

if ! command -v uv >/dev/null 2>&1; then
  fail "uv is required to install/manage Spec Kit. Install uv first."
fi

if ! command -v specify >/dev/null 2>&1; then
  log "Installing Spec Kit CLI from PyPI with uv..."
  uv tool install specify-cli
fi

specify version

if [ ! -d .specify ]; then
  log "Initializing Spec Kit for Codex..."
  specify init --here --force --non-interactive --integration codex --script py
else
  log "Spec Kit artifacts already exist; preserving project governance files."
  if [ ! -d .agents/skills ]; then
    log "Installing Codex Spec Kit integration into the existing project..."
    specify integration install codex --script py --force
  fi
fi

if ! command -v rtk >/dev/null 2>&1 || ! rtk gain >/dev/null 2>&1; then
  cat >&2 <<'MSG'
Rust Token Killer (rtk-ai/rtk) is not installed or the wrong `rtk` is on PATH.
Install the official RTK from https://github.com/rtk-ai/rtk and verify `rtk gain` works.
Do not install the unrelated crates.io project with the same binary name.
MSG
  exit 1
fi

rtk --version
rtk gain >/dev/null
rtk init --codex
rtk gain || true
