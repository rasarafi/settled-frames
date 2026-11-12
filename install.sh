#!/usr/bin/env bash
# Sets up what the watch-video skill needs:
#   1. a Python venv at ~/.local/share/watch-video-venv (override with WATCH_VIDEO_VENV)
#   2. unless --no-skill is given, a copy of the skill at ~/.claude/skills/watch-video
# Plugin users only need step 1:  ./install.sh --no-skill
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
venv=${WATCH_VIDEO_VENV:-$HOME/.local/share/watch-video-venv}

for bin in python3 ffmpeg ffprobe; do
  command -v "$bin" >/dev/null || { echo "missing: $bin (install it first)"; exit 1; }
done

if [ ! -x "$venv/bin/python" ]; then
  python3 -m venv "$venv"
fi
"$venv/bin/pip" install --quiet --upgrade pip
"$venv/bin/pip" install --quiet -r "$here/requirements.txt"
echo "venv ready: $venv"

if [ "${1:-}" != "--no-skill" ]; then
  dest=${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/watch-video
  if [ -e "$dest" ]; then
    echo "skill already exists at $dest - not overwriting. Remove it first to reinstall."
  else
    mkdir -p "$(dirname "$dest")"
    cp -r "$here/skills/watch-video" "$dest"
    echo "skill installed: $dest"
  fi
fi
echo "done. In Claude Code, ask: watch this video: <path or URL>"
