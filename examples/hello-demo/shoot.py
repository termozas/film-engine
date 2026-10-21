"""Footage for the hello-demo film: one function per footage scene, named after its id in script.json.

  python kit/shoot.py examples/hello-demo            # all footage scenes
  python kit/shoot.py examples/hello-demo s03        # one scene

Each function: prepare the starting page off camera, start recording, fire actions on cue words, finish.
- sc.cue(phrase, fn, early): run fn `early` seconds before the phrase is spoken. Phrases are exact words from the
  scene's text. A click lands best with early=0.5-0.9 (the cursor travels for about half a second first).
- s.click(sel), s.type(sel, text): a visible, eased cursor and real key presses.
- s.zoom(sel): the camera eases onto the element from now on; s.zoom(None) pulls back to the full page.
  build_data.py adds a pull-back before any click outside the zoomed element and ends any zoom held over 3.4 s.
"""
from cap import go


def s02(sc):
    """Type a vendor, press Check. One zoom on the form; both clicks land inside it, so the camera stays put."""
    sc.prepare(go("/", "#vendor"))
    sc.start()
    sc.cue("Type the", lambda s: s.zoom("#check-form"), early=0.35)
    def type_vendor(s):
        s.click("#vendor", after=150)
        s.type("#vendor", "Northwind Supply", delay=28)
    sc.cue("vendor's name", type_vendor, early=0.9)
    sc.cue("press Check", lambda s: s.click("#check", after=300), early=0.6)
    sc.finish()


def s03(sc):
    """The result: zoom on the table, then open one flagged line (the row is inside the zoom: no pull-back)."""
    def ready(s):
        go("/", "#vendor")(s)
        s.pg.fill("#vendor", "Northwind Supply"); s.pg.click("#check"); s.pg.wait_for_selector("#result.on")
        s.pg.wait_for_timeout(600)
    sc.prepare(ready)
    sc.start()
    sc.cue("three lines", lambda s: s.zoom("#lines"), early=0.3)
    sc.cue("purchase order", lambda s: s.click("#row-toner", after=300), early=0.7)
    sc.finish()
