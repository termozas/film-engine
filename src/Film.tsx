import React from 'react';
import { AbsoluteFill, Audio, OffthreadVideo, Sequence, interpolate, Easing, staticFile, useCurrentFrame } from 'remotion';
import { SCENES, DIR, CARDS, VIEW, MUSIC, SFX, CAPTIONS } from './data';
import { NumberCard } from './Cards';
import { fontFamily, INK, BRAND, SLATE, BACKDROP } from './theme';

/* The film: footage scenes sit in a rounded window on a quiet backdrop, with a camera that eases onto the narrated
   element (zoom cues from the shoot, cleaned by kit/build_data.py), a spotlight, captions, scene labels and source
   tags. Card scenes (Cards.tsx) are full-frame animated diagrams and numbers. Everything comes from src/data.ts. */

export const FPS = 30;
export const W = 1920;
export const H = 1200;
const INTRO = Number(CARDS?.intro?.dur ?? 0);   // title card before the first scene (0 = none: the first scene opens the film)
const OUTRO = Number(CARDS?.outro?.dur ?? 0);   // end card after the last scene (0 = none: a cta card ends the film)
const DIP = 0.18;            // scenes butt-join; each dips to the backdrop for a moment instead of a muddy crossfade
const CSS_W = VIEW[0];       // the browser's CSS size; the clip is its 2x capture
const WW = 1728;             // window size, 16:10 like the capture
const WH = Math.round(WW * VIEW[1] / VIEW[0]);
const WX = (W - WW) / 2;
const WY = 44;
const RADIUS = 18;
const K = WW / CSS_W;        // CSS px -> window px
const MAX_ZOOM = 1.9;        // past this, text in a 2x capture goes soft
const MOVE = 0.9;            // seconds for the camera to settle on a new target
const BLUR_SAMPLES = 8;      // motion blur: sub-frame camera positions blended while the camera moves
const SHUTTER = 0.4;         // fraction of a frame the virtual shutter stays open (0.5 = a film camera; lower = crisper)
const MUSIC_LEVEL = 0.16;    // music volume in the pauses
const DUCK = 0.42;           // music under the voice, as a share of MUSIC_LEVEL
const DUCK_RAMP = 0.35;      // seconds for the music to dip and come back

type Focus = { t: number; rect: number[] | null; scale?: number | null };

export const timeline = () => {
  let t = INTRO;
  const starts: number[] = [];
  SCENES.forEach((s) => { starts.push(t); t += s.dur; });
  return { starts, total: t + OUTRO };
};

const ease = Easing.bezier(0.45, 0, 0.2, 1);

type Cam = { s: number; cx: number; cy: number };
const target = (f: Focus | undefined): Cam => {
  if (!f || !f.rect) return { s: 1, cx: WW / 2, cy: WH / 2 };
  const [x, y, w, h] = f.rect.map((v) => v * K);
  // the element fills most of the window, with room around it so what's nearby stays readable
  const fit = Math.min(WW / (w * 1.45), WH / (h * 1.55));
  const s = Math.max(1, Math.min(f.scale ? f.scale * 1.08 : fit, fit, MAX_ZOOM));
  let cx = x + w / 2, cy = y + h / 2;
  cx = Math.min(Math.max(cx, WW / (2 * s)), WW - WW / (2 * s));
  cy = Math.min(Math.max(cy, WH / (2 * s)), WH - WH / (2 * s));
  return { s, cx, cy };
};

function camState(focus: readonly Focus[], t: number) {
  let i = -1;
  for (let k = 0; k < focus.length; k++) if (focus[k].t <= t) i = k;
  const cur = target(i >= 0 ? focus[i] : undefined);
  const prev = i > 0 ? target(focus[i - 1]) : target(undefined);
  const p = i >= 0 ? ease(Math.min(1, Math.max(0, (t - focus[i].t) / MOVE))) : 1;
  return { s: prev.s + (cur.s - prev.s) * p, cx: prev.cx + (cur.cx - prev.cx) * p, cy: prev.cy + (cur.cy - prev.cy) * p };
}

const camCss = (c: Cam) => `translate(${WW / 2}px, ${WH / 2}px) scale(${c.s}) translate(${-c.cx}px, ${-c.cy}px)`;

