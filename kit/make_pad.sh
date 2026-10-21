#!/usr/bin/env bash
# A quiet synth pad for under the narration (the film plays it at about -18 dB and fades it in and out).
#   kit/make_pad.sh [seconds=180] [out=public/pad.mp3]
# Swap in any licensed track instead: put it in public/ and set "music" in film.json.
set -euo pipefail
D="${1:-180}"; OUT="${2:-public/pad.mp3}"
mkdir -p "$(dirname "$OUT")"
ffmpeg -v error -y \
  -f lavfi -i "sine=f=146.83:d=$D" -f lavfi -i "sine=f=220.00:d=$D" -f lavfi -i "sine=f=277.18:d=$D" -f lavfi -i "sine=f=329.63:d=$D" \
  -filter_complex "[0][1][2][3]amix=inputs=4:normalize=1,tremolo=f=0.15:d=0.35,lowpass=f=900,aecho=0.8:0.7:420|780:0.25|0.18,volume=0.9,afade=t=in:d=3,afade=t=out:st=$(( D - 4 )):d=4,aformat=channel_layouts=stereo" \
  -ar 48000 -c:a libmp3lame -b:a 128k "$OUT"
echo "wrote $OUT ($D s)"
