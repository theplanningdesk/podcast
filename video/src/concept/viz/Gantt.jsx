import React from 'react';
import {C, FONT, HEAD} from '../../theme.js';
import {fmt, mix, ramp} from '../kit.js';

// One filling line over a week. Orders are blocks coloured light -> dark; changeovers sit between them.
const FAM = {A: '#F1D9A0', B: '#E1A06B', C: '#B5573A', D: '#5A2E24'};
const FAM_TXT = {A: C.ink, B: C.ink, C: '#FFF4EC', D: '#FFF4EC'};
const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri'];

export const Gantt = ({d, f, w, h}) => {
  const M = d.model, A = d.acts.map((a) => a.start);
  const pOpt = ramp(f, A[2] + 16, 46), pRush = ramp(f, A[3] + 12, 36), drop = ramp(f, A[3] + 36, 22);
  const draw = ramp(f, 6, 70);
  const pulse = f >= A[1] && f < A[2] ? 0.5 + 0.5 * Math.sin((f - A[1]) / 5) : 0;
  const top = 74, rowH = Math.min(220, h - 380), X = (hr) => (hr / 120) * w;
  const jobs = (s) => Object.fromEntries(s.filter((x) => x.kind === 'job').map((x) => [x.id, x]));
  const jb = jobs(M.base), jo = jobs(M.opt), jr = jobs(M.rush);
  const cos = (s) => s.filter((x) => x.kind === 'co');
  // Changeovers crossfade between schedules.
  const coSets = [[cos(M.base), 1 - pOpt], [cos(M.opt), pOpt * (1 - pRush)], [cos(M.rush), pRush]];
  const lateO = 1 - pOpt;
  const hours = [
    {run: 86, co: 26.5, free: 7.5},
    {run: 86, co: 13, free: 21},
    {run: 92, co: 13, free: 15},
  ];
  const hv = ['run', 'co', 'free'].map((k) => mix(mix(hours[0][k], hours[1][k], pOpt), hours[2][k], pRush));

  return (
    <div style={{position: 'relative', width: w, height: h, fontFamily: FONT}}>
      <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'baseline'}}>
        <div style={{color: C.sub, fontSize: 26}}>Filling line, one week</div>
        <div style={{display: 'flex', gap: 14, alignItems: 'center', color: C.sub, fontSize: 22}}>
          {Object.keys(FAM).map((k) => (
            <div key={k} style={{display: 'flex', alignItems: 'center', gap: 6}}>
              <div style={{width: 22, height: 22, borderRadius: 4, background: FAM[k]}} />{k}
            </div>
          ))}
          <div style={{marginLeft: 4}}>light → dark</div>
        </div>
      </div>
      <svg width={w} height={rowH + 120} style={{position: 'absolute', top, left: 0, overflow: 'visible'}}>
        <defs>
          <pattern id="hatch" width={8} height={8} patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
            <rect width={8} height={8} fill={C.paper2} /><line x1={0} y1={0} x2={0} y2={8} stroke={C.muted} strokeWidth={3} />
          </pattern>
          <clipPath id="gdraw"><rect x={0} y={-80} width={w * draw} height={rowH + 220} /></clipPath>
        </defs>
        {DAYS.map((dname, i) => (
          <g key={dname}>
            <line x1={X(i * 24)} x2={X(i * 24)} y1={-6} y2={rowH + 10} stroke={C.grid} strokeWidth={2} />
            <text x={X(i * 24 + 12)} y={rowH + 40} textAnchor="middle" fill={C.muted} fontSize={24}>{dname}</text>
          </g>
        ))}
        <line x1={X(120)} x2={X(120)} y1={-6} y2={rowH + 10} stroke={C.grid} strokeWidth={2} />
        <g clipPath="url(#gdraw)">
          {coSets.map(([set, o], si) => o > 0.01 && set.map((c, i) => {
            const big = c.dur >= 4;
            return (
              <g key={`${si}-${i}`} opacity={o}>
                <rect x={X(c.start)} y={0} width={X(c.dur)} height={rowH} fill={big ? C.orange : 'url(#hatch)'}
                  opacity={big ? 0.55 + 0.45 * pulse : 1} />
              </g>
            );
          }))}
          {Object.keys(jb).map((id) => {
            const b = jb[id], o = jo[id], r = jr[id];
            const x = mix(mix(b.start, o.start, pOpt), r.start, pRush);
            const late = b.late && lateO > 0.02;
            return (
              <g key={id}>
                <rect x={X(x) + 1} y={0} width={X(b.dur) - 2} height={rowH} rx={4} fill={FAM[b.fam]} />
                <text x={X(x + b.dur / 2)} y={rowH / 2 + 9} textAnchor="middle" fill={FAM_TXT[b.fam]} fontSize={24} fontWeight={700} fontFamily={HEAD}>{b.fam}</text>
                {late && (
                  <g opacity={lateO}>
                    <rect x={X(x) + 1} y={0} width={X(b.dur) - 2} height={rowH} rx={4} fill="none" stroke={C.orange} strokeWidth={5} />
                    <text x={X(x + b.dur / 2)} y={-14} textAnchor="middle" fill={C.orange} fontSize={21} fontWeight={700}>late</text>
                  </g>
                )}
              </g>
            );
          })}
        </g>
        {drop > 0 && (() => {
          const r = jr[13];
          const y = (1 - drop) * -120;
          return (
            <g opacity={drop}>
              <rect x={X(r.start) + 1} y={y} width={X(r.dur) - 2} height={rowH} rx={4} fill={FAM[r.fam]} stroke={C.ink} strokeWidth={4} />
              <text x={X(r.start + r.dur / 2)} y={y + rowH / 2 + 9} textAnchor="middle" fill={FAM_TXT[r.fam]} fontSize={24} fontWeight={700} fontFamily={HEAD}>C</text>
              <text x={X(r.start + r.dur / 2)} y={y - 14} textAnchor="middle" fill={C.ink} fontSize={21} fontWeight={700}>rush</text>
            </g>
          );
        })()}
      </svg>
      <div style={{position: 'absolute', top: top + rowH + 74, left: 0, width: w}}>
        <div style={{display: 'flex', gap: 22, color: C.sub, fontSize: 22, alignItems: 'center'}}>
          <div style={{display: 'flex', alignItems: 'center', gap: 8}}><div style={{width: 22, height: 22, background: C.orange, opacity: 0.7}} />Dark → light clean, 4 h</div>
          <div style={{display: 'flex', alignItems: 'center', gap: 8}}>
            <svg width={22} height={22}><rect width={22} height={22} fill="url(#hatch)" /><rect width={22} height={22} fill="none" /></svg>
            Light → dark, 1.5 h
          </div>
        </div>
        <div style={{color: C.sub, fontSize: 24, marginTop: 30, marginBottom: 12}}>The week's 120 hours</div>
        <div style={{display: 'flex', height: 46, borderRadius: 6, overflow: 'hidden'}}>
          <div style={{width: X(hv[0]), background: C.ink}} />
          <div style={{width: X(hv[1]), background: C.orange}} />
          <div style={{width: X(hv[2]), background: C.sage}} />
        </div>
        <div style={{display: 'flex', gap: 26, marginTop: 10, fontSize: 23, color: C.text}}>
          <span><b style={{color: C.ink}}>{fmt(hv[0], 0)} h</b> running</span>
          <span><b style={{color: C.orange}}>{fmt(hv[1], 1)} h</b> changing over</span>
          <span><b style={{color: C.ink}}>{fmt(hv[2], 1)} h</b> free</span>
        </div>
      </div>
    </div>
  );
};
