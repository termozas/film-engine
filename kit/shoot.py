"""Shoot the footage scenes of a film.

  python kit/shoot.py <film> [scene ids...] [--draft] [--allow-low-fps]

For every scene in script.json without a "card", runs the function of the same name in the film's shoot.py.
If film.json sets "serve" (a folder of static files), the kit serves it on 127.0.0.1:<port> for the shoot.
Otherwise start your app yourself and point base_url (or BASE_URL) at it.
--draft captures at device scale 1 (faster, softer). Exit code 2 if any scene captured under min_fps.
"""
import functools
import http.server
import importlib.util
import os
import socket
import sys
import threading
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config  # noqa: E402


def port_free(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) != 0


def serve(folder, port):
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a): pass
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", port), functools.partial(Quiet, directory=folder))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


def main():
    film, only, flags = config.film_arg(sys.argv)
    if "--draft" in flags:
        os.environ["DRAFT"] = "1"
    os.environ["FILM_DIR"] = os.path.abspath(film)
    c = config.load(film)
    S = config.script(c)

    httpd = None
    if c.serve:
        if not port_free(c.port):
            sys.exit(f"port {c.port} is busy. Pick a free one with PORT=<n> (never stop a process you did not start).")
        httpd = serve(os.path.join(c.film_dir, c.serve), c.port)
        print(f"serving {c.serve}/ on {c.base_url}")
    try:
        urllib.request.urlopen(c.base_url, timeout=10)
    except Exception as e:
        sys.exit(f"the app is not answering at {c.base_url} ({e}). Start it, or set base_url in film.json / BASE_URL.")

    import cap   # reads FILM_DIR
    spec = importlib.util.spec_from_file_location("film_shoot", os.path.join(c.film_dir, c.shoot))
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)

    ids = [s["id"] for s in S if not s.get("card")]
    if only:
        bad = [i for i in only if i not in ids]
        if bad:
            sys.exit(f"not footage scenes in {c.script}: {bad}")
        ids = [i for i in ids if i in only]
    missing = [i for i in ids if not hasattr(mod, i)]
    if missing:
        sys.exit(f"{c.shoot} has no function for scene(s) {missing}")
    for i in ids:
        if not os.path.exists(os.path.join(c.vo_dir, i + ".json")):
            sys.exit(f"no take for {i} in {c.vo_dir}: run kit/tts.py first")

    from playwright.sync_api import sync_playwright
    low = []
    with sync_playwright() as p:
        tails = {s["id"]: s.get("tail") for s in S}
        for sid in ids:
            sc = cap.Scene(p, sid, tail=tails.get(sid))   # the script's "tail": seconds held after the narration
            getattr(mod, sid)(sc)
            if getattr(sc, "fps", 99) < c.min_fps:
                low.append((sid, sc.fps))
    if httpd:
        httpd.shutdown()
    if low:
        print(f"capture under {c.min_fps} fps: {low}. Pause screen recorders and GeForce NOW, close heavy apps, re-shoot those scenes.")
        if "--allow-low-fps" not in flags:
            sys.exit(2)


if __name__ == "__main__":
    main()
