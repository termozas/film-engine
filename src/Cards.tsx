import React from 'react';
import { AbsoluteFill, Img, interpolate, Easing, staticFile } from 'remotion';
import { fontFamily, INK, BRAND, SLATE, SOFT, LINE, WASH, AMBER } from './theme';
import { PipelineCard } from './Pipeline';

/* Animated cards. A card scene in script.json names its kind ("card": "number") and gives its content in "props";
   "marks" name words in the narration ({"count": "four hours"}) and the card animates when they are spoken.
   Kinds:
     number    1-3 counters that count up on their mark            props: kicker, title, sub, stats[], source
     bars      one total and a stacked bar of its parts             props: kicker, title, total, parts[], source
     timeline  steps on a line; one can be struck out (a step removed)  props: kicker, title, steps[], start, end, strike, headline, sub, source
     pipeline  boxes and arrows, new steps filled, a loop back      props: see Pipeline.tsx
     cta       plain end card                                        props: title, sub, footnote, logo
   Every card that shows a number carries a plain-English source line (kit/qa/lint_script.py checks this). */

const ease = Easing.bezier(0.45, 0, 0.2, 1);
const clamp = { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' } as const;

type Props = { kind: string; t: number; marks: Record<string, number>; props: any };

export const fadeUp = (t: number, at: number, d = 0.5) => ({
  opacity: interpolate(t, [at, at + d], [0, 1], clamp),
  transform: `translateY(${interpolate(t, [at, at + d], [16, 0], { ...clamp, easing: ease })}px)`,
});
const count = (t: number, at: number, to: number, d = 1.1) => interpolate(t, [at, at + d], [0, to], { ...clamp, easing: ease });
const fmt = (n: number, decimals = 0) => n.toLocaleString('en-US', { minimumFractionDigits: decimals, maximumFractionDigits: decimals });

const Kicker: React.FC<{ text?: string; t: number }> = ({ text, t }) => !text ? null : (
  <div style={{ display: 'inline-block', fontSize: 22, fontWeight: 700, letterSpacing: '0.14em', textTransform: 'uppercase', color: BRAND,
    padding: '7px 18px', border: `2px solid ${BRAND}`, borderRadius: 999, ...fadeUp(t, 0.05) }}>{text}</div>
);

export const Source: React.FC<{ text?: string; t: number; at?: number }> = ({ text, t, at = 1.0 }) => !text ? null : (
  <div style={{ position: 'absolute', left: 160, right: 160, bottom: 165, textAlign: 'center', fontSize: 23, lineHeight: 1.45, color: SOFT,
    opacity: interpolate(t, [at, at + 0.6], [0, 1], clamp), whiteSpace: 'pre-line' }}>{text}</div>
);

const Head: React.FC<{ p: any; t: number }> = ({ p, t }) => (
  <div style={{ position: 'absolute', left: 0, right: 0, top: 150, textAlign: 'center' }}>
    <Kicker text={p.kicker} t={t} />
    {p.title && <div style={{ fontSize: 62, fontWeight: 600, color: INK, letterSpacing: '-0.02em', marginTop: 24, ...fadeUp(t, 0.2) }}>{p.title}</div>}
    {p.sub && <div style={{ fontSize: 30, color: SLATE, marginTop: 18, ...fadeUp(t, 0.9) }}>{p.sub}</div>}
  </div>
);

/* number: {stats: [{value, prefix, suffix, decimals, label, of, mark}]} */
const NumberStats: React.FC<Props> = ({ t, marks, props: p }) => {
  const stats: any[] = p.stats || [];
  return (
    <AbsoluteFill>
      <Head p={p} t={t} />
      <div style={{ position: 'absolute', left: 0, right: 0, top: stats.length > 1 ? 520 : 470, display: 'flex', justifyContent: 'center', gap: 160 }}>
        {stats.map((s, i) => {
          const at = (s.mark && marks[s.mark] != null ? marks[s.mark] : 0.8 + i * 0.9) - 0.2;
          return (
            <div key={i} style={{ textAlign: 'center', ...fadeUp(t, at) }}>
              <div style={{ fontSize: stats.length > 1 ? 130 : 170, fontWeight: 700, color: INK, lineHeight: 1, letterSpacing: '-0.02em', fontVariantNumeric: 'tabular-nums' }}>
                {s.prefix || ''}{fmt(count(t, at, Number(s.value), s.dur ?? 1.1), s.decimals || 0)}{s.suffix || ''}
                {s.of != null && <span style={{ color: SOFT, fontWeight: 600 }}> / {s.of}</span>}
              </div>
              <div style={{ fontSize: 30, color: SLATE, marginTop: 14, maxWidth: 560 }}>{s.label}</div>
            </div>
          );
        })}
      </div>
      <Source t={t} at={1.2} text={p.source} />
    </AbsoluteFill>
  );
};

/* bars: {total: {value, prefix, suffix}, parts: [{label, value, color}], unit} */
const Bars: React.FC<Props> = ({ t, marks, props: p }) => {
  const a0 = marks.grow ?? 1.2, l0 = marks.parts ?? a0 + 1.2;
  const BW = 1300, X = (1920 - BW) / 2, Y = 640, BH = 92;
  const parts: any[] = p.parts || [];
  const sum = parts.reduce((s, x) => s + Number(x.value), 0) || 1;
  const grow = interpolate(t, [a0 - 0.2, a0 + 1.0], [0, 1], { ...clamp, easing: ease });
  const colors = [BRAND, AMBER, SLATE, SOFT];
  const total = p.total || { value: sum };
  let x = 0;
  return (
    <AbsoluteFill>
      <Head p={p} t={t} />
      <div style={{ position: 'absolute', left: 0, right: 0, top: 430, textAlign: 'center', ...fadeUp(t, a0 - 0.3) }}>
        <span style={{ fontSize: 132, fontWeight: 700, color: INK, letterSpacing: '-0.02em', fontVariantNumeric: 'tabular-nums' }}>
          {total.approx ? '≈ ' : ''}{total.prefix || ''}{fmt(count(t, a0 - 0.3, Number(total.value), 1.2), total.decimals || 0)}{total.suffix || ''}
        </span>
      </div>
      <div style={{ position: 'absolute', left: X, top: Y, width: BW, height: BH, borderRadius: 14, background: WASH, overflow: 'hidden', ...fadeUp(t, a0 - 0.4) }}>
        {parts.map((pt, i) => {
          const w = (BW * Number(pt.value) / sum) * grow;
          const el = <div key={i} style={{ position: 'absolute', left: x, top: 0, width: w, height: BH, background: pt.color || colors[i % colors.length] }} />;
          x += w; return el;
        })}
      </div>
      <div style={{ position: 'absolute', left: X, width: BW, top: Y + BH + 34, display: 'flex', justifyContent: 'space-between', gap: 30 }}>
        {parts.map((pt, i) => (
          <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 14, fontSize: 30, color: INK, ...fadeUp(t, l0 - 0.2 + i * 0.5) }}>
            <span style={{ width: 22, height: 22, borderRadius: 6, background: pt.color || colors[i % colors.length], flex: 'none' }} />
            <b style={{ fontWeight: 700 }}>{p.unit || ''}{fmt(Number(pt.value))}</b>
            <span style={{ color: SLATE }}>{pt.label}</span>
          </div>
        ))}
      </div>
      <Source t={t} at={1.4} text={p.source} />
    </AbsoluteFill>
  );
};

