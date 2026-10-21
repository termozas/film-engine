"""Shared text normalisation for comparing a script with what a speech model heard (STT check, Kokoro alignment)."""
import re

ONES = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split()
TENS = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()
BREAK = re.compile(r"\s*<break[^>]*/>\s*")


def spell(n):
    if n < 20: return ONES[n]
    if n < 100: return TENS[n // 10] + ("" if n % 10 == 0 else " " + ONES[n % 10])
    if n < 1000: return ONES[n // 100] + " hundred" + ("" if n % 100 == 0 else " " + spell(n % 100))
    for d, w in ((10 ** 9, "billion"), (10 ** 6, "million"), (1000, "thousand")):
        if n >= d:
            return spell(n // d) + " " + w + ("" if n % d == 0 else " " + spell(n % d))
    return str(n)


def strip_breaks(t):
    return BREAK.sub(" ", t or "").strip()


def norm(t):
    """Lower-case word tokens with punctuation gone and digits spelled out ("$60,000" -> sixty thousand)."""
    t = strip_breaks(t)
    t = re.sub(r"\[[^\]]*\]|\([^)]*\)", " ", t)                          # [music], (laughs)
    t = t.replace("’", "'").replace("%", " percent").replace("$", " ")
    t = re.sub(r"(\d),(\d{3})", r"\1\2", t)
    t = re.sub(r"\d+", lambda m: " " + spell(int(m.group())) + " " if len(m.group()) < 10 else m.group(), t)
    t = t.lower().replace("-", " ").replace("'", "")
    return re.sub(r"[^a-z0-9 ]", " ", t).split()