/* Motion blur for camera moves: while the camera zooms or pans, the clip is drawn at several sub-frame camera
   positions and blended, like a film camera's shutter. Still frames are drawn once, so renders stay fast. */
const CameraBlur: React.FC<{ s: any; t: number }> = ({ s, t }) => {
  const video = <OffthreadVideo src={staticFile(`${DIR.clips}/${s.id}.mp4`)} muted style={{ width: WW, height: WH, display: 'block' }} />;
  const layer = (c: Cam, key: number, op = 1) => (
    <div key={key} style={{ position: 'absolute', left: 0, top: 0, width: WW, height: WH, transform: camCss(c), transformOrigin: '0 0',
      opacity: op, mixBlendMode: op < 1 ? 'plus-lighter' : undefined }}>{video}</div>
  );
  const cams = Array.from({ length: BLUR_SAMPLES }, (_, i) => camState(s.focus, Math.max(0, t - (SHUTTER * i) / (BLUR_SAMPLES - 1) / FPS)));
  const a = cams[0], b = cams[cams.length - 1];
  const travel = Math.abs(a.s - b.s) * WW + (Math.abs(a.cx - b.cx) + Math.abs(a.cy - b.cy)) * a.s;
  if (travel < 0.75) return layer(a, 0);
  return <div style={{ position: 'absolute', inset: 0, isolation: 'isolate' }}>{cams.map((c, i) => layer(c, i, 1 / BLUR_SAMPLES))}</div>;
};

/* Spotlight: dims everything but the narrated element, only while it sits still and visible (see build_data.py).
   It rides the camera transform, so it stays glued to the element. */
type Spot = { t0: number; t1: number; rect: number[] };
const Spotlight: React.FC<{ spots: readonly Spot[]; t: number }> = ({ spots, t }) => {
  const g = (spots || []).find((x) => t >= x.t0 && t <= x.t1 + 0.25);
  if (!g) return null;
  const a = Math.min(interpolate(t, [g.t0, g.t0 + 0.3], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }),
    interpolate(t, [g.t1, g.t1 + 0.25], [1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }));
  if (a <= 0) return null;
  const pad = 10;
  const [x, y, w, h] = [g.rect[0] * K - pad, g.rect[1] * K - pad, g.rect[2] * K + 2 * pad, g.rect[3] * K + 2 * pad];
  return (
    <div style={{ position: 'absolute', left: x, top: y, width: w, height: h, borderRadius: 12, pointerEvents: 'none',
      boxShadow: `0 0 0 4000px rgba(20,20,26,${0.3 * a}), 0 0 0 2px rgba(255,255,255,${0.55 * a})` }} />
  );
};

