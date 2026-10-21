"""Word timings for a take that came without them (Kokoro): forced alignment with faster-whisper.

Whisper transcribes the take with word_timestamps=True; its words are matched to the script's own words, so the
output always holds the script words (the shoot's cues match them) with whisper's times. Script words whisper
missed or heard differently get times spread between their matched neighbours. Output format matches ElevenLabs:
[{"w": word, "s": start, "e": end}, ...].
"""
import difflib
import os

from textnorm import norm, strip_breaks

_model = None


def whisper_words(path, model_name=None, names=()):
    global _model
    from faster_whisper import WhisperModel
    if _model is None:
        _model = WhisperModel(model_name or os.environ.get("WHISPER_MODEL", "small.en"), device="cpu", compute_type="int8")
    prompt = ("Names: " + ", ".join(names) + ".") if names else None
    segs, _ = _model.transcribe(path, language="en", word_timestamps=True, beam_size=5, initial_prompt=prompt)
    return [(w.word.strip(), float(w.start), float(w.end)) for sg in segs for w in sg.words]


def align(text, path, dur, model_name=None, names=()):
    words = strip_breaks(text).split()
    ref, owner = [], []                      # script tokens and the script word each belongs to
    for i, w in enumerate(words):
        for t in norm(w) or [""]:
            ref.append(t); owner.append(i)
    hyp, times = [], []
    for w, s, e in whisper_words(path, model_name, names):
        toks = norm(w)
        for k, t in enumerate(toks):         # a word heard as "38" -> two tokens sharing its span
            a = s + (e - s) * k / len(toks); b = s + (e - s) * (k + 1) / len(toks)
            hyp.append(t); times.append((a, b))
    span = [[None, None] for _ in words]
    for blk in difflib.SequenceMatcher(a=ref, b=hyp, autojunk=False).get_matching_blocks():
        for k in range(blk.size):
            i = owner[blk.a + k]; a, b = times[blk.b + k]
            span[i][0] = a if span[i][0] is None else min(span[i][0], a)
            span[i][1] = b if span[i][1] is None else max(span[i][1], b)
    matched = sum(1 for s in span if s[0] is not None)
    # fill gaps: unmatched runs share the time between their neighbours, by length
    i = 0
    while i < len(words):
        if span[i][0] is not None:
            i += 1; continue
        j = i
        while j < len(words) and span[j][0] is None:
            j += 1
        t0 = span[i - 1][1] if i > 0 else 0.05
        t1 = span[j][0] if j < len(words) else dur
        if t1 <= t0: t1 = t0 + 0.1 * (j - i)
        tot = sum(len(words[k]) + 1 for k in range(i, j)); t = t0
        for k in range(i, j):
            d = (t1 - t0) * (len(words[k]) + 1) / tot
            span[k] = [t, t + d]; t += d
        i = j
    out = [{"w": w, "s": round(s[0], 3), "e": round(s[1], 3)} for w, s in zip(words, span)]
    return out, matched / max(1, len(words))