/* timeline: {steps: ["Step 1", ...], start, end, strike: index, headline, note} */
const Timeline: React.FC<Props> = ({ t, marks, props: p }) => {
  const steps: string[] = p.steps || [];
  const s0 = marks.steps ?? 1.0, x0 = marks.strike ?? s0 + 1.5, h0 = marks.headline ?? x0 + 0.6;
  const X0 = 300, X1 = 1620, Y = p.headline ? 560 : 640;
  const bar = interpolate(t, [0.5, s0 + steps.length * 0.16 + 0.6], [0, 1], { ...clamp, easing: ease });
  const pos = (i: number) => steps.length === 1 ? 0.5 : 0.08 + i * (0.78 / (steps.length - 1));
  const gone = p.strike != null ? interpolate(t, [x0, x0 + 0.8], [0, 1], { ...clamp, easing: ease }) : 0;
  return (
    <AbsoluteFill>
      <Head p={p} t={t} />
      <svg width={1920} height={1200} style={{ position: 'absolute', left: 0, top: 0 }}>
        <line x1={X0} y1={Y} x2={X1} y2={Y} stroke={LINE} strokeWidth={10} strokeLinecap="round" />
        <line x1={X0} y1={Y} x2={X0 + (X1 - X0) * bar} y2={Y} stroke={BRAND} strokeWidth={10} strokeLinecap="round" />
        {steps.map((_, i) => {
          const at = s0 - 0.4 + i * 0.16, a = interpolate(t, [at, at + 0.35], [0, 1], { ...clamp, easing: ease });
          const struck = i === p.strike;
          return <circle key={i} cx={X0 + (X1 - X0) * pos(i)} cy={Y} r={22 * a} fill={struck ? '#fff' : BRAND} stroke={struck ? AMBER : BRAND} strokeWidth={6}
            opacity={a * (struck ? 1 - 0.75 * gone : 1)} strokeDasharray={struck && gone > 0.5 ? '8 7' : undefined} />;
        })}
      </svg>
      {steps.map((label, i) => {
        const struck = i === p.strike;
        return <div key={i} style={{ position: 'absolute', left: X0 + (X1 - X0) * pos(i) - 100, width: 200, top: Y + 40, textAlign: 'center', fontSize: 25, fontWeight: 600,
          color: struck ? AMBER : INK, textDecoration: struck && gone > 0.5 ? 'line-through' : 'none', ...fadeUp(t, s0 - 0.4 + i * 0.16, 0.35) }}>{label}</div>;
      })}
      {p.start && <div style={{ position: 'absolute', left: X0 - 120, width: 240, top: Y - 92, textAlign: 'center', fontSize: 24, color: SLATE, ...fadeUp(t, 0.4) }}>{p.start}</div>}
      {p.end && <div style={{ position: 'absolute', left: X1 - 120, width: 240, top: Y - 92, textAlign: 'center', fontSize: 24, color: SLATE, ...fadeUp(t, 0.4) }}>{p.end}</div>}
      {p.headline && <div style={{ position: 'absolute', left: 0, right: 0, top: Y + 170, textAlign: 'center', ...fadeUp(t, h0 - 0.2) }}>
        <div style={{ fontSize: 76, fontWeight: 700, color: INK, letterSpacing: '-0.02em' }}>{p.headline}</div>
        {p.note && <div style={{ fontSize: 32, color: SLATE, marginTop: 14 }}>{p.note}</div>}
      </div>}
      <Source t={t} at={1.2} text={p.source} />
    </AbsoluteFill>
  );
};

