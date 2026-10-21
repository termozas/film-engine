---
name: demo-film
description: Make a narrated product demo film with this kit (voice with word timings, cue-synced browser capture, camera rules, Remotion edit, finish, QA). Use when asked to make, re-cut, fix or check a demo film, product video or walkthrough in this folder.
---

# Demo film

The README in the kit root is the manual. Read its "For Claude" section, then "The workflow", "How to write cues" and "The rules we learned", before changing anything.

Order of work, from the kit root:

1. Check the setup: Node 20+, Python 3.11+ with Playwright, ffmpeg. Check whether `ELEVENLABS_API_KEY` is set without printing it. No key: offer `TTS_BACKEND=kokoro` or `--no-voice`.
2. Prove the pipeline: `bash kit/run.sh examples/hello-demo --no-voice`.
3. New film: copy `examples/hello-demo` to `films/<name>/`. Ask for the audience, the one action the film should lead to, the app URL and port, the login, and the source of every number. Never guess a number or a source.
4. Script: one sentence per scene. `python kit/qa/lint_script.py films/<name>` must show no errors. Show the script to the person before making the voice.
5. Voice: `python kit/tts.py films/<name>`, then `python kit/qa/stt_check.py films/<name>`.
6. Shoot: `python kit/shoot.py films/<name> --draft` while working out cues, then without `--draft`. Every scene needs at least 20 fps.
7. Camera: `python kit/build_data.py films/<name>` must print "camera: no warnings". Fix warnings by removing zoom cues.
8. Render, finish, contact sheets, STT on the master (or `bash kit/run.sh films/<name>` for steps 4 to 8). Look at the contact sheets yourself.
9. Before anything leaves the machine: `bash kit/qa/check_secrets.sh <folder> <private-terms file>`.

Hard rules: no "it" for the product; every on-screen number has a plain-English source; never overwrite a finished file; never stop a process you did not start; never upload or send anything unless asked.
