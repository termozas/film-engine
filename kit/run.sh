#!/usr/bin/env bash
# The whole chain for one film: lint -> voice -> shoot -> camera build -> render -> finish -> contact sheet -> STT.
#   kit/run.sh <film-folder> [--no-voice] [--draft]
# Run from the kit root. Keeps existing takes and clips (delete public/<film>/ to start over).
# The master goes to out/<film>/<film>-vN.mp4 with the next free N; finished files are never overwritten.
set -euo pipefail
FILM="${1:?usage: kit/run.sh <film-folder> [--no-voice] [--draft]}"; shift
NOVOICE=""; DRAFT=""
for a in "$@"; do case "$a" in --no-voice) NOVOICE="--no-voice";; --draft) DRAFT="--draft";; esac; done
PY="${PYTHON:-python3}"
NAME="$(basename "$FILM")"
cd "$(dirname "$0")/.."

[ -f public/sfx/click.mp3 ] || bash kit/make_sfx.sh >/dev/null    # interface sounds (once)
[ -f public/pad.mp3 ] || bash kit/make_pad.sh >/dev/null           # quiet music pad (once); replace with a licensed track
echo "== 1. script check";        $PY kit/qa/lint_script.py "$FILM"
echo "== 2. voice";               $PY kit/tts.py "$FILM" $NOVOICE
echo "== 3. shoot";               $PY kit/shoot.py "$FILM" $DRAFT
echo "== 4. camera and data";     $PY kit/build_data.py "$FILM"
mkdir -p "out/$NAME"
N=1; while [ -e "out/$NAME/$NAME-v$N.mp4" ]; do N=$((N + 1)); done
RAW="out/$NAME/render-v$N.mp4"; MASTER="out/$NAME/$NAME-v$N.mp4"
echo "== 5. render -> $RAW";      npx remotion render src/index.ts Film "$RAW" --codec=h264 --crf=16 --log=error
echo "== 6. finish -> $MASTER";   bash kit/finish.sh "$RAW" "$MASTER"
echo "== 7. contact sheet";       bash kit/qa/sheet.sh "$MASTER" "out/$NAME/sheet-v$N.png" 1 5
if [ -z "$NOVOICE" ]; then
  echo "== 8. STT check (master)"; $PY kit/qa/stt_check.py "$FILM" --master "$MASTER" || echo "STT mismatch: fix the take(s) before sending"
else
  echo "== 8. STT check skipped (silent placeholder voice)"
fi
echo "done: $MASTER and ${MASTER%.mp4}-web.mp4; look at out/$NAME/sheet-v$N.png"
