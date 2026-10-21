"""Screen capture for the film: Chromium at device scale 2, frames from the CDP screencast, actions fired on the
narration's own word timings, and a log of what to zoom on and when (build_data.py turns it into camera moves).

A film's shoot.py defines one function per footage scene, named like the scene id in script.json:

    from cap import go, glide_to

    def s02(sc):
        sc.prepare(go("/", "#vendor"))          # off camera: load the starting page
        sc.start()                              # recording starts; the take starts lead seconds later
        sc.cue("Type a vendor", lambda s: s.click("#vendor"), early=0.4)
        sc.cue("vendor's name", lambda s: s.zoom("#check-form"))
        sc.finish()                             # waits for the take to end, then encodes the clip

Run it with `python kit/shoot.py <film> [scene ids]`.
"""
import base64, json, os, re, shutil, subprocess, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config  # noqa: E402

CFG = config.load(os.environ["FILM_DIR"]) if os.environ.get("FILM_DIR") else None
BASE = CFG.base_url if CFG else os.environ.get("BASE_URL", "http://127.0.0.1:4173")
ARGS = ["--hide-scrollbars", "--ignore-gpu-blocklist"] + (["--use-angle=metal"] if sys.platform == "darwin" else [])
CHROMIUM = os.environ.get("CHROMIUM_PATH") or None     # default: Playwright's own Chromium
W, H = (CFG.viewport if CFG else [1440, 900])
DPR = int(CFG.dpr) if CFG else 2
STATE = os.environ.get("STATE") or None                 # optional Playwright storage_state file (a logged-in session)

CURSOR = """
(() => {
  if (window.__cur) return; window.__cur = 1;
  const css = `#__cursor{position:fixed;left:0;top:0;width:30px;height:30px;z-index:2147483647;pointer-events:none;will-change:transform;transition:transform 90ms cubic-bezier(.25,.8,.3,1);filter:drop-shadow(0 2px 4px rgba(0,0,0,.35))}
  #__ripple,#__ripple2{position:fixed;width:64px;height:64px;margin:-32px 0 0 -32px;border-radius:50%;z-index:2147483646;pointer-events:none;opacity:0;transform:scale(.3)}
  #__ripple{background:rgba(0,74,195,.16);border:3px solid rgba(0,38,100,.85)}
  #__ripple2{border:2px solid rgba(0,38,100,.45)}
  html{scroll-behavior:smooth}`;
  const mk = () => {
    const st = document.createElement('style'); st.textContent = css; document.documentElement.appendChild(st);
    const c = document.createElement('div'); c.id = '__cursor';
    c.innerHTML = '<svg width="30" height="30" viewBox="0 0 28 28"><path d="M5 3 L5 23 L10.2 18.2 L13.6 25.6 L17 24.1 L13.7 16.9 L20.6 16.6 Z" fill="#111" stroke="#fff" stroke-width="1.6" stroke-linejoin="round"/></svg>';
    document.documentElement.appendChild(c);
    const r = document.createElement('div'); r.id = '__ripple'; document.documentElement.appendChild(r);
    const r2 = document.createElement('div'); r2.id = '__ripple2'; document.documentElement.appendChild(r2);
    const p = window.__pos || JSON.parse(sessionStorage.getItem('__pos') || '[720,450]');
    c.style.transform = `translate(${p[0] - 5}px,${p[1] - 3}px)`;
    addEventListener('mousemove', (e) => { window.__pos = [e.clientX, e.clientY]; sessionStorage.setItem('__pos', JSON.stringify(window.__pos)); c.style.transform = `translate(${e.clientX - 5}px,${e.clientY - 3}px)`; }, true);
    addEventListener('mousedown', (e) => {
      for (const [el, d, to] of [[r, 0, 1.15], [r2, 90, 1.6]]) {
        el.style.left = e.clientX + 'px'; el.style.top = e.clientY + 'px';
        el.animate([{ opacity: 1, transform: 'scale(.25)' }, { opacity: 0, transform: `scale(${to})` }], { duration: 640, delay: d, easing: 'cubic-bezier(.2,.7,.2,1)', fill: 'both' });
      }
      c.animate([{ transform: c.style.transform + ' scale(1)' }, { transform: c.style.transform + ' scale(.86)' }, { transform: c.style.transform + ' scale(1)' }], { duration: 220 });
    }, true);
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mk); else mk();
})();
"""

