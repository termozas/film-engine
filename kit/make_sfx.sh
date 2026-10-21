#!/usr/bin/env bash
# Soft interface sounds, made from filtered noise (no sample files, no licences to track):
#   kit/make_sfx.sh [out_dir=public/sfx]
# click.mp3 for mouse presses, key1-3.mp3 for key presses (three variants so typing does not sound looped).
# The film plays them quietly on the exact moments the capture logged. To use your own sounds, replace these files
# (CC0 packs such as Kenney's UI Audio work well); set "sfx": false in film.json to turn them off.
set -euo pipefail
OUT="${1:-public/sfx}"; mkdir -p "$OUT"
mk() {   # mk <file> <dur> <highpass> <lowpass> <decay> <thump_hz> <thump_gain> <noise_gain>
  ffmpeg -v error -y \
    -f lavfi -i "anoisesrc=d=$2:c=white:a=$8:seed=$RANDOM" \
    -f lavfi -i "sine=f=$6:d=$2" \
    -filter_complex "[0]highpass=f=$3,lowpass=f=$4,afade=t=out:st=0.001:d=$5:curve=exp[n];[1]volume=$7,afade=t=out:st=0:d=$2:curve=exp[b];[n][b]amix=inputs=2:normalize=0,afade=t=in:d=0.0015,alimiter=limit=0.6" \
    -ar 48000 -ac 1 -c:a libmp3lame -b:a 128k "$OUT/$1"
}
mk click.mp3 0.07 1800 7500 0.030 190 0.35 0.9
mk key1.mp3  0.05 2000 6500 0.016 140 0.18 0.6
mk key2.mp3  0.05 2400 7000 0.014 160 0.15 0.55
mk key3.mp3  0.05 1700 6000 0.018 130 0.20 0.6
echo "wrote $OUT/click.mp3 and key1-3.mp3"