/* Captions: one line at a time. In "words" mode (film.json "captions") each word lights up as it is spoken. */
const Caption: React.FC<{ caps: readonly any[]; t: number }> = ({ caps, t }) => {
  if (CAPTIONS === 'none') return null;
  const c = caps.find((x, i) => t >= x.t0 - 0.05 && t <= (caps[i + 1] ? Math.min(caps[i + 1].t0 - 0.05, x.t1 + 0.6) : x.t1 + 0.8));
  if (!c) return null;
  const words = CAPTIONS === 'words' && c.words ? c.words.map((w: any, i: number) => (
    <span key={i} style={{ opacity: interpolate(t, [w.s - 0.06, w.s + 0.06], [0.42, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }) }}>{(i ? ' ' : '') + w.w}</span>
  )) : c.text;
  const a = interpolate(t, [c.t0 - 0.05, c.t0 + 0.15], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  return (
    <div style={{ position: 'absolute', left: 0, right: 0, bottom: 70, display: 'flex', justifyContent: 'center', opacity: a }}>
      <div style={{ maxWidth: 1380, padding: '14px 26px', borderRadius: 14, background: 'rgba(20,20,26,0.82)', color: '#fff',
        fontFamily, fontSize: 36, fontWeight: 500, lineHeight: 1.3, textAlign: 'center', letterSpacing: '-0.005em',
        boxShadow: '0 8px 30px rgba(20,20,26,0.25)' }}>{words}</div>
    </div>
  );
};

/* Scene label: a pill at the top left when the label changes ("Setup", "Results") */
const Label: React.FC<{ text: string; t: number }> = ({ text, t }) => {
  const a = interpolate(t, [0.25, 0.75, 3.6, 4.2], [0, 1, 1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const y = interpolate(t, [0.25, 0.75], [14, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: ease });
  return (
    <div style={{ position: 'absolute', left: WX + 36, top: WY + 30, opacity: a, transform: `translateY(${y}px)`, display: 'flex', alignItems: 'center', gap: 14,
      padding: '12px 20px 12px 16px', borderRadius: 999, background: 'rgba(255,255,255,0.95)', boxShadow: '0 6px 24px rgba(20,20,26,0.18)', fontFamily }}>
      <span style={{ width: 12, height: 12, borderRadius: 6, background: BRAND }} />
      <span style={{ fontSize: 28, fontWeight: 600, color: INK }}>{text}</span>
    </div>
  );
};

/* Source tag: a lower third over footage ("Demo data: invented", "Source: ...") */
const SourceTag: React.FC<{ tags: readonly { t0: number; t1: number; text: string }[]; t: number }> = ({ tags, t }) => {
  const g = (tags || []).find((x) => t >= x.t0 && t <= x.t1);
  if (!g) return null;
  const a = interpolate(t, [g.t0, g.t0 + 0.3, g.t1 - 0.3, g.t1], [0, 1, 1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const x = interpolate(t, [g.t0, g.t0 + 0.4], [-16, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: ease });
  return (
    <div style={{ position: 'absolute', left: WX + 36, bottom: 176, opacity: a, transform: `translateX(${x}px)` }}>
      <div style={{ padding: '10px 20px', borderRadius: 12, background: 'rgba(20,20,26,0.82)', color: '#fff', fontFamily, fontSize: 28, fontWeight: 500,
        letterSpacing: '-0.005em' }}>{g.text}</div>
    </div>
  );
};

const Voice: React.FC<{ s: any }> = ({ s }) => (
  <Sequence from={Math.round(s.voAt * FPS)}>
    <Audio src={staticFile(`${DIR.vo}/${s.id}.mp3`)} volume={0.95} endAt={Math.max(1, Math.floor((s.voLen - 0.1) * FPS))} />
  </Sequence>
);

const Scene: React.FC<{ s: any; showLabel?: boolean }> = ({ s, showLabel = true }) => {
  const t = useCurrentFrame() / FPS;
  const fade = interpolate(t, [0, DIP, s.dur - DIP, s.dur], [0, 1, 1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  if (s.card) return (
    <AbsoluteFill>
      <AbsoluteFill style={{ opacity: fade }}>
        <NumberCard kind={s.card} t={t} marks={s.cardMarks || {}} props={s.props || {}} />
        {s.card !== 'cta' && <Caption caps={s.caps} t={t - s.voAt} />}
      </AbsoluteFill>
      <Voice s={s} />
    </AbsoluteFill>
  );
  const cam = camState(s.focus, t);
  return (
    <AbsoluteFill>
      <AbsoluteFill style={{ opacity: fade }}>
        <div style={{ position: 'absolute', left: WX, top: WY, width: WW, height: WH, borderRadius: RADIUS, overflow: 'hidden', background: '#fff',
          boxShadow: '0 30px 80px rgba(20,20,26,0.20), 0 8px 24px rgba(20,20,26,0.12), 0 0 0 1px rgba(20,20,26,0.08)' }}>
          <CameraBlur s={s} t={t} />
          <div style={{ position: 'absolute', left: 0, top: 0, width: WW, height: WH, transform: camCss(cam), transformOrigin: '0 0' }}>
            <Spotlight spots={s.spots} t={t} />
          </div>
        </div>
        {showLabel && <Label text={s.label} t={t} />}
        <SourceTag tags={s.tags} t={t - s.voAt} />
        <Caption caps={s.caps} t={t - s.voAt} />
      </AbsoluteFill>
      <Voice s={s} />
      <Sfx s={s} />
    </AbsoluteFill>
  );
};

/* Interface sounds: a soft click on every mouse press and a light tick per key, at the moments the capture logged.
   Off when public/sfx/ has no sounds (kit/make_sfx.sh makes them) or film.json sets "sfx": false. */
const Sfx: React.FC<{ s: any }> = ({ s }) => !SFX ? null : (
  <>
    {(s.sfx || []).map((e: any, i: number) => (
      <Sequence key={i} from={Math.max(0, Math.round(e.t * FPS))} durationInFrames={Math.round(0.4 * FPS)}>
        <Audio src={staticFile(e.k === 'click' ? SFX.click : SFX.keys[i % SFX.keys.length])} volume={e.k === 'click' ? 0.55 : 0.3} />
      </Sequence>
    ))}
  </>
);

/* Title card (cards.json intro / outro, shown when its "dur" is above 0) */
const TitleCard: React.FC<{ kicker?: string; title?: string; sub?: string; dur: number }> = ({ kicker, title, sub, dur }) => {
  const t = useCurrentFrame() / FPS;
  const a = interpolate(t, [0, 0.6, dur - 0.6, dur], [0, 1, 1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const y = interpolate(t, [0, 0.9], [18, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: ease });
  return (
    <AbsoluteFill style={{ justifyContent: 'center', alignItems: 'center', fontFamily }}>
      <div style={{ opacity: a, transform: `translateY(${y}px)`, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 26, textAlign: 'center' }}>
        {kicker && <div style={{ fontSize: 22, fontWeight: 600, letterSpacing: '0.16em', textTransform: 'uppercase', color: BRAND, padding: '6px 16px', border: `2px solid ${BRAND}`, borderRadius: 999 }}>{kicker}</div>}
        <div style={{ fontSize: 112, fontWeight: 600, color: INK, letterSpacing: '-0.03em', lineHeight: 1.0, maxWidth: 1500 }}>{title}</div>
        {sub && <div style={{ fontSize: 32, color: SLATE, maxWidth: 1500, lineHeight: 1.5, whiteSpace: 'pre-line' }}>{sub}</div>}
      </div>
    </AbsoluteFill>
  );
};

/* Music ducks under the narration: the spoken stretches come from the word timings, so the dip is exact. */
const speech: [number, number][] = (() => {
  const { starts } = timeline();
  const iv: [number, number][] = [];
  SCENES.forEach((s, i) => (s.caps || []).forEach((c: any) => iv.push([starts[i] + s.voAt + c.t0, starts[i] + s.voAt + c.t1])));
  iv.sort((a, b) => a[0] - b[0]);
  const out: [number, number][] = [];
  for (const x of iv) { const l = out[out.length - 1]; if (l && x[0] - l[1] < 0.5) l[1] = Math.max(l[1], x[1]); else out.push([...x] as [number, number]); }
  return out;
})();

const musicVolume = (t: number, total: number) => {
  let dist = Infinity;
  for (const [a, b] of speech) dist = Math.min(dist, t < a ? a - t : t > b ? t - b : 0);
  const duck = Math.max(0, Math.min(1, 1 - dist / DUCK_RAMP));
  const fade = interpolate(t, [0, 2, total - 3, total], [0, 1, 1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  return MUSIC_LEVEL * fade * (1 - duck * (1 - DUCK));
};

export const Film: React.FC = () => {
  const { starts, total } = timeline();
  return (
    <AbsoluteFill>
      <AbsoluteFill style={{ background: BACKDROP }} />
      {INTRO > 0 && <Sequence durationInFrames={Math.round(INTRO * FPS)}>
        <TitleCard {...CARDS.intro} dur={INTRO} />
      </Sequence>}
      {SCENES.map((s, i) => (
        <Sequence key={s.id} from={Math.round(starts[i] * FPS)} durationInFrames={Math.max(1, Math.round(s.dur * FPS))}>
          <Scene s={s} showLabel={!!s.label && (i === 0 || SCENES[i - 1].label !== s.label)} />
        </Sequence>
      ))}
      {OUTRO > 0 && <Sequence from={Math.round((total - OUTRO) * FPS)} durationInFrames={Math.round(OUTRO * FPS)}>
        <TitleCard {...CARDS.outro} dur={OUTRO} />
      </Sequence>}
      {MUSIC && <Audio src={staticFile(MUSIC)} volume={(f) => musicVolume(f / FPS, total)} />}
    </AbsoluteFill>
  );
};
