"""Collect scene timings, camera moves, spotlights, captions and card data into src/data.ts for Remotion.

  python kit/build_data.py <film> [--strict]

Applies the camera rules (pull back before a click outside the zoom; no zoom held past HOLD seconds) and prints a
`camera:` warning for anything that will read as jitter or a double zoom. --strict exits 1 on any warning.
"""
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config  # noqa: E402

HOLD, PRE = 3.4, 1.0      # longest a zoom holds; how early the camera pulls back before a click outside the zoom
MIN_ZOOM, MIN_PULLBACK = 1.2, 1.8
warnings = []


def warn(msg):
    warnings.append(msg); print("  " + msg)


def spots_and_camera(m, dur, area_max):
    """Spotlight segments from the live track: lit only while the element sits still and visible; cut by a page change
    or a click outside it. The camera aims at where the element settled, not where it was when the cue fired."""
    ff = m["first_frame"]; F = m["focus"]; T = [(t - ff, i, v) for t, i, v in m.get("track", [])]
    navs = [t for t, i, v in T if i == "nav"]
    clicks = [(t, *map(float, v.split(","))) for t, i, v in T if i == -1]
    spots, focus = [], []
    for k, f in enumerate(F):
        t0 = f["t"] - ff; t1 = (F[k + 1]["t"] - ff) if k + 1 < len(F) else dur
        g = dict(f); g["t"] = round(t0, 3); focus.append(g)
        if not f["rect"]:
            continue
        segs = []
        if f.get("tracked"):
            smp = sorted((t, v) for t, i, v in T if i == f["id"])
            pts = []
            for t, v in smp:
                r = None if v in (None, "null") else [float(x) for x in v.split(",")]
                pts.append((max(t, t0), r))
            for a in range(len(pts)):
                ta, r = pts[a]; tb = pts[a + 1][0] if a + 1 < len(pts) else t1
                tb = min(tb, t1)
                if r and tb - ta >= 0.6:
                    segs.append([ta + 0.1, tb, r])
            settled = next((r for _, _, r in segs), None) or next((r for _, r in reversed(pts) if r), None)
            if settled:
                g["rect"] = settled
        else:
            segs.append([t0 + 0.3, t1, f["rect"]])
        for a, b, r in segs:
            stop = [n for n in navs if a < n < b] + [c for c, x, y in clicks if a < c < b and not (r[0] - 8 <= x <= r[0] + r[2] + 8 and r[1] - 8 <= y <= r[1] + r[3] + 8)]
            if stop:
                b = min(stop)
            if b - a >= 0.5 and r[2] * r[3] < area_max:
                spots.append({"t0": round(a, 3), "t1": round(b, 3), "rect": [round(x, 1) for x in r]})
    return focus, spots


def calm(m):
    """Camera rules: (1) before a click that lands outside the zoomed element, ease back to the full page so the
    viewer sees what is clicked; (2) never sit on one element longer than HOLD seconds."""
    F = sorted(m["focus"], key=lambda f: f["t"])
    clicks = sorted((t, *map(float, v.split(","))) for t, i, v in m.get("track", []) if i == -1)
    out = F[:]

    def active(t):
        cur = None
        for f in out:
            if f["t"] <= t:
                cur = f
        return cur
    for c, x, y in clicks:
        f = active(c - PRE)
        if f and f["rect"]:
            r = f["rect"]
            if not (r[0] - 12 <= x <= r[0] + r[2] + 12 and r[1] - 12 <= y <= r[1] + r[3] + 12):
                t = max(f["t"] + 0.8, c - PRE)
                out.append({"t": round(t, 3), "rect": None, "scale": None, "hold": None, "id": -1, "tracked": False})
                out.sort(key=lambda f: f["t"])
    final = []
    for k, f in enumerate(out):
        final.append(f)
        nxt = out[k + 1]["t"] if k + 1 < len(out) else m["dur"]
        if f["rect"] and nxt - f["t"] > HOLD + 0.8:
            final.append({"t": round(f["t"] + HOLD, 3), "rect": None, "scale": None, "hold": None, "id": -2, "tracked": False})
    m["focus"] = final
    return m