/* cta: plain end card. logo: a file in public/ (optional) */
const Cta: React.FC<Props> = ({ t, props: p }) => (
  <AbsoluteFill style={{ justifyContent: 'center', alignItems: 'center' }}>
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 34, textAlign: 'center' }}>
      {p.logo && <Img src={staticFile(p.logo)} style={{ height: 150, ...fadeUp(t, 0.0, 0.6) }} />}
      {p.brand && !p.logo && <div style={{ fontSize: 44, fontWeight: 700, color: BRAND, letterSpacing: '-0.01em', ...fadeUp(t, 0.0, 0.6) }}>{p.brand}</div>}
      <div style={{ fontSize: 76, fontWeight: 600, color: INK, letterSpacing: '-0.02em', ...fadeUp(t, 0.35, 0.6) }}>{p.title}</div>
      {p.sub && <div style={{ fontSize: 30, color: SLATE, ...fadeUp(t, 1.2, 0.6) }}>{p.sub}</div>}
    </div>
    {p.footnote && <div style={{ position: 'absolute', left: 120, right: 120, bottom: 120, textAlign: 'center', fontSize: 22, color: SOFT, opacity: interpolate(t, [1.6, 2.2], [0, 1], clamp) }}>
      {p.footnote}
    </div>}
  </AbsoluteFill>
);

export const NumberCard: React.FC<Props> = (p) => {
  const C: React.FC<Props> = ({ number: NumberStats, bars: Bars, timeline: Timeline, pipeline: PipelineCard, cta: Cta } as any)[p.kind] ?? NumberStats;
  return <AbsoluteFill style={{ fontFamily }}><C {...p} /></AbsoluteFill>;
};
