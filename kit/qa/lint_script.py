"""Script check: the narration and on-screen text against the rules we learned. Run it before generating voice.

  python kit/qa/lint_script.py <film>

Errors (exit 1):
  - "it" / "it's" / "its" in narration (name the product instead; list scene ids in film.json "allow_it" when the
    word does not refer to the product)
  - a card that shows a number without a plain-English "source" line, or a source that is a file path
  - any word from film.json "banned" (customer names, code names), anywhere in the film folder's text files
Warnings:
  - AI-sounding phrasing ("delve", "leverage", "not just X, but Y", em dashes...); rewrite it the way a person would say it
  - more than one sentence in a scene; digits in narration (spell numbers so the voice reads them right);
    hype words; claims nobody can back ("guaranteed", "never misses").
"""
import json
import os
import re
import sys

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KIT)
import config  # noqa: E402
from textnorm import strip_breaks  # noqa: E402

IT = re.compile(r"\b(it|it's|it’s|its|itself)\b", re.I)
HYPE = re.compile(r"\b(revolutionary|game[- ]chang\w*|ai[- ]powered|seamless\w*|cutting[- ]edge|supercharg\w*|unlock\w*|effortless\w*|next[- ]gen\w*|magic\w*|10x)\b", re.I)
OVERCLAIM = re.compile(r"\b(guarantee\w*|never miss\w*|always catch\w*|100 ?%|perfect accuracy|catches everything)\b", re.I)
AI_WORDS = re.compile(r"\b(delv\w*|leverag\w*|robust\w*|streamlin\w*|elevat\w*|empower\w*|harness\w*|unleash\w*|"
                      r"revolutioni[sz]\w*|transformative|pivotal|crucial|paramount|testament|tapestry|realm|landscape|"
                      r"embark\w*|foster\w*|holistic|synerg\w*|meticulous\w*|navigat\w* the|dive into|deep dive|"
                      r"fast-paced|ever-evolving|today's (digital |modern )?world|look no further|say goodbye to|"
                      r"to the next level|at the end of the day|in a world where|whether you're|imagine a world|"
                      r"designed to help|(?:isn't|is not|it's not|not) just [^.,]{1,40},? but|not only [^.]{1,60} but also|"
                      r"here's the thing|let's be honest|the best part)\b", re.I)
DASH = re.compile(r"—|–| -- ")
NUMWORD = re.compile(r"\d|\b(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand|million|percent)\b", re.I)
PATHY = re.compile(r"(\w/\w.*\.(md|json|py|csv|txt|ts))|(\.(md|json|py|csv)\b)")


def texts(obj):
    """Every string inside a card's props (recursively)."""
    if isinstance(obj, str): yield obj
    elif isinstance(obj, dict):
        for v in obj.values(): yield from texts(v)
    elif isinstance(obj, list):
        for v in obj: yield from texts(v)


def has_number(obj):
    if isinstance(obj, bool): return False
    if isinstance(obj, (int, float)): return True
    if isinstance(obj, str): return bool(re.search(r"\d", obj))
    if isinstance(obj, dict): return any(has_number(v) for k, v in obj.items() if k not in ("source", "color", "logo", "mark"))
    if isinstance(obj, list): return any(has_number(v) for v in obj)
    return False


def main():
    film, _, _ = config.film_arg(sys.argv)
    c = config.load(film)
    S = config.script(c)
    errors, warns = [], []
    banned = [b for b in c.banned if b.strip()]
    for s in S:
        sid, text = s["id"], strip_breaks(s["text"])
        props = s.get("props", {})
        screen = list(texts(props)) + [t["text"] for t in s.get("tags", [])] + [s.get("label", "")]
        if IT.search(text) and sid not in c.allow_it:
            errors.append(f"{sid}: \"{IT.search(text).group()}\" in narration; name the product or rephrase (or add {sid} to allow_it)")
        for where, t in [("narration", text)] + [("screen", x) for x in screen]:
            if HYPE.search(t): warns.append(f"{sid}: hype word on {where}: {HYPE.search(t).group()!r}")
            ai = sorted({m.group().lower() for m in AI_WORDS.finditer(t)})
            if ai: warns.append(f"{sid}: AI-sounding phrasing on {where}: {', '.join(repr(x) for x in ai)}; say it the way a person would")
            if DASH.search(t): warns.append(f"{sid}: dash on {where}; use a comma, a colon or two sentences")
            if OVERCLAIM.search(t): warns.append(f"{sid}: claim a test cannot back on {where}: {OVERCLAIM.search(t).group()!r}")
        n = len(re.findall(r"[.?!](\s|$)", text))
        if n > 1: warns.append(f"{sid}: {n} sentences; aim for one sentence per scene")
        if re.search(r"\d", text): warns.append(f"{sid}: digits in narration; spell numbers out so the voice reads them right")
        if s.get("card") and s["card"] != "cta" and has_number(props):
            src = props.get("source", "")
            if not src.strip(): errors.append(f"{sid}: card shows numbers but has no \"source\" line")
            elif PATHY.search(src): errors.append(f"{sid}: source is a file path ({src!r}); write it in plain English")
        if not s.get("card") and NUMWORD.search(text) and not any("source" in t["text"].lower() or ":" in t["text"] for t in s.get("tags", [])):
            warns.append(f"{sid}: number spoken over footage; if it is a claim, add a source tag")
    if banned:
        rx = re.compile("|".join(re.escape(b) for b in banned), re.I)
        for root, _, files in os.walk(c.film_dir):
            for f in files:
                if f != "film.json" and f.endswith((".json", ".py", ".html", ".md", ".txt", ".css", ".js", ".tsx", ".ts")):
                    p = os.path.join(root, f)
                    for k, line in enumerate(open(p, errors="ignore"), 1):
                        if rx.search(line):
                            errors.append(f"{os.path.relpath(p, c.film_dir)}:{k}: banned word {rx.search(line).group()!r}")
    for w in warns: print("warning:", w)
    for e in errors: print("ERROR:  ", e)
    print(f"{c.name}: {len(errors)} errors, {len(warns)} warnings")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
