import React from 'react';
import {C, FONT, HEAD} from '../../theme.js';
import {fmt, mix, ramp} from '../kit.js';

// Two items with the same point forecast, then their forecast ranges, then stock set from each range.
const Panel = ({name, hist, sd, f, w, ph, bandO, pointO, draw}) => {
  const m = {l: 64, r: 10, t: 8, b: 30};
  const pw = w - m.l - m.r, ih = ph - m.t - m.b, N = 28, H = 20;
  const X = (i) => m.l + (i / (N - 1)) * pw;
  const Y = (v) => m.t + ih - (Math.min(v, 2600) / 2600) * ih;
  const shown = hist.slice(0, Math.max(2, Math.round(hist.length * draw)));
  const fx0 = X(H - 1), fx1 = X(N - 1);
  const band = (k) => `M${fx0},${Y(1000 + k * sd * 0.8)} L${fx1},${Y(1000 + k * sd)} L${fx1},${Y(1000 - k * sd)} L${fx0},${Y(1000 - k * sd * 0.8)} Z`;
  return (
    <svg width={w} height={ph} style={{overflow: 'visible'}}>
      {[0, 1000, 2000].map((v) => (
        <g key={v}>
          <line x1={m.l} x2={w - m.r} y1={Y(v)} y2={Y(v)} stroke={C.grid} strokeWidth={v ? 1.5 : 2.5} />
          <text x={m.l - 10} y={Y(v) + 8} textAnchor="end" fill={C.muted} fontSize={21}>{fmt(v, 0)}</text>
        </g>
      ))}
      <line x1={fx0} x2={fx0} y1={m.t - 4} y2={m.t + ih} stroke={C.muted} strokeWidth={2} strokeDasharray="4 6" />
      <g opacity={bandO}>
        <path d={band(2.05)} fill={C.blue} opacity={0.14} />
        <path d={band(1.28)} fill={C.blue} opacity={0.3} />
      </g>
      <path d={shown.map((v, i) => `${i ? 'L' : 'M'}${X(i)},${Y(v)}`).join(' ')} fill="none" stroke={C.ink} strokeWidth={4} strokeLinejoin="round" />
      <line x1={fx0} x2={fx0 + (fx1 - fx0) * pointO} y1={Y(1000)} y2={Y(1000)} stroke={C.orange} strokeWidth={5} strokeDasharray="12 8" />
      <text x={m.l + 4} y={m.t + 24} fill={C.ink} fontSize={24} fontWeight={700} fontFamily={HEAD}>{name}</text>
      <text x={fx1} y={ph - 4} textAnchor="end" fill={C.muted} fontSize={20}>next 8 weeks</text>
      <text x={m.l} y={ph - 4} fill={C.muted} fontSize={20}>last 20 weeks</text>
    </svg>
  );
};

const Bar = ({label, v, max, col, w, o}) => (
  <div style={{display: 'flex', alignItems: 'center', height: 36 * Math.min(1, o * 1.5), opacity: o, overflow: 'hidden'}}>
    <div style={{width: 190, color: C.text, fontSize: 22}}>{label}</div>
    <div style={{width: (w - 190 - 100) * (v / max), height: 22, background: col, borderRadius: 3}} />
    <div style={{marginLeft: 10, color: col === C.sage ? C.sub : col, fontFamily: HEAD, fontWeight: 700, fontSize: 24}}>{fmt(v, 0)}</div>
  </div>
);

export const Fan = ({d, f, w, h}) => {
  const M = d.model, A = d.acts.map((a) => a.start);
  const ph = Math.round((h - 250) / 2);
  const draw = ramp(f, 6, 54), pointO = ramp(f, 54, 30);
  const bandO = ramp(f, A[1] + 14, 30), pMonthly = ramp(f, A[3] + 16, 40);
  const stockO = ramp(f, A[2] + 10, 26), ruleO = ramp(f, 70, 24);
  const sdB = mix(350, 693, pMonthly);
  const histB = M.B.map((v, i) => (i >= 12 ? mix(v, M.B2[i], pMonthly) : v));
  const ssB = mix(M.ssB, M.ssB2, pMonthly);
  const max = 2600;
  return (
    <div style={{position: 'relative', width: w, height: h, fontFamily: FONT}}>
      <div style={{display: 'flex', justifyContent: 'space-between', color: C.sub, fontSize: 22, marginBottom: 6}}>
        <span>Units a week</span>
        <span style={{display: 'flex', gap: 18, alignItems: 'center'}}>
          <span style={{display: 'flex', alignItems: 'center', gap: 6}}><span style={{width: 26, height: 0, borderTop: `5px dashed ${C.orange}`}} />Point forecast</span>
          <span style={{display: 'flex', alignItems: 'center', gap: 6, opacity: bandO}}><span style={{width: 22, height: 16, background: C.blue, opacity: 0.45}} />80% range</span>
        </span>
      </div>
      <Panel name="Item A" hist={M.A} sd={80} f={f} w={w} ph={ph} bandO={bandO} pointO={pointO} draw={draw} />
      <div style={{height: 8}} />
      <Panel name="Item B" hist={histB} sd={sdB} f={f} w={w} ph={ph} bandO={bandO} pointO={pointO} draw={draw} />
      <div style={{position: 'absolute', top: h - 196, left: 0, width: w}}>
        <div style={{color: C.sub, fontSize: 22, marginBottom: 6, opacity: ruleO}}>Safety stock, units: <span style={{color: C.muted}}>■</span> one week of cover rule <span style={{color: C.ink, opacity: stockO}}>■ set from the range</span></div>
        <Bar label="Item A, rule" v={1000} max={max} col={C.sage} w={w} o={ruleO} />
        <Bar label="Item A, range" v={M.ssA * stockO} max={max} col={C.ink} w={w} o={stockO} />
        <Bar label="Item B, rule" v={1000} max={max} col={C.sage} w={w} o={ruleO} />
        <Bar label="Item B, range" v={ssB * stockO} max={max} col={C.ink} w={w} o={stockO} />
      </div>
    </div>
  );
};
