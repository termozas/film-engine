"""Narration: one take per scene, with word timings (the shoot fires its actions on these words).

  python kit/tts.py <film> [scene ids...] [--force] [--no-voice]
  TTS_BACKEND=kokoro python kit/tts.py <film>

Backends (film.json "tts_backend" or the TTS_BACKEND variable):
  elevenlabs (default)  ElevenLabs text-to-speech with-timestamps. Needs ELEVENLABS_API_KEY.
  kokoro                Kokoro-82M, open source, runs locally. Word timings come from forced alignment with
                        faster-whisper (kit/align.py). Needs `pip install -r requirements-kokoro.txt`.

Writes public/<film>/<vo>/<id>.mp3 and <id>.json ({"words": [{"w", "s", "e"}], "dur"}), the same for every backend.
Existing takes are kept unless you name the scene ids or pass --force.
--no-voice: no voice at all. Writes a silent placeholder take with estimated word timings, so the shoot, the camera
build and the render can be tried first. Placeholder takes are marked and the STT check refuses them.
"""
import base64
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config  # noqa: E402
from textnorm import strip_breaks as clean  # noqa: E402


# ---- ElevenLabs ---------------------------------------------------------------------------------------------------

def words_from_alignment(al):
    chars, st, en = al["characters"], al["character_start_times_seconds"], al["character_end_times_seconds"]
    words, cur, t0, last = [], "", None, None
    for c, a, b in zip(chars, st, en):
        if c.isspace():
            if cur:
                words.append({"w": cur, "s": t0, "e": last}); cur = ""
        else:
            if not cur:
                t0 = a
            cur += c; last = b
    if cur:
        words.append({"w": cur, "s": t0, "e": last})
    words = [w for w in words if not re.match(r"^(<break|time=|/>)", w["w"])]   # break tags are not words
    return words, en[-1]


class ElevenLabs:
    def __init__(self, c):
        self.c = c
        self.key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
        if not self.key:
            sys.exit("ELEVENLABS_API_KEY is not set. Export it (see .env.example), use TTS_BACKEND=kokoro for the open-source voice, "
                     "or pass --no-voice for a silent placeholder take.")

    def take(self, S, i, mp3):
        c, s = self.c, S[i]
        body = {"text": s["text"], "model_id": c.model,
                "previous_text": clean(S[i - 1]["text"]) if i else None,
                "next_text": clean(S[i + 1]["text"]) if i + 1 < len(S) else None}
        if not c.model.startswith("eleven_v4"):   # v4 takes no voice_settings; older models sound better with these
            body["voice_settings"] = {"stability": 0.45, "similarity_boost": 0.8, "style": 0.12, "use_speaker_boost": True, "speed": 0.96}
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{c.voice_id}/with-timestamps?output_format={c.output_format}"
        req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"xi-api-key": self.key, "Content-Type": "application/json"})
        try:
            r = json.load(urllib.request.urlopen(req, timeout=120))
        except urllib.error.HTTPError as e:
            sys.exit(f"ElevenLabs error {e.code} on {s['id']}: {e.read().decode()[:400]}")
        open(mp3, "wb").write(base64.b64decode(r["audio_base64"]))
        words, dur = words_from_alignment(r["alignment"])
        return words, dur, {"backend": "elevenlabs", "voice_id": c.voice_id, "model": c.model}


# ---- Kokoro (open source) -------------------------------------------------------------------------------------------

def _short_espeak_data():
    """espeak-ng (Kokoro's fallback phonemiser) silently fails to load its data from a long path, such as a deep
    virtualenv. Copy the bundled data to a short cache folder when the path is long."""
    try:
        import espeakng_loader
        from phonemizer.backend.espeak.wrapper import EspeakWrapper
    except ImportError:
        return
    src = espeakng_loader.get_data_path()
    if len(src) < 120:
        return
    dst = os.path.join(os.path.expanduser("~"), ".cache", "film-engine", "espeak-ng-data")
    if not os.path.exists(os.path.join(dst, "phontab")):
        shutil.rmtree(dst, ignore_errors=True); shutil.copytree(src, dst)
    EspeakWrapper.set_data_path(dst)


