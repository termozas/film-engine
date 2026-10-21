#!/usr/bin/env bash
# Before you share a folder or zip: fail if it holds a real API key, a .env file, generated media or private terms.
#   kit/qa/check_secrets.sh <folder> [private-terms.txt]
# private-terms.txt: one word or phrase per line (customer names, addresses, private paths). Keep that file
# outside the folder you check, or the check finds the terms in it.
set -uo pipefail
DIR="${1:?usage: check_secrets.sh <folder> [private-terms.txt]}"; TERMS="${2:-}"
fail=0
say() { echo "FAIL: $*"; fail=1; }
EXC=(--exclude-dir=node_modules --exclude-dir=.git --exclude-dir=.venv --exclude-dir=venv --exclude-dir=__pycache__)

# key-shaped strings (the header name xi-api-key and the variable name are fine; a literal value next to them is not)
hits=$(grep -rnIE "${EXC[@]}" \
  -e 'sk_[A-Za-z0-9]{20,}' \
  -e 'sk-or-[A-Za-z0-9-]{10,}' \
  -e 'sk-(ant-|proj-)?[A-Za-z0-9_-]{20,}' \
  -e "xi-api-key[\"']?[:=, ]+[\"']?[A-Za-z0-9]{20,}" \
  -e 'ELEVEN[A-Z_]*=[\"'"'"']?[A-Za-z0-9_]{16,}' \
  -e 'Bearer [A-Za-z0-9._-]{20,}' \
  -e 'hf_[A-Za-z0-9]{30,}' \
  "$DIR" 2>/dev/null)
[ -n "$hits" ] && { say "key-shaped strings:"; echo "$hits"; }

# files that should never travel
envs=$(find "$DIR" -name node_modules -prune -o \( -name ".env" -o -name ".env.*" ! -name ".env.example" \) -print)
[ -n "$envs" ] && { say ".env files:"; echo "$envs"; }
media=$(find "$DIR" -name node_modules -prune -o -type f \( -iname "*.mp3" -o -iname "*.wav" -o -iname "*.mp4" -o -iname "*.mov" -o -iname "*.m4a" -o -iname "*.webm" \) -print)
[ -n "$media" ] && { say "generated audio or video:"; echo "$media"; }
junk=$(find "$DIR" -type d \( -name node_modules -o -name .venv -o -name venv -o -name __pycache__ -o -name .cache \) -prune -print)
[ -n "$junk" ] && { say "dependency or cache folders:"; echo "$junk"; }

# machine-specific absolute paths
paths=$(grep -rnIE "${EXC[@]}" -e '/Users/[A-Za-z0-9._-]+/' -e '/home/[A-Za-z0-9._-]+/' -e 'C:\\Users\\' "$DIR" 2>/dev/null)
[ -n "$paths" ] && { say "absolute paths to someone's machine:"; echo "$paths"; }

# private terms
if [ -n "$TERMS" ]; then
  while IFS= read -r t; do
    [ -z "$t" ] && continue
    h=$(grep -rnIiF "${EXC[@]}" -e "$t" "$DIR" 2>/dev/null)
    [ -n "$h" ] && { say "private term '$t':"; echo "$h"; }
    f=$(find "$DIR" -iname "*$t*" -not -path "*/node_modules/*" -not -path "*/.git/*")
    [ -n "$f" ] && { say "file name with private term '$t':"; echo "$f"; }
  done < "$TERMS"
fi

[ $fail -eq 0 ] && echo "clean: no keys, .env files, media, caches, machine paths$( [ -n "$TERMS" ] && echo " or private terms") in $DIR"
exit $fail