TRACK = """
(() => {
  if (window.__trkInit) return; window.__trkInit = 1;
  // every smooth scroll the film asks for becomes a slow, eased glide (the browser's own is too quick under a zoom)
  window.__gliding = 0;
  const ease = (t) => t < .5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
  const scroller = (el) => { let p = el && el.parentElement; while (p && p !== document.body && p !== document.documentElement) { const cs = getComputedStyle(p); if (/(auto|scroll)/.test(cs.overflowY) && p.scrollHeight > p.clientHeight + 2) return p; p = p.parentElement; } return document.scrollingElement; };
  const glide = (sc, top) => {
    top = Math.max(0, Math.min(top, sc.scrollHeight - sc.clientHeight)); const from = sc.scrollTop, d = top - from;
    if (Math.abs(d) < 2) return;
    const ms = Math.min(1200, 880 + Math.abs(d) * 0.22); window.__gliding++;   /* 0.9-1.2 s */
    const html = document.documentElement, hb = html.style.scrollBehavior, sb = sc.style.scrollBehavior;
    html.style.scrollBehavior = 'auto'; sc.style.scrollBehavior = 'auto'; const t0 = performance.now();
    const step = (now) => { const k = Math.min(1, (now - t0) / ms); sc.scrollTop = from + d * ease(k);
      if (k < 1) requestAnimationFrame(step); else { window.__gliding = Math.max(0, window.__gliding - 1); html.style.scrollBehavior = hb; sc.style.scrollBehavior = sb; } };
    requestAnimationFrame(step);
  };
  window.__glide = glide;
  const siv = Element.prototype.scrollIntoView;
  // window.__glideAll (set by a scene): the page's own instant jumps glide too, and focus() does not jump
  const fo = HTMLElement.prototype.focus;
  HTMLElement.prototype.focus = function (o) { return fo.call(this, (window.__glideAll || window.__noJump) ? Object.assign({}, o || {}, { preventScroll: true }) : o); };
  Element.prototype.scrollIntoView = function (o) {
    if (window.__noJump && (o === undefined || o === true || (o && typeof o === 'object' && o.behavior !== 'smooth'))) return;   // the scene glides itself
    if (window.__glideAll && (o === undefined || o === true || (o && typeof o === 'object' && o.behavior !== 'smooth'))) o = Object.assign({ block: 'start' }, (o && typeof o === 'object') ? o : {}, { behavior: 'smooth' });
    if (o && typeof o === 'object' && o.behavior === 'smooth') {
      const sc = scroller(this), r = this.getBoundingClientRect();
      const box = sc === document.scrollingElement ? { top: 0, height: innerHeight } : sc.getBoundingClientRect();
      const b = o.block || 'start';
      const off = b === 'center' ? r.top - box.top - (box.height - r.height) / 2 : b === 'end' ? r.bottom - box.top - box.height : r.top - box.top - 16;
      return glide(sc, sc.scrollTop + off);
    }
    return siv.call(this, o);
  };
  const est = Element.prototype.scrollTo;
  Element.prototype.scrollTo = function (a) { if (a && typeof a === 'object' && a.behavior === 'smooth' && 'top' in a) return glide(this, a.top); return est.apply(this, arguments); };
  const wst = window.scrollTo.bind(window);
  window.scrollTo = function (a, b) {
    if (a && typeof a === 'object' && a.behavior === 'smooth' && 'top' in a) return glide(document.scrollingElement, a.top);
    if (window.__noJump && !(a && typeof a === 'object' && a.behavior === 'smooth')) return;
    if (window.__glideAll) { const top = (a && typeof a === 'object') ? a.top : b; if (typeof top === 'number') return glide(document.scrollingElement, top); }
    return wst(a, b); };
  // live position of the narrated element, so the editor's spotlight sits on it, and only while it is visible
  let last = '';
  const loop = () => {
    const el = window.__trkEl;
    if (el && window.__trk) {
      let v = 'null';
      if (el.isConnected) {
        const r = el.getBoundingClientRect();
        if (r.width > 0 && r.height > 0) {
          let vis = 0, n = 0;
          for (const [fx, fy] of [[.5, .5], [.25, .3], [.75, .3], [.25, .7], [.75, .7]]) {
            const x = r.left + r.width * fx, y = r.top + r.height * fy;
            if (x < 0 || y < 0 || x > innerWidth || y > innerHeight) continue; n++;
            const t = document.elementFromPoint(x, y); if (t && (el.contains(t) || (t !== document.documentElement && t !== document.body && t.contains(el)))) vis++;
          }
          if (n && vis * 2 >= n) v = [r.left, r.top, r.width, r.height].map(Math.round).join(',');
        }
      }
      const key = window.__trkId + ':' + v;
      if (key !== last) { last = key; window.__trk(window.__trkId, v, Date.now()); }
    }
    setTimeout(loop, 40);
  };
  setTimeout(loop, 40);
  addEventListener('mousedown', (e) => { if (window.__trk) window.__trk(-1, e.clientX + ',' + e.clientY, Date.now()); }, true);
})();
"""


