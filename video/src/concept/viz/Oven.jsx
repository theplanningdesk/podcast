import React from 'react';
import {interpolate} from 'remotion';
import {C, FONT, HEAD} from '../../theme.js';
import {clamp, fmt, ramp} from '../kit.js';

// Research clip: energy-aware scheduling of a paint oven (Khayyati et al. 2026).
// Top: cars moving up the line to the oven, with the visibility window. Middle: the oven's mode over an
// illustrative shift under each policy. Bottom: the paper's Table 2 (energy per car, waiting per car).
const MODE = {on: C.orange, warm: C.sand, standby: '#F3B79A', off: C.paper2};
const SHIFT = 480;

// Illustrative arrival clusters at the oven over one shift (minutes); not data from the paper.
const CLUSTERS = [[0, 50], [95, 150], [172, 196], [262, 330], [392, 428], [452, 480]];

const policy = (name) => {
  const seg = [];
  if (name === 'always') return [[0, SHIFT, 'on']];
  if (name === 'threshold') {
    // Reacts to the queue: stays hot for a while after the last car, warms up only once cars are waiting.
    let t = 0;
    CLUSTERS.forEach(([a, b], i) => {
      const next = CLUSTERS[i + 1];
      if (a > t) { seg.push([t, a, 'off']); seg.push([a, a + 14, 'warm']); seg.push([a + 14, b, 'on']); }
      else seg.push([t, b, 'on']);
      const hold = Math.min(b + 35, next ? next[0] : SHIFT);
      seg.push([b, hold, 'on']);
      t = hold;
    });
    if (t < SHIFT) seg.push([t, SHIFT, 'off']);
    return seg;
  }
  // Scheduled on predicted arrivals: standby in short gaps, off in long ones, warm-up timed to finish as cars arrive.
  let t = 0;
  CLUSTERS.forEach(([a, b], i) => {
    if (a > t) {
      const gap = a - t;
      if (gap > 50) { seg.push([t, a - 14, 'off']); seg.push([a - 14, a, 'warm']); }
      else { seg.push([t, a - 5, 'standby']); seg.push([a - 5, a, 'warm']); }
    }
    seg.push([a, b, 'on']);
    t = b;
  });
  return seg;
};
const POL = {always: policy('always'), threshold: policy('threshold'), scheduled: policy('scheduled')};

const Strip = ({segs, X, y, h, o}) => (
  <g opacity={o}>
    {segs.map(([a, b, m], i) => <rect key={i} x={X(a)} y={y} width={Math.max(0, X(b) - X(a))} height={h} fill={MODE[m]} />)}
  </g>
);

const Line = ({f, w, A, win}) => {
  // Cars move right towards the oven at a steady pace; spacing has gaps like the clusters.
  const ovenX = w - 130, startX = 10;
  const slots = Array.from({length: 26}, (_, i) => i);
  const gapAt = new Set([5, 6, 7, 12, 13, 18, 19, 20]);
  const shift = (f * 1.6) % 34;
  return (
    <svg width={w} height={150} style={{overflow: 'visible'}}>
      <line x1={startX} x2={ovenX} y1={92} y2={92} stroke={C.grid} strokeWidth={6} strokeLinecap="round" />
      {slots.map((i) => {
        if (gapAt.has(i)) return null;
        const x = ovenX - 30 - i * 34 + shift;
        if (x < startX || x > ovenX - 26) return null;
        const inWin = win > 0 && x > ovenX - 26 - win;
        return <rect key={i} x={x - 13} y={78} width={26} height={16} rx={5} fill={inWin ? C.ink : C.muted} opacity={inWin ? 1 : 0.65} />;
      })}
      <g transform={`translate(${ovenX}, 42)`}>
        <rect width={120} height={80} rx={10} fill={C.ink} />
        <text x={60} y={50} textAnchor="middle" fill={C.paper} fontSize={28} fontWeight={700} fontFamily={HEAD}>Oven</text>
      </g>
      {win > 0 && (
        <g>
          <path d={`M${ovenX - 26 - win},62 L${ovenX - 26 - win},50 L${ovenX - 10},50 L${ovenX - 10},62`} fill="none" stroke={C.ink} strokeWidth={3} />
          <text x={ovenX - 18 - win / 2} y={36} textAnchor="middle" fill={C.ink} fontSize={22} fontWeight={700} fontFamily={FONT}>Arrival times known</text>
        </g>
      )}
      <text x={startX} y={132} fill={C.muted} fontSize={21} fontFamily={FONT}>Upstream stations</text>
    </svg>
  );
};

