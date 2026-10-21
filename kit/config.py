"""Film settings: kit defaults, then the film's own film.json, then environment variables (highest).

Every script takes the film folder as its first argument, e.g. `python kit/tts.py examples/hello-demo`.
Generated media goes to public/<film>/<vo|clips>/ (Remotion serves public/), renders to out/<film>/.
"""
import json
import os
import sys

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # the kit root (package.json lives here)

DEFAULTS = {
    # voice. "elevenlabs" (default) or "kokoro" (open source, local). The ElevenLabs key is only ever read from
    # the ELEVENLABS_API_KEY environment variable.
    "tts_backend": "elevenlabs",
    "voice_id": "cgSgspJ2msm6clMCkdW9",      # Jessica
    "model": "eleven_v4",
    "output_format": "mp3_44100_128",
    "stt_model": "scribe_v1",                # ElevenLabs speech-to-text, for the QA check
    "kokoro_voice": "af_heart",              # Kokoro voice id (af_/am_ American, bf_/bm_ British)
    "kokoro_speed": 0.92,              
    "whisper_model": "small.en",             # faster-whisper model for Kokoro alignment and the keyless STT check
    # files inside the film folder
    "script": "script.json",
    "cards": "cards.json",
    "shoot": "shoot.py",
    # the app being filmed: either a folder of static files served by the kit, or a running app at base_url
    "serve": None,                           # e.g. "site" (relative to the film folder)
    "port": 4173,
    "base_url": None,                        # default: http://127.0.0.1:<port>
    # take and footage folder names under public/<film>/ (bump to vo2 / clips2 to keep an older cut intact)
    "vo": "vo",
    "clips": "clips",
    # capture
    "viewport": [1440, 900],                 # CSS pixels; the Remotion window is laid out for 16:10
    "dpr": 2,                                # captured at 2x for crisp zooms
    "locale": "en-US",
    "timezone": "America/New_York",
    "lead": 0.45,                            # silence before the narration starts in each scene
    "tail": 0.55,                            # held after it ends
    "min_fps": 20,
    # film
    "music": "pad.mp3",                      # file in public/; skipped if missing. Ducks under the voice.
    "sfx": True,                             # click and key sounds from public/sfx/ (kit/make_sfx.sh)
    "captions": "words",                     # "words" (each word lights up as spoken), "plain" or "none"
    "names": [],                             # product and place names, to prime local speech-to-text ("Tally")
    "banned": [],                            # extra words that must never appear (customer names, code names)
    "allow_it": [],                          # scene ids where "it" is fine (it does not refer to the product)
}

ENV = {
    "tts_backend": "TTS_BACKEND", "kokoro_voice": "KOKORO_VOICE", "kokoro_speed": "KOKORO_SPEED", "whisper_model": "WHISPER_MODEL",
    "voice_id": "VOICE_ID", "model": "TTS_MODEL", "output_format": "TTS_FORMAT", "stt_model": "STT_MODEL",
    "script": "SCRIPT", "cards": "CARDS", "base_url": "BASE_URL", "port": "PORT",
    "vo": "VO_DIR", "clips": "CLIPS_DIR", "dpr": "DPR",
}


class Cfg(dict):
    __getattr__ = dict.get


def load(film_dir):
    if not film_dir or not os.path.isdir(film_dir):
        sys.exit(f"film folder not found: {film_dir!r} (pass the folder that holds film.json, e.g. examples/hello-demo)")
    film_dir = os.path.abspath(film_dir)
    c = Cfg(DEFAULTS)
    fj = os.path.join(film_dir, "film.json")
    if os.path.exists(fj):
        c.update(json.load(open(fj)))
    for k, e in ENV.items():
        if os.environ.get(e):
            v = os.environ[e]
            c[k] = int(v) if k in ("port", "dpr") else v
    if os.environ.get("DRAFT"):
        c["dpr"] = 1
    c["port"] = int(c["port"])
    c["name"] = c.get("name") or os.path.basename(film_dir)
    c["film_dir"] = film_dir
    c["base_url"] = (c["base_url"] or f"http://127.0.0.1:{c['port']}").rstrip("/")
    c["script_path"] = os.path.join(film_dir, c["script"])
    c["cards_path"] = os.path.join(film_dir, c["cards"])
    c["public_dir"] = os.path.join(KIT, "public", c["name"])
    c["vo_dir"] = os.path.join(c["public_dir"], c["vo"])
    c["clips_dir"] = os.path.join(c["public_dir"], c["clips"])
    c["out_dir"] = os.path.join(KIT, "out", c["name"])
    return c


def script(c):
    return json.load(open(c.script_path))


def film_arg(argv):
    """First non-flag argument is the film folder; the rest are scene ids."""
    pos = [a for a in argv[1:] if not a.startswith("--")]
    if not pos:
        sys.exit(f"usage: {os.path.basename(argv[0])} <film-folder> [scene ids...] [flags]")
    return pos[0], pos[1:], {a for a in argv[1:] if a.startswith("--")}
