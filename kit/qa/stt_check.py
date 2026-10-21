"""Speech-to-text check: every take, and the finished master, must say the script word for word.

  python kit/qa/stt_check.py <film> [scene ids...]             # each take in public/<film>/<vo>/
  python kit/qa/stt_check.py <film> --master out/<film>/<film>-v1.mp4

Transcribes with ElevenLabs speech-to-text (stt_model, default scribe_v1) when ELEVENLABS_API_KEY is set; without
a key, or with --whisper, it runs locally with faster-whisper (pip install faster-whisper). Both sides are lower-cased, stripped of
punctuation, and digits in the transcript are spelled out, so "38" matches "thirty-eight". Any other difference
is printed and the exit code is 1. A misread word means: re-generate the take, or spell the word the way it
should sound (numbers, names, abbreviations).
"""
import difflib
import json
import os
import subprocess
import sys
import tempfile
import uuid
import urllib.request

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KIT)
import config  # noqa: E402
from textnorm import norm  # noqa: E402

def scribe(path, model):
    key = os.environ["ELEVENLABS_API_KEY"].strip()
    bnd = uuid.uuid4().hex
    body = (f"--{bnd}\r\nContent-Disposition: form-data; name=\"model_id\"\r\n\r\n{model}\r\n"
            f"--{bnd}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{os.path.basename(path)}\"\r\n"
            f"Content-Type: application/octet-stream\r\n\r\n").encode() + open(path, "rb").read() + f"\r\n--{bnd}--\r\n".encode()
    req = urllib.request.Request("https://api.elevenlabs.io/v1/speech-to-text", data=body,
                                 headers={"xi-api-key": key, "Content-Type": f"multipart/form-data; boundary={bnd}"})
    return json.load(urllib.request.urlopen(req, timeout=300)).get("text", "")


_whisper = None


def whisper(path, model_name="small.en", names=()):
    global _whisper
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        sys.exit("no ELEVENLABS_API_KEY and faster-whisper is not installed: pip install faster-whisper (or set the key)")
    _whisper = _whisper or WhisperModel(model_name, device="cpu", compute_type="int8")
    prompt = ("Names: " + ", ".join(names) + ".") if names else None   # film.json "names": spell product names right
    segs, _ = _whisper.transcribe(path, language="en", initial_prompt=prompt)
    return " ".join(s.text for s in segs)


def compare(label, ref_text, heard):
    ref, hyp = norm(ref_text), norm(heard)
    if ref == hyp:
        print(f"{label}: OK ({len(ref)} words)")
        return True
    print(f"{label}: MISMATCH\n  heard: {heard.strip()}")
    for op, a1, a2, b1, b2 in difflib.SequenceMatcher(a=ref, b=hyp, autojunk=False).get_opcodes():
        if op != "equal":
            print(f"  {op:7} script: {' '.join(ref[a1:a2]) or '-':40}  heard: {' '.join(hyp[b1:b2]) or '-'}")
    return False


def main():
    film, only, flags = config.film_arg(sys.argv)
    c = config.load(film)
    S = config.script(c)
    local = "--whisper" in flags or not os.environ.get("ELEVENLABS_API_KEY", "").strip()
    print("speech-to-text:", f"faster-whisper {c.whisper_model} (local)" if local else f"ElevenLabs {c.stt_model}")
    stt = (lambda p: whisper(p, c.whisper_model, c.names)) if local else (lambda p: scribe(p, c.stt_model))
    master = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--master=")), None)
    if "--master" in sys.argv:
        k = sys.argv.index("--master"); master = sys.argv[k + 1] if k + 1 < len(sys.argv) else None
        only = [x for x in only if x != master]
    ok = True
    if master:
        tmp = os.path.join(tempfile.mkdtemp(), "master.mp3")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", master, "-vn", "-ac", "1", "-b:a", "96k", tmp], check=True)
        ok = compare(f"master {os.path.basename(master)}", " ".join(s["text"] for s in S), stt(tmp))
    else:
        for s in S:
            if only and s["id"] not in only:
                continue
            js = os.path.join(c.vo_dir, s["id"] + ".json")
            if os.path.exists(js) and json.load(open(js)).get("placeholder"):
                print(f"{s['id']}: placeholder (silent) take, nothing to check; generate the real take first"); ok = False; continue
            ok = compare(s["id"], s["text"], stt(os.path.join(c.vo_dir, s["id"] + ".mp3"))) and ok
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