class Kokoro:
    def __init__(self, c):
        self.c = c
        os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")
        try:
            import numpy, soundfile  # noqa: F401
            from kokoro import KPipeline
            import faster_whisper  # noqa: F401
        except ImportError as e:
            sys.exit(f"Kokoro backend needs its packages ({e}). Run: pip install -r requirements-kokoro.txt")
        import kokoro.pipeline  # noqa: F401  (imports misaki, which sets the espeak paths)
        _short_espeak_data()
        self.voice = c.kokoro_voice
        lang = self.voice[0]                       # af_/am_ American English, bf_/bm_ British English
        self.pipe = KPipeline(lang_code=lang, repo_id="hexgrad/Kokoro-82M")

    def take(self, S, i, mp3):
        import numpy as np
        import soundfile as sf
        from align import align
        s = S[i]
        chunks = [r.audio.numpy() for r in self.pipe(clean(s["text"]), voice=self.voice, speed=float(self.c.kokoro_speed))]
        audio = np.concatenate(chunks)
        tmp = os.path.join(tempfile.mkdtemp(), s["id"] + ".wav")
        sf.write(tmp, audio, 24000)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", tmp, "-ar", "44100", "-c:a", "libmp3lame", "-b:a", "128k", mp3], check=True)
        dur = round(len(audio) / 24000, 3)
        words, share = align(s["text"], tmp, dur, self.c.whisper_model, self.c.names)
        if share < 0.85:
            print(f"  {s['id']}: only {share:.0%} of the words were heard as written; listen to the take and run the STT check", flush=True)
        return words, words[-1]["e"] if words else dur, {"backend": "kokoro", "voice": self.voice, "aligned_share": round(share, 3)}


# ---- placeholder (no voice) ---------------------------------------------------------------------------------------

def placeholder(text):
    """Estimated timings for a silent take: about 2.7 words a second, a short pause after each sentence."""
    t, words = 0.05, []
    for w in clean(text).split():
        d = 0.12 + 0.055 * len(w)
        words.append({"w": w, "s": round(t, 3), "e": round(t + d, 3)})
        t += d + (0.32 if re.search(r"[.?!]$", w) else 0.12 if re.search(r"[,;:]$", w) else 0.05)
    return words, round(words[-1]["e"] + 0.1, 3)


BACKENDS = {"elevenlabs": ElevenLabs, "kokoro": Kokoro}


def main():
    film, only, flags = config.film_arg(sys.argv)
    c = config.load(film)
    S = config.script(c)
    no_voice = "--no-voice" in flags
    backend = None
    if not no_voice:
        if c.tts_backend not in BACKENDS:
            sys.exit(f"unknown TTS_BACKEND {c.tts_backend!r}; use one of {sorted(BACKENDS)}")
    os.makedirs(c.vo_dir, exist_ok=True)
    for i, s in enumerate(S):
        if only and s["id"] not in only:
            continue
        mp3, js = os.path.join(c.vo_dir, s["id"] + ".mp3"), os.path.join(c.vo_dir, s["id"] + ".json")
        if os.path.exists(mp3) and not only and "--force" not in flags:
            meta = json.load(open(js)) if os.path.exists(js) else {}
            if not (meta.get("placeholder") and not no_voice):   # a real run replaces placeholders
                continue
        if no_voice:
            words, dur = placeholder(s["text"])
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", f"{dur:.3f}",
                            "-c:a", "libmp3lame", "-b:a", "128k", mp3], check=True)
            json.dump({"words": words, "dur": dur, "placeholder": True}, open(js, "w"))
            print(s["id"], dur, "s (silent placeholder)", flush=True)
            continue
        backend = backend or BACKENDS[c.tts_backend](c)
        words, dur, meta = backend.take(S, i, mp3)
        json.dump({"words": words, "dur": dur, **meta}, open(js, "w"))
        print(s["id"], round(dur, 2), "s", f"({meta['backend']})", flush=True)


if __name__ == "__main__":
    main()
