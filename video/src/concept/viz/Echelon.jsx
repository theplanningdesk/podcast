import React from 'react';
import {C, FONT, HEAD} from '../../theme.js';
import {fmt, mix, ramp} from '../kit.js';

// Central DC over four local warehouses. Bars show safety stock by type; dots are trucks.
const COL = {fast: C.ink, slow: '#E2B45C', cbuf: C.blue};

const Stack = ({x, base, bw, parts, k, label, sub, labelY, o = 1}) => {
  let y = base;
  const total = parts.reduce((s, p) => s + p.v, 0);
  return (
    <g opacity={o}>
      {parts.map((p, i) => {
        const hgt = p.v * k;
        y -= hgt;
        return hgt > 0.5 ? <rect key={i} x={x - bw / 2} y={y} width={bw} height={hgt} fill={COL[p.c]} rx={2} /> : null;
      })}
      <text x={x} y={y - 12} textAnchor="middle" fill={C.ink} fontSize={25} fontWeight={700} fontFamily={HEAD}>€{fmt(total, 2)}M</text>
      <line x1={x - bw / 2 - 14} x2={x + bw / 2 + 14} y1={base} y2={base} stroke={C.sub} strokeWidth={3} />
      <text x={x} y={labelY} textAnchor="middle" fill={C.text} fontSize={23} fontWeight={700}>{label}</text>
      {sub && <text x={x} y={labelY + 26} textAnchor="middle" fill={C.muted} fontSize={20}>{sub}</text>}
    </g>
  );
};

export const Echelon = ({d, f, w, h, fm}) => {
  const M = d.model, A = d.acts.map((a) => a.start);
  const v = fm === 'v';
  const k = v ? 120 : 100;                       // px per €1M
  const cBase = 74 + 1.75 * k, linkTop = cBase + 50, lBase = h - 56, linkBot = lBase - 0.9 * k - 52;
  const cx = w / 2, xs = [0.125, 0.375, 0.625, 0.875].map((t) => t * w);
  const pOpt = ramp(f, A[2] + 16, 50), pTwice = ramp(f, A[3] + 18, 40);
  const st = (key) => mix(mix(M.today[key], M.opt[key], pOpt), M.twice[key], pTwice);
  const grow = ramp(f, 8, 50);
  const slowHi = f >= A[1] && f < A[2] + 10 ? 0.5 + 0.5 * Math.sin((f - A[1]) / 5) : 0;
  const trips = mix(3, 1, pTwice);
  return (
    <div style={{position: 'relative', width: w, height: h, fontFamily: FONT}}>
      <div style={{display: 'flex', gap: 20, color: C.sub, fontSize: 22, alignItems: 'center'}}>
        <span>Safety stock:</span>
        {[['fast', 'Fast movers'], ['slow', 'Slow movers'], ['cbuf', 'Supplier buffer']].map(([c, t]) => (
          <span key={c} style={{display: 'flex', alignItems: 'center', gap: 6}}><span style={{width: 18, height: 18, borderRadius: 3, background: COL[c]}} />{t}</span>
        ))}
      </div>
      <svg width={w} height={h} style={{position: 'absolute', left: 0, top: 0, overflow: 'visible'}}>
        {xs.map((x, i) => (
          <g key={i}>
            <line x1={cx} y1={linkTop} x2={x} y2={linkBot} stroke={C.grid} strokeWidth={4} />
            {[0, 1, 2].map((j) => {
              const t = ((f / 45 + j / 3 + i * 0.13) % 1);
              const o = j === 0 ? 1 : Math.max(0, Math.min(1, trips - j));
              return <circle key={j} cx={cx + (x - cx) * t} cy={linkTop + (linkBot - linkTop) * t} r={7} fill={C.sub} opacity={o * grow * 0.8} />;
            })}
            {pOpt > 0.02 && pOpt < 0.98 && (() => {
              const t = pOpt, s = 0.4 * k * 0.5;
              const px = x + (cx - x) * t, py = linkBot + (linkTop - linkBot) * t;
              return <rect x={px - s / 2} y={py - s / 2} width={s} height={s} fill={COL.slow} opacity={Math.sin(Math.PI * t)} rx={3} />;
            })()}
          </g>
        ))}
        <Stack x={cx} base={cBase} bw={v ? 120 : 110} k={k}
          parts={[{c: 'cbuf', v: st('cbuf') * grow}, {c: 'slow', v: st('cslow') * grow}]}
          label={`Central DC · ${M.central}`} labelY={cBase + 34} />
        {M.nodes.map((n, i) => (
          <g key={n}>
            <Stack x={xs[i]} base={lBase} bw={v ? 84 : 78} k={k}
              parts={[{c: 'fast', v: st('fast') * grow}, {c: 'slow', v: st('slow') * grow}]}
              label={n} labelY={lBase + 34} />
            {slowHi > 0 && st('slow') > 0.05 && (
              <rect x={xs[i] - 50} y={lBase - (st('fast') + st('slow')) * k - 4} width={100} height={st('slow') * k + 8} fill="none"
                stroke={C.orange} strokeWidth={4} opacity={slowHi} rx={4} />
            )}
          </g>
        ))}
        <text x={w} y={cBase + 34} textAnchor="end" fill={C.muted} fontSize={21}>
          {pTwice > 0.5 ? 'Trucks twice a week' : 'Trucks daily'}
        </text>
      </svg>
    </div>
  );
};
