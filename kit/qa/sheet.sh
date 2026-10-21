#!/usr/bin/env bash
# Contact sheet: one frame every N seconds, tiled, so a whole clip or film can be checked in one image.
#   kit/qa/sheet.sh <video.mp4> <out.png> [every_seconds=1] [columns=5] [tile_width=576]
# Check: nothing private on screen, the cursor is visible before each click, zooms land on what is narrated,
# no frozen or blank stretches, captions and source lines readable.
set -euo pipefail
IN="${1:?usage: sheet.sh <video> <out.png> [every_s] [cols] [width]}"; OUT="${2:?}"; EV="${3:-1}"; C="${4:-5}"; W="${5:-576}"
D=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$IN")
R=$(python3 -c "import math;print(max(1, math.ceil($D/$EV/$C)))")
mkdir -p "$(dirname "$OUT")"
ffmpeg -v error -y -i "$IN" -vf "fps=1/$EV,scale=$W:-1,tile=${C}x${R}:padding=4" -frames:v 1 "$OUT"
echo "wrote $OUT (${D%.*} s, one frame every $EV s)"
