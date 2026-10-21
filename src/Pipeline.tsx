import React from 'react';
import { AbsoluteFill, interpolate, Easing } from 'remotion';
import { INK, BRAND, SLATE, SOFT, LINE, RED } from './theme';
import { fadeUp, Source } from './Cards';

/* Pipeline diagram: a row of steps with arrows; new steps are filled in the brand colour; a loop arrow can run back
   (a rework loop, an order sent back). Good for a "today" vs "with the product" pair of cards.
   props: {
     kicker, title,
     boxes: [{kicker, title, sub, isNew}],      // 2-6 boxes
     legend: "New with Acme",                    // shown when any box isNew
     highlight: 1,                               // box index lit on marks.highlight
     loop: {from: 1, to: 0, label: "Missing details, sent back", alert: true},   // drawn on marks.loop
     footnote: "...", source: "..."             // footnote shows on marks.footnote
   } */

const ease = Easing.bezier(0.45, 0, 0.2, 1);
const clamp = { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' } as const;

export const PipelineCard: React.FC<{ t: number; marks: Record<string, number>; props: any }> = ({ t, marks, props: p }) => {
  const boxes: any[] = p.boxes || [];
  const n = Math.max(1, boxes.length);
  const wide = n <= 4;
  const BW = wide ? 330 : 246, GAP = wide ? 74 : 40, BH = wide ? 210 : 230;
  const X0 = (1920 - (n * BW + (n - 1) * GAP)) / 2, Y0 = 420;
  const bx = (i: number) => X0 + i * (BW + GAP);
  const appear = (i: number) => 0.35 + i * 0.22;

  const hiAt = marks.highlight;
  const hi = hiAt != null ? interpolate(t, [hiAt - 0.1, hiAt + 0.4], [0, 1], clamp) : 0;
  const loop = p.loop;
  const loopAt = marks.loop ?? 1.6;
  const loopDraw = loop ? interpolate(t, [loopAt - 0.1, loopAt + 0.8], [0, 1], { ...clamp, easing: ease }) : 0;
  const alert = loop?.alert;
  const from = loop ? bx(loop.from) + BW / 2 : 0, to = loop ? bx(loop.to) + BW / 2 : 0, yb = Y0 + BH + 8;
  const depth = alert ? 120 : 64;
  const loopPath = `M ${from} ${yb} C ${from} ${yb + depth}, ${to} ${yb + depth}, ${to} ${yb + 6}`;
  const loopLen = Math.abs(from - to) + depth * 2;
  const footAt = marks.footnote ?? 2.4;

  return (
    <AbsoluteFill>
      <div style={{ position: 'absolute', left: 0, right: 0, top: 150, textAlign: 'center', ...fadeUp(t, 0.05) }}>
        {p.kicker && <div style={{ display: 'inline-block', fontSize: 22, fontWeight: 700, letterSpacing: '0.14em', textTransform: 'uppercase', color: BRAND, padding: '7px 18px', border: `2px solid ${BRAND}`, borderRadius: 999 }}>{p.kicker}</div>}
        <div style={{ fontSize: 62, fontWeight: 600, color: INK, letterSpacing: '-0.02em', marginTop: 24 }}>{p.title}</div>
      </div>

      {p.legend && boxes.some((b) => b.isNew) && (
        <div style={{ position: 'absolute', right: X0, top: Y0 - 54, display: 'flex', alignItems: 'center', gap: 10, fontSize: 21, color: SLATE, ...fadeUp(t, 1.4) }}>
          <span style={{ width: 18, height: 18, borderRadius: 5, background: BRAND }} />{p.legend}
        </div>
      )}

      <svg width={1920} height={1200} style={{ position: 'absolute', left: 0, top: 0 }}>
        <defs>
          <marker id="ar" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill={SOFT} /></marker>
          <marker id="arl" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill={alert ? RED : SOFT} /></marker>
        </defs>
        {boxes.slice(0, -1).map((_, i) => {
          const a = interpolate(t, [appear(i) + 0.2, appear(i) + 0.5], [0, 1], clamp);
          const x1 = bx(i) + BW + 8, x2 = bx(i + 1) - 8, y = Y0 + BH / 2;
          return <line key={i} x1={x1} y1={y} x2={x1 + (x2 - x1) * a} y2={y} stroke={SOFT} strokeWidth={2.5} markerEnd={a > 0.95 ? 'url(#ar)' : undefined} />;
        })}
        {loopDraw > 0 && (
          <path d={loopPath} fill="none" stroke={alert ? RED : SOFT} strokeWidth={alert ? 4 : 2} strokeDasharray={alert ? `${loopLen}` : '7 7'}
            strokeDashoffset={alert ? loopLen * (1 - loopDraw) : 0} opacity={alert ? 1 : loopDraw} markerEnd={loopDraw > 0.95 ? 'url(#arl)' : undefined} />
        )}
      </svg>

      {boxes.map((b, i) => {
        const isHi = i === p.highlight && hi > 0;
        return (
          <div key={i} style={{ position: 'absolute', left: bx(i), top: Y0, width: BW, height: BH, boxSizing: 'border-box', borderRadius: 22, padding: wide ? '26px 26px' : '22px 20px',
            background: b.isNew ? BRAND : '#fff', color: b.isNew ? '#fff' : INK,
            border: b.isNew ? `2px solid ${BRAND}` : `${isHi ? 2 + hi : 1.5}px solid ${isHi ? BRAND : LINE}`,
            boxShadow: isHi ? `0 0 0 ${6 * hi}px rgba(22,92,168,0.12)` : '0 1px 2px rgba(0,12,31,0.04)',
            display: 'flex', flexDirection: 'column', gap: 10, ...fadeUp(t, appear(i), 0.45) }}>
            {b.kicker && <div style={{ fontSize: wide ? 19 : 17, fontWeight: 600, letterSpacing: '0.1em', textTransform: 'uppercase', color: b.isNew ? 'rgba(255,255,255,0.7)' : SOFT }}>{b.kicker}</div>}
            <div style={{ fontSize: wide ? 31 : 26, fontWeight: 600, lineHeight: 1.2, letterSpacing: '-0.01em' }}>{b.title}</div>
            {b.sub && <div style={{ fontSize: wide ? 22 : 19, lineHeight: 1.35, color: b.isNew ? 'rgba(255,255,255,0.75)' : SLATE, marginTop: 'auto' }}>{b.sub}</div>}
          </div>
        );
      })}

      {loop?.label && loopDraw > 0 && (
        <div style={{ position: 'absolute', left: Math.min(from, to) - 200, width: Math.abs(from - to) + 400, top: yb + depth * 0.78 + (alert ? 14 : 8), textAlign: 'center',
          fontSize: alert ? 24 : 20, fontWeight: alert ? 600 : 500, whiteSpace: 'nowrap', color: alert ? RED : SOFT, opacity: interpolate(t, [loopAt + 0.4, loopAt + 0.8], [0, 1], clamp) }}>
          {loop.label}
        </div>
      )}

      {p.footnote && <div style={{ position: 'absolute', left: 0, right: 0, top: 880, textAlign: 'center', fontSize: 27, color: INK,
        opacity: interpolate(t, [footAt - 0.1, footAt + 0.4], [0, 1], clamp) }}>{p.footnote}</div>}
      <Source t={t} at={1.4} text={p.source} />
    </AbsoluteFill>
  );
};