def captions(words):
    """One sentence per line; a long sentence splits at the comma nearest its middle."""
    sents, cur = [], []
    for w in words:
        cur.append(w)
        if re.search(r"[.?!]$", w["w"]) and w["w"] not in ("Dr.", "Mr.", "Ms.", "Mrs.", "St."):
            sents.append(cur); cur = []
    if cur:
        sents.append(cur)
    lines = []

    def split(ws):
        if len(" ".join(x["w"] for x in ws)) <= 64 or len(ws) < 6:
            lines.append(ws); return
        cands = [i for i in range(2, len(ws) - 2) if re.search(r"[,;:]$", ws[i]["w"])]
        mid = len(ws) / 2
        i = min(cands, key=lambda k: abs(k + 1 - mid)) + 1 if cands else int(mid)
        split(ws[:i]); split(ws[i:])
    for se in sents:
        split(se)
    return [{"t0": round(l[0]["s"], 3), "t1": round(l[-1]["e"], 3), "text": " ".join(x["w"] for x in l),
             "words": [{"w": x["w"], "s": round(x["s"], 3)} for x in l]} for l in lines]


def main():
    film, _, flags = config.film_arg(sys.argv)
    c = config.load(film)
    S = config.script(c)
    vw, vh = c.viewport
    area_max = 0.55 * vw * vh
    out, placeholders = [], []
    for s in S:
        vj = os.path.join(c.vo_dir, s["id"] + ".json")
        if not os.path.exists(vj):
            sys.exit(f"no take for {s['id']} ({vj}): run kit/tts.py first")
        vo = json.load(open(vj))
        if vo.get("placeholder"):
            placeholders.append(s["id"])
        if s.get("card"):   # a Remotion card, not footage: the scene is the take plus a lead and a tail
            m = {"dur": round(c.lead + vo["dur"] + s.get("tail", 0.9), 3), "first_frame": 0, "vo_at": c.lead, "focus": [], "track": [], "marks": {}}
        else:
            cj = os.path.join(c.clips_dir, s["id"] + ".json")
            if not os.path.exists(cj):
                sys.exit(f"no footage for {s['id']} ({cj}): run kit/shoot.py first")
            m = calm(json.load(open(cj)))
            if m.get("fps") and m["fps"] < c.min_fps:
                warn(f"capture: {s['id']} was captured at {m['fps']} fps (under {c.min_fps}); re-shoot with screen recorders paused")
        ff = m["first_frame"]

        def wt(phrase, sid=s["id"]):
            ph = [re.sub(r"[^a-z0-9]", "", x.lower()) for x in phrase.split()]
            ws = [re.sub(r"[^a-z0-9]", "", x["w"].lower()) for x in vo["words"]]
            hit = next((i for i in range(len(ws)) if ws[i:i + len(ph)] == ph), None)
            if hit is None:
                sys.exit(f"{sid}: phrase not found in the take: {phrase!r} (marks and tags must quote the scene's own words)")
            return vo["words"][hit]["s"]

        tags = [{"t0": round(wt(t["at"]) - 0.2, 3), "t1": round(wt(t["at"]) - 0.2 + t.get("dur", 4.0), 3), "text": t["text"]} for t in s.get("tags", [])]
        vlen = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", os.path.join(c.vo_dir, s["id"] + ".mp3")]))
        cmarks = {k: round(wt(v) + m["vo_at"] - ff, 3) for k, v in (s.get("marks") or {}).items()}
        focus, spots = spots_and_camera(m, m["dur"] - ff, area_max)
        # interface sounds: every mouse press and key press the capture logged, in scene time
        sfx = [{"t": round(t - ff, 3), "k": "click"} for t, i, v in m.get("track", []) if i == -1 and t - ff >= 0]
        last = -1.0
        for t in m.get("keys", []):
            if t - ff >= 0 and t - last >= 0.03:
                sfx.append({"t": round(t - ff, 3), "k": "key"}); last = t
        sfx.sort(key=lambda e: e["t"])
        out.append({"id": s["id"], "label": s.get("label", ""), "card": s.get("card"), "props": s.get("props", {}), "cardMarks": cmarks,
                    "voLen": round(vlen, 3), "dur": round(m["dur"] - ff, 3), "voAt": round(m["vo_at"] - ff, 3),
                    "focus": focus, "spots": spots, "tags": tags, "caps": captions(vo["words"]), "sfx": sfx})

    cards = json.load(open(c.cards_path)) if os.path.exists(c.cards_path) else {}
    music = c.music if c.music and os.path.exists(os.path.join(config.KIT, "public", c.music)) else None
    pub = os.path.join(config.KIT, "public")
    keys = sorted(f"sfx/{f}" for f in os.listdir(os.path.join(pub, "sfx")) if f.startswith("key")) if os.path.isdir(os.path.join(pub, "sfx")) else []
    sfx_files = {"click": "sfx/click.mp3", "keys": keys} if c.sfx and keys and os.path.exists(os.path.join(pub, "sfx", "click.mp3")) else None
    data = {"DIR": {"vo": f"{c.name}/{c.vo}", "clips": f"{c.name}/{c.clips}"}, "VIEW": [vw, vh], "MUSIC": music, "SFX": sfx_files,
            "CAPTIONS": c.captions, "CARDS": cards}
    ts = "// generated by kit/build_data.py for " + c.name + "; do not edit by hand\n"
    ts += "".join(f"export const {k}: any = {json.dumps(v, ensure_ascii=False)};\n" for k, v in data.items())
    ts += "export const SCENES: any[] = " + json.dumps(out, indent=1, ensure_ascii=False) + ";\n"
    open(os.path.join(config.KIT, "src", "data.ts"), "w").write(ts)
    total = sum(x["dur"] for x in out) + float(cards.get("intro", {}).get("dur", 0)) + float(cards.get("outro", {}).get("dur", 0))
    print(f"{c.name}: {len(out)} scenes, {total:.1f} s -> src/data.ts" + ("" if music else "  (no music: run kit/make_pad.sh, or put a licensed track in public/)")
          + ("" if sfx_files or not c.sfx else "  (no interface sounds: run kit/make_sfx.sh)"))
    if placeholders:
        print(f"  note: silent placeholder takes for {placeholders} (--no-voice). Generate real takes before the final render.")

    # camera check: a zoom under MIN_ZOOM s, or a pull-back under MIN_PULLBACK s between two zooms, reads as jitter or a double zoom
    for x in out:
        F = x["focus"]
        for i, f in enumerate(F):
            n = F[i + 1]["t"] if i + 1 < len(F) else x["dur"]
            if f["rect"] and n - f["t"] < MIN_ZOOM:
                warn(f"camera: {x['id']} zoom at {f['t']:.1f}s lasts {n - f['t']:.2f}s (jitter); drop a zoom cue")
            if not f["rect"] and 0 < i < len(F) - 1 and F[i - 1]["rect"] and F[i + 1]["rect"] and n - f["t"] < MIN_PULLBACK:
                warn(f"camera: {x['id']} zooms out and back in at {f['t']:.1f}s (double zoom); drop a zoom cue")
            if f.get("scale") and f["scale"] > 1.9:
                warn(f"camera: {x['id']} asks for {f['scale']}x at {f['t']:.1f}s; the film caps zoom at 1.9x")
    if not warnings:
        print("  camera: no warnings")
    if warnings and "--strict" in flags:
        sys.exit(1)


if __name__ == "__main__":
    main()