def norm(w):
    import unicodedata
    w = "".join(c for c in unicodedata.normalize("NFD", w.lower()) if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]", "", w)


class Scene:
    """One narrated scene: words = the take's word timings; cue(phrase) = the time that phrase starts."""

    def __init__(self, p, sid, state=STATE, init=None, lead=None, tail=None):
        self.sid = sid
        self.lead = CFG.lead if lead is None else lead
        self.tail = CFG.tail if tail is None else tail
        vo = json.load(open(os.path.join(CFG.vo_dir, sid + ".json")))
        self.words, self.dur = vo["words"], vo["dur"]
        self.b = p.chromium.launch(args=ARGS, executable_path=CHROMIUM)
        kw = dict(viewport={"width": W, "height": H}, device_scale_factor=DPR, ignore_https_errors=True, locale=CFG.locale, timezone_id=CFG.timezone)
        if state: kw["storage_state"] = state
        self.ctx = self.b.new_context(**kw)
        if init: self.ctx.add_init_script(init)
        self.ctx.add_init_script(CURSOR)
        self.ctx.add_init_script(TRACK)
        self.track, self.fid = [], 0
        self.ctx.expose_function("__trk", lambda i, v, ts: self.track.append((ts / 1000.0, i, v)))
        self.pg = self.ctx.new_page()
        self.pg.on("framenavigated", lambda fr: fr == self.pg.main_frame and self.track.append((time.time(), "nav", None)))
        self.pg.on("pageerror", lambda e: print("PAGEERROR", str(e)[:160]))
        self.focus, self.frames, self.rec, self.marks, self.keys = [], [], False, {}, []
        self.fdir = os.path.join(CFG.out_dir, "frames", sid); shutil.rmtree(self.fdir, ignore_errors=True); os.makedirs(self.fdir)
        self.cdp = self.ctx.new_cdp_session(self.pg)
        self.cdp.on("Page.screencastFrame", self._frame)

    def _frame(self, ev):
        if self.rec:
            n = len(self.frames)
            path = os.path.join(self.fdir, f"{n:06d}.jpg")
            open(path, "wb").write(base64.b64decode(ev["data"]))
            self.frames.append((time.time(), path))
        try: self.cdp.send("Page.screencastFrameAck", {"sessionId": ev["sessionId"]})
        except Exception: pass

    def prepare(self, fn):
        """Load the starting page off camera."""
        fn(self); self.pg.wait_for_timeout(600)

    def start(self):
        self.cdp.send("Page.startScreencast", {"format": "jpeg", "quality": 92, "maxWidth": W * DPR, "maxHeight": H * DPR, "everyNthFrame": 1})
        self.pg.wait_for_timeout(300)
        self.rec = True; self.t0 = time.time()
        # keep frames flowing even on a still page
        self.pg.evaluate("(()=>{if(window.__tick)return;window.__tick=1;const d=document.createElement('div');d.style.cssText='position:fixed;right:0;bottom:0;width:1px;height:1px;opacity:.01;z-index:-1';document.documentElement.appendChild(d);let i=0;setInterval(()=>{d.style.background=(i++%2)?'#000':'#fff'},40)})()")

    def now(self): return time.time() - self.t0

    def mark(self, name):
        """Name a moment in the clip (seconds from the start of recording)."""
        self.marks[name] = round(self.now(), 3)

    def at(self, phrase, nth=0):
        """Time (from the start of recording) at which this phrase starts in the take."""
        target = [norm(w) for w in phrase.split()]
        hits = [i for i in range(len(self.words)) if [norm(x["w"]) for x in self.words[i:i + len(target)]] == target]
        if not hits:
            raise KeyError(f"{self.sid}: cue not found in the take: {phrase!r}. Cues must be exact words from the scene's text.")
        return self.lead + self.words[hits[nth]]["s"]

    def wait_until(self, t):
        rem = t - self.now()
        if rem > 0: self.pg.wait_for_timeout(int(rem * 1000))

    def cue(self, phrase, fn, early=0.25, nth=0):
        """Run fn(scene) `early` seconds before the phrase is spoken (a click lands as the word is said)."""
        want = self.at(phrase, nth) - early
        self.wait_until(want); a = self.now(); fn(self)
        late = a - want
        if os.environ.get("CUELOG") or late > 0.35:
            print(f"  cue {phrase!r}: wanted {want:.2f}s, started {a:.2f}s, took {self.now() - a:.2f}s" + ("  (late: the previous action ran long)" if late > 0.35 else ""), flush=True)

    def idle(self):
        """Wait for any glide scroll to land, so nothing is measured or clicked mid-scroll."""
        try: self.pg.wait_for_function("!window.__gliding", timeout=4000, polling=50)
        except Exception: pass

    def box(self, sel):
        self.idle()
        loc = self.pg.locator(sel).first
        try:
            if loc.evaluate("e => { for (let p = e; p && p !== document.body; p = p.parentElement) { const ps = getComputedStyle(p).position; if (ps === 'fixed' || ps === 'sticky') return 0 } const r = e.getBoundingClientRect(); if (r.height && (r.height < innerHeight * 0.8 ? (r.top < 50 || r.bottom > innerHeight - 30) : (r.top > innerHeight * 0.6 || r.bottom < innerHeight * 0.3))) { e.scrollIntoView({behavior: 'smooth', block: 'center'}); return 1 } return 0 }", timeout=3000):
                self.pg.wait_for_timeout(60); self.idle()
        except Exception: pass
        try: loc.scroll_into_view_if_needed(timeout=3000)
        except Exception: pass
        return loc.bounding_box()

    def zoom(self, sel=None, rect=None, scale=None, hold=None):
        """Ask the editor to frame this element from now on (None = back to the full screen). An element given by
        selector is tracked live in the page, so the spotlight follows it and drops when it scrolls or is covered."""
        self.fid += 1; tracked = False
        if sel:
            b = self.box(sel); rect = [b["x"], b["y"], b["width"], b["height"]] if b else None
            try: self.pg.locator(sel).first.evaluate("(e, id) => { window.__trkEl = e; window.__trkId = id; }", self.fid); tracked = True
            except Exception: pass
        else:
            try: self.pg.evaluate("window.__trkEl = null")
            except Exception: pass
        self.focus.append({"t": round(self.now(), 3), "rect": rect, "scale": scale, "hold": hold, "id": self.fid, "tracked": tracked})

    def move(self, sel=None, x=None, y=None, steps=34, dx=0.5, dy=0.5, settle=160):
        """An eased, unhurried cursor move (0.4-0.6 s), starting from wherever the page cursor really is."""
        if sel:
            b = self.box(sel); x, y = b["x"] + min(b["width"] * dx, 80), b["y"] + b["height"] * dy
        try: p = self.pg.evaluate("window.__pos || null")
        except Exception: p = None
        if not p: self.pg.mouse.move(x, y, steps=max(steps, 12)); self.pg.wait_for_timeout(settle); return
        x0, y0 = p; dist = ((x - x0) ** 2 + (y - y0) ** 2) ** 0.5
        dur = min(0.6, max(0.4, 0.3 + dist / 2600)) * (1.0 if steps >= 12 else 0.75)   # time-based: same pace at any load
        t0 = time.time()
        while True:
            k = min(1.0, (time.time() - t0) / dur); e = 4 * k ** 3 if k < .5 else 1 - (-2 * k + 2) ** 3 / 2
            self.pg.mouse.move(x0 + (x - x0) * e, y0 + (y - y0) * e)
            if k >= 1: break
            self.pg.wait_for_timeout(12)
        self.pg.wait_for_timeout(settle)

    def click(self, sel, after=400, **k):
        self.move(sel, **k); self.idle(); self.pg.mouse.down(); self.pg.wait_for_timeout(70); self.pg.mouse.up(); self.pg.wait_for_timeout(after)

    def type(self, sel, text, delay=55):
        """Types into the element, one key at a time (click it first so the cursor is seen going there).
        Each key press is logged so the film can add a light key sound."""
        self.pg.locator(sel).first.focus()
        for ch in text:
            if self.rec: self.keys.append(round(self.now(), 3))
            self.pg.keyboard.type(ch)
            self.pg.wait_for_timeout(delay)

    def finish(self, state_out=None, post=None):
        self.wait_until(self.lead + self.dur + self.tail)
        end = time.time(); self.rec = False
        try: self.cdp.send("Page.stopScreencast")
        except Exception: pass
        if post: post(self)          # off camera: whatever must still happen for the next scene
        if state_out: self.ctx.storage_state(path=state_out)
        self.ctx.close(); self.b.close()
        if not self.frames:
            raise RuntimeError(f"{self.sid}: no frames captured")
        # frames -> constant 30 fps video
        lst = os.path.join(self.fdir, "list.txt")
        with open(lst, "w") as f:
            fr = self.frames
            for i, (t, path) in enumerate(fr):
                d = (fr[i + 1][0] if i + 1 < len(fr) else end) - t
                f.write(f"file '{path}'\nduration {max(d, 0.001):.4f}\n")
            f.write(f"file '{fr[-1][1]}'\n")
        os.makedirs(CFG.clips_dir, exist_ok=True)
        out = os.path.join(CFG.clips_dir, self.sid + ".mp4")
        start_off = self.frames[0][0] - self.t0
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst, "-vf", "fps=30,format=yuv420p",
                        "-c:v", "libx264", "-crf", "14", "-preset", "slow", "-tune", "stillimage", out], check=True)
        span = max(0.001, end - self.frames[0][0])
        self.fps = round(len(self.frames) / span, 1)
        meta = {"sid": self.sid, "dur": round(end - self.t0, 3), "vo_at": self.lead, "first_frame": round(start_off, 3), "fps": self.fps,
                "focus": self.focus, "marks": self.marks, "keys": self.keys,
                "track": [[round(t - self.t0, 3), i, v] for t, i, v in self.track if self.t0 - 1 <= t <= end + 1]}
        json.dump(meta, open(os.path.join(CFG.clips_dir, self.sid + ".json"), "w"), indent=1)
        shutil.rmtree(self.fdir, ignore_errors=True)
        warn = f"  LOW FRAME RATE (under {CFG.min_fps}): pause screen recorders, GeForce NOW and other GPU-heavy apps, then re-shoot" if self.fps < CFG.min_fps else ""
        print(f"scene {self.sid}: {meta['dur']:.1f} s, {len(self.frames)} frames, {self.fps} fps{warn}", flush=True)


