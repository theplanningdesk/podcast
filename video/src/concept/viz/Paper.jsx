import React from 'react';
import {C, FONT, HEAD} from '../../theme.js';
import {fmt, ramp} from '../kit.js';

// Generic research visual, filled from the paper by the research writer (no code per paper):
//   flow     the method as 3 to 5 steps; steps light up per act
//   compare  up to 4 rows from one of the paper's tables: a bar metric plus an optional right-hand metric
//   trend    optional line from a table (x, y), shown from a given act
// Every number comes from the paper; the JSON's source.checked says where.
const actStart = (d, i) => (i <= 0 ? 0 : d.acts[Math.min(i, d.acts.length - 1)].start);

const Flow = ({d, f, w, flow, v}) => {
  const n = flow.steps.length, gap = 18, bw = (w - gap * (n - 1)) / n;
  return (
    <div>
      {flow.title && <div style={{color: C.sub, fontSize: 23, marginBottom: 10}}>{flow.title}</div>}
      <div style={{display: 'flex', gap}}>
        {flow.steps.map((s, i) => {
          const at = actStart(d, (flow.reveal || [])[i] ?? 0);
          const o = ramp(f, at + 6 + i * 6, 16);
          const lit = (flow.lit || []).some(([act, idx]) => idx === i && f >= actStart(d, act) + 10 && (act === 3 || f < actStart(d, act + 1)));
          return (
            <div key={i} style={{width: bw, minHeight: v ? 128 : 92, borderRadius: 10, padding: '12px 12px', boxSizing: 'border-box', opacity: Math.max(0.18, o),
              background: lit ? C.ink : C.paper2, color: lit ? C.paper : C.text, fontSize: v ? 24 : 21, lineHeight: 1.22, fontWeight: lit ? 700 : 400,
              position: 'relative', display: 'flex', alignItems: 'center'}}>
              {s}
              {i < n - 1 && <div style={{position: 'absolute', right: -gap + 2, top: '50%', marginTop: -9, width: 0, height: 0,
                borderTop: '9px solid transparent', borderBottom: '9px solid transparent', borderLeft: `12px solid ${C.muted}`}} />}
            </div>
          );
        })}
      </div>
    </div>
  );
};

const Compare = ({d, f, w, cmp, v}) => {
  const max = Math.max(...cmp.rows.map((r) => r.value)) * 1.02;
  return (
    <div>
      <div style={{display: 'flex', justifyContent: 'space-between', color: C.sub, fontSize: 22, marginBottom: 4}}>
        <span>{cmp.title}</span>{cmp.rightTitle && <span>{cmp.rightTitle}</span>}
      </div>
      {cmp.rows.map((r, i) => {
        const o = ramp(f, actStart(d, r.act ?? 0) + 10 + (r.act ? 0 : 30), 22);
        const best = i === cmp.best;
        return (
          <div key={i} style={{opacity: o, marginTop: v ? 22 : 7}}>
            <div style={{color: C.text, fontSize: 23, fontWeight: best ? 700 : 400}}>{r.label}</div>
            <div style={{display: 'flex', alignItems: 'center', marginTop: 4}}>
              <div style={{width: (w - 250) * (r.value / max) * o, height: v ? 26 : 21, background: best ? C.ink : C.sage, borderRadius: 3}} />
              <div style={{marginLeft: 12, fontFamily: HEAD, fontWeight: 700, fontSize: 28, color: best ? C.ink : C.sub}}>
                {fmt(r.value, cmp.decimals ?? 1)}{cmp.unit || ''}
              </div>
              {r.right != null && (
                <div style={{marginLeft: 'auto', fontFamily: HEAD, fontWeight: 700, fontSize: 28, color: best && cmp.rightWorse ? C.orange : C.sub}}>
                  {fmt(r.right, cmp.rightDecimals ?? 0)}{cmp.rightUnit || ''}
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
};

const Trend = ({d, f, w, h, tr}) => {
  const at = actStart(d, tr.act ?? 3);
  const o = ramp(f, at + 6, 16), draw = ramp(f, at + 14, 50);
  const m = {l: 60, r: 14, t: 10, b: 40}, pw = w - m.l - m.r, ph = h - m.t - m.b - 30;
  const xs = tr.x, ys = tr.y, x0 = Math.min(...xs), x1 = Math.max(...xs);
  const y0 = tr.yMin ?? Math.min(0, ...ys), y1 = tr.yMax ?? Math.max(...ys) * 1.1;
  const X = (x) => m.l + ((x - x0) / (x1 - x0 || 1)) * pw, Y = (y) => m.t + ph - ((y - y0) / (y1 - y0 || 1)) * ph;
  const n = Math.max(2, Math.ceil(xs.length * draw));
  return (
    <div style={{opacity: o}}>
      <div style={{color: C.sub, fontSize: 22}}>{tr.title}</div>
      <svg width={w} height={h - 30} style={{overflow: 'visible'}}>
        {[y0, (y0 + y1) / 2, y1].map((t, i) => (
          <g key={i}>
            <line x1={m.l} x2={w - m.r} y1={Y(t)} y2={Y(t)} stroke={C.grid} strokeWidth={1.5} />
            <text x={m.l - 10} y={Y(t) + 8} textAnchor="end" fill={C.muted} fontSize={20}>{fmt(t, tr.decimals ?? 0)}</text>
          </g>
        ))}
        <path d={xs.slice(0, n).map((x, i) => `${i ? 'L' : 'M'}${X(x)},${Y(ys[i])}`).join(' ')} fill="none" stroke={C.ink} strokeWidth={4} strokeLinejoin="round" />
        {xs.slice(0, n).map((x, i) => <circle key={i} cx={X(x)} cy={Y(ys[i])} r={5} fill={C.ink} />)}
        {xs.map((x, i) => (i % Math.ceil(xs.length / 6) === 0 || i === xs.length - 1) && (
          <text key={i} x={X(x)} y={m.t + ph + 30} textAnchor="middle" fill={C.muted} fontSize={20}>{x}</text>
        ))}
        {tr.xTitle && <text x={m.l + pw / 2} y={m.t + ph + 56} textAnchor="middle" fill={C.sub} fontSize={20}>{tr.xTitle}</text>}
      </svg>
    </div>
  );
};

export const Paper = ({d, f, w, h, fm}) => {
  const M = d.model, v = fm === 'v';
    const trendH = M.trend ? (v ? 200 : 150) : 0;
  return (
    <div style={{position: 'relative', width: w, height: h, fontFamily: FONT}}>
      {M.flow && <Flow d={d} f={f} w={w} flow={M.flow} v={v} />}
      <div style={{marginTop: M.flow ? (v ? 44 : 16) : 0}}><Compare d={d} f={f} w={w} cmp={M.compare} v={v} /></div>
      {M.trend && <div style={{position: 'absolute', left: 0, bottom: 0, width: w, height: trendH}}><Trend d={d} f={f} w={w} h={trendH} tr={M.trend} /></div>}
    </div>
  );
};
