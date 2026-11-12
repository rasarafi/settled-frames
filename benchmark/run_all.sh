#!/bin/bash
# Run every tool and setting on one video. Skips runs that already finished.
# Usage: run_all.sh <key> <video.mp4> <runs-dir>
# Needs: SETTLED_PY (python of the settled-frames venv), CRV_PY (python of a venv with claude-real-video
# installed), CV_DIR (a clone of bradautomates/claude-video). See benchmark/README.md.
set -u
k=$1; f=$(realpath "$2"); runs=$(realpath -m "$3"); here=$(cd "$(dirname "$0")" && pwd)
: "${SETTLED_PY:?}" "${CRV_PY:?}" "${CV_DIR:?}"
export CRV_NO_MEMORY=1   # stop crv from indexing the video into ~/.crv
SETTLED="$SETTLED_PY -I $here/../skills/watch-video/scripts/prepare.py"
CRV="$CRV_PY -I -m claude_real_video.cli"
CV="python3 -I $CV_DIR/skills/watch/scripts/watch.py"
run() { # name, command...
  local name=$1; shift; local d=$runs/$name
  [ -f "$d/time.txt" ] && { echo "skip $name"; return; }
  mkdir -p "$d"; local t0=$(date +%s.%N)
  "$@" > "$d/stdout.txt" 2>&1; local rc=$?
  echo "rc=$rc secs=$(echo "$(date +%s.%N) - $t0" | bc)" > "$d/time.txt"; echo "$name $(cat "$d/time.txt")"
}
o() { echo "$runs/$k-$1/out"; }
run $k-settled-default $SETTLED "$f" --out $(o settled-default) --lang en
run $k-settled-nofine  $SETTLED "$f" --out $(o settled-nofine) --lang en --fine 0
run $k-crv-default     $CRV "$f" -o $(o crv-default) --no-transcribe
run $k-crv-tuned       $CRV "$f" -o $(o crv-tuned) --no-transcribe --adaptive --text-anchors --frame-width 1920 --max-frames 600
run $k-crv-max         $CRV "$f" -o $(o crv-max) --no-transcribe --adaptive --text-anchors --frame-width 1920 --max-frames 600 --scene 0.1 --dedup-threshold 2 --fps-floor 0.5
run $k-crv-fine        $CRV "$f" -o $(o crv-fine) --no-transcribe --adaptive --text-anchors --frame-width 1920 --max-frames 600 --scene 0.1 --dedup-threshold 0.5 --fps-floor 0.5
run $k-cv-default      $CV "$f" --engine local --no-whisper --out-dir $(o cv-default)
run $k-cv-tuned        $CV "$f" --engine local --no-whisper --detail token-burner --resolution 1920 --out-dir $(o cv-tuned)
run $k-cv-2fps         $CV "$f" --engine local --no-whisper --detail token-burner --resolution 1920 --fps 2 --out-dir $(o cv-2fps)
echo "ALL DONE $k"