export const Oven = ({d, f, w, h, fm}) => {
  const A = d.acts.map((a) => a.start), T = d.model.table;
  const pThr = ramp(f, A[1] + 10, 30), pSch = ramp(f, A[2] + 14, 34);
  const winIn = ramp(f, A[2] + 4, 24);
  // Act 4: the window grows from about 40 to 70 cars ahead and beyond (scaled on screen).
  const win = winIn * interpolate(f, [A[3], A[3] + 40, A[3] + 90, A[3] + 150], [190, 190, 360, 480], clamp);
  const band4 = ramp(f, A[3] + 20, 20);
  const stripIn = ramp(f, 10, 40);
  const X = (m) => (m / SHIFT) * w;
  const v = fm === 'v';
  const top = 34, stripY = v ? 214 : 226, stripH = v ? 56 : 46, barsY = v ? 344 : 338;
  const rows = [
    {k: 'always', label: 'Always on', at: 30},
    {k: 'threshold', label: 'Threshold rule', at: A[1] + 10},
    {k: 'scheduled', label: 'Scheduled on predicted arrivals', at: A[2] + 14},
  ];
  const maxE = 10.08;
  return (
    <div style={{position: 'relative', width: w, height: h, fontFamily: FONT}}>
      <div style={{color: C.sub, fontSize: 24}}>Special-colour paint oven, about 100 cars a day</div>
      <div style={{position: 'absolute', top}}><Line f={f} w={w} A={A} win={win} /></div>
      {band4 > 0 && (
        <div style={{position: 'absolute', top: top + 114, left: 210, color: C.orange, fontSize: 22, fontWeight: 700, opacity: band4}}>
          Biggest gain: from 40 to 70 cars ahead
        </div>
      )}
      <div style={{position: 'absolute', top: stripY - 34, left: 0, right: 0, display: 'flex', justifyContent: 'space-between', fontSize: 21, color: C.sub}}>
        <span>Oven mode over one shift (illustrative)</span>
        <span style={{display: 'flex', gap: 12}}>
          {[['on', 'On'], ['warm', 'Warm-up'], ['standby', 'Standby'], ['off', 'Off']].map(([m, t]) => (
            <span key={m} style={{display: 'flex', alignItems: 'center', gap: 5}}>
              <span style={{width: 16, height: 16, borderRadius: 3, background: MODE[m], border: m === 'off' ? `1px solid ${C.grid}` : 'none'}} />{t}
            </span>
          ))}
        </span>
      </div>
      <svg width={w} height={stripH + 26} style={{position: 'absolute', top: stripY, left: 0, overflow: 'visible'}}>
        <defs><clipPath id="ovenin"><rect x={0} y={-10} width={w * stripIn} height={stripH + 40} /></clipPath></defs>
        <g clipPath="url(#ovenin)">
          <Strip segs={POL.always} X={X} y={0} h={stripH} o={1} />
          <Strip segs={POL.threshold} X={X} y={0} h={stripH} o={pThr} />
          <Strip segs={POL.scheduled} X={X} y={0} h={stripH} o={pSch} />
          {CLUSTERS.map(([a, b], i) => (
            <rect key={i} x={X(a)} y={stripH + 8} width={X(b) - X(a)} height={8} rx={4} fill={C.ink} />
          ))}
        </g>
        <text x={w} y={stripH + 42} textAnchor="end" fill={C.muted} fontSize={20} fontFamily={FONT}>cars reach the oven ▬</text>
      </svg>
      <div style={{position: 'absolute', top: barsY, left: 0, width: w}}>
        <div style={{display: 'flex', justifyContent: 'space-between', color: C.sub, fontSize: 22, marginBottom: 6}}>
          <span>Energy per car, minutes of full heat</span><span>Wait per car</span>
        </div>
        {rows.map((r, i) => {
          const o = ramp(f, r.at, 22), row = T[r.k];
          const best = r.k === 'scheduled';
          return (
            <div key={r.k} style={{opacity: o, marginTop: v ? 12 : 8}}>
              <div style={{color: C.text, fontSize: 23, fontWeight: best ? 700 : 400}}>{r.label}</div>
              <div style={{display: 'flex', alignItems: 'center', marginTop: 4}}>
                <div style={{width: (w - 240) * (row.energy / maxE) * o, height: v ? 26 : 22, background: best ? C.ink : C.sage, borderRadius: 3}} />
                <div style={{marginLeft: 12, fontFamily: HEAD, fontWeight: 700, fontSize: 28, color: best ? C.ink : C.sub}}>{fmt(row.energy, 2)}</div>
                <div style={{marginLeft: 'auto', fontFamily: HEAD, fontWeight: 700, fontSize: 28, color: best ? C.orange : C.sub}}>{fmt(row.wait, 0)} s</div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