# ---- helpers for shoot files -------------------------------------------------------------------------------------

SCROLLER_JS = "(function f(p) { while (p && p !== document.body) { const o = getComputedStyle(p).overflowY; if (/(auto|scroll)/.test(o) && p.scrollHeight > p.clientHeight + 2) return p; p = p.parentElement; } return document.scrollingElement; })"


def go(path, wait, then=None):
    """Off camera: open BASE + path, wait for a selector, settle."""
    def f(s):
        s.pg.goto(BASE + path); s.pg.wait_for_selector(wait, timeout=30000); s.pg.wait_for_timeout(900)
        if then: then(s)
        s.pg.wait_for_timeout(300)
    return f


def top_at(sel, y=110):
    """Off camera: put the element's top at y (instant)."""
    return lambda s: s.pg.locator(sel).first.evaluate(f"e => {{ const sc = {SCROLLER_JS}(e.parentElement); sc.scrollTop += e.getBoundingClientRect().top - {y}; }}")


def glide_to(sel, y=96):
    """On camera: an eased glide that brings the element's top to y."""
    def f(s):
        s.pg.locator(sel).first.evaluate(f"e => {{ const sc = {SCROLLER_JS}(e.parentElement); window.__glide(sc, sc.scrollTop + e.getBoundingClientRect().top - {y}); }}")
        s.pg.wait_for_timeout(120); s.idle()
    return f


def union(sel, n):
    """Zoom on the bounding rect of the first n matches (a list of rows, a group of tiles)."""
    def f(s):
        s.idle()
        r = s.pg.evaluate("""([sel, n]) => { const L = [...document.querySelectorAll(sel)].slice(0, n).map((e) => e.getBoundingClientRect());
            const x = Math.min(...L.map((r) => r.left)), y = Math.min(...L.map((r) => r.top)), R = Math.max(...L.map((r) => r.right)), B = Math.max(...L.map((r) => r.bottom));
            return [x, y, R - x, B - y]; }""", [sel, n])
        s.zoom(rect=r)
    return f
