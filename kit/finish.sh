#!/usr/bin/env bash
# Finish a Remotion render: loudness to -16 LUFS (true peak -1.5 dB) for the master, plus a smaller web copy.
#   kit/finish.sh out/<film>/raw.mp4 out/<film>/<film>-v1.mp4
# Writes <master>.mp4 (same picture, 1920x1200) and <master>-web.mp4 (1440x900, crf 25). Never overwrites a file.
set -euo pipefail
IN="${1:?usage: finish.sh <render.mp4> <master.mp4>}"; OUT="${2:?usage: finish.sh <render.mp4> <master.mp4>}"
WEB="${OUT%.mp4}-web.mp4"
for f in "$OUT" "$WEB"; do [ -e "$f" ] && { echo "exists: $f (pick a new version name; finished files are never overwritten)"; exit 1; }; done
mkdir -p "$(dirname "$OUT")"
ffmpeg -v error -y -i "$IN" -c:v copy -af loudnorm=I=-16:TP=-1.5 -c:a aac -b:a 192k -ar 48000 -movflags +faststart "$OUT"
ffmpeg -v error -y -i "$OUT" -vf "scale=1440:900:flags=lanczos" -c:v libx264 -crf 25 -preset slow -pix_fmt yuv420p \
  -c:a aac -b:a 128k -movflags +faststart "$WEB"
for f in "$OUT" "$WEB"; do
  ffprobe -v error -show_entries format=duration,size:stream=codec_name,width,height,r_frame_rate -of compact "$f"
done
# integrated loudness of the master (aim: about -16 LUFS)
ffmpeg -nostats -i "$OUT" -af ebur128 -f null - 2>&1 | grep -E "^\s+I:" | tail -1 | sed 's/^ */loudness: /'
