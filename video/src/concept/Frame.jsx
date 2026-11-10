import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import {C, FONT, HEAD} from '../theme.js';
import {Mark} from '../components/Chrome.jsx';
import {CW, LAYOUT, PAD, clamp, fmt, ramp, stepped} from './kit.js';
import {VIZ} from './viz/index.js';

const Act = ({a, end, f, l}) => {
  const o = Math.min(interpolate(f, [a.start, a.start + 10], [0, 1], clamp), interpolate(f, [end - 8, end], [1, 0], clamp));
  if (o <= 0) return null;
  const y = interpolate(f, [a.start, a.start + 14], [16, 0], clamp);
  const so = interpolate(f, [a.start + 12, a.start + 24], [0, 1], clamp);
  return (
    <div style={{position: 'absolute', left: 0, right: 0, top: 0, opacity: o, transform: `translateY(${y}px)`}}>
      <div style={{fontFamily: HEAD, color: C.ink, fontSize: l.head, fontWeight: 700, lineHeight: 1.1, letterSpacing: -0.6}}>{a.head}</div>
      <div style={{fontFamily: FONT, color: C.text, fontSize: l.sub, lineHeight: 1.3, marginTop: 20, opacity: so}}>{a.sub}</div>
    </div>
  );
};

const Kpis = ({d, f, l, dim}) => (
  <div style={{display: 'flex', gap: 70, opacity: dim * interpolate(f, [d.kpiIn ?? 30, (d.kpiIn ?? 30) + 12], [0, 1], clamp)}}>
    {d.kpis.map((k, i) => {
      const v = stepped(f, k.steps);
      const good = f >= (k.goodFrom ?? d.goodFrom ?? 1e9);
      return (
        <div key={i}>
          <div style={{fontFamily: HEAD, fontWeight: 700, fontSize: l.kpiSize, lineHeight: 1, letterSpacing: -2.5,
            color: good ? C.ink : C.orange, fontVariantNumeric: 'tabular-nums'}}>{k.prefix || ''}{fmt(v, k.decimals || 0)}{k.suffix || ''}</div>
          <div style={{fontFamily: FONT, color: C.text, fontSize: 26, marginTop: 10}}>{k.label}</div>
        </div>
      );
    })}
  </div>
);

const Header = ({l, d}) => (
  <div style={{position: 'absolute', top: l.header, left: PAD, right: PAD, display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontFamily: FONT}}>
    <div style={{display: 'flex', alignItems: 'center', gap: 16}}>
      <Mark size={42} />
      <div style={{fontFamily: HEAD, fontWeight: 700, fontSize: 28, color: C.ink}}>The Planning Desk</div>
      <div style={{color: C.muted, fontSize: 24}}>·&nbsp;&nbsp;{d.series || 'Planning concept'}</div>
    </div>
    <div style={{color: C.muted, border: `2px solid ${C.grid}`, fontSize: 20, fontWeight: 700, padding: '7px 15px', borderRadius: 999}}>AI-generated</div>
  </div>
);

export const Story = ({fmt: fm = 'v', d}) => {
  const f = useCurrentFrame();
  const l = LAYOUT[fm];
  const endP = ramp(f, d.endStart, 18);
  const dim = 1 - (d.source ? 0.97 : 0.55) * endP;
  const Viz = VIZ[d.viz];
  return (
    <AbsoluteFill style={{backgroundColor: C.paper}}>
      <Header l={l} d={d} />
      <div style={{position: 'absolute', top: l.text, left: PAD, width: CW, height: l.textH, opacity: 1 - endP}}>
        {d.acts.map((a, i) => <Act key={i} a={a} end={i < d.acts.length - 1 ? d.acts[i + 1].start : d.endStart} f={f} l={l} />)}
      </div>
      {endP > 0 && (
        <div style={{position: 'absolute', top: l.text, left: PAD, width: CW, opacity: endP, transform: `translateY(${(1 - endP) * 16}px)`}}>
          <div style={{fontFamily: FONT, color: C.orange, fontSize: 26, fontWeight: 900, letterSpacing: 2.6, textTransform: 'uppercase'}}>{d.kicker || 'Planning concept'}</div>
          <div style={{fontFamily: HEAD, color: C.ink, fontSize: l.head + 16, fontWeight: 700, lineHeight: 1.05, marginTop: 14, letterSpacing: -1}}>{d.endTitle}</div>
          <div style={{fontFamily: FONT, color: C.text, fontSize: l.sub, lineHeight: 1.3, marginTop: 18}}>{d.endTag}</div>
          {d.source && (
            <div style={{marginTop: 22, paddingLeft: 18, borderLeft: `5px solid ${C.orange}`, fontFamily: FONT, color: C.sub, fontSize: l.sub - 6, lineHeight: 1.3}}>
              <span style={{fontWeight: 900, color: C.ink}}>Paper</span>&nbsp;&nbsp;{d.source.card || d.source.cite}
            </div>
          )}
        </div>
      )}
      <div style={{position: 'absolute', top: l.viz, left: PAD, width: CW, height: l.vizH, opacity: dim}}>
        <Viz d={d} f={f} w={CW} h={l.vizH} fm={fm} />
      </div>
      <div style={{position: 'absolute', top: l.kpis, left: PAD, width: CW}}><Kpis d={d} f={f} l={l} dim={dim} /></div>
      <div style={{position: 'absolute', top: l.footer, left: PAD, width: fm === 'v' ? CW - 90 : CW, fontFamily: FONT}}>
        <div style={{color: C.muted, fontSize: 21, marginBottom: 12}}>{d.footnote}</div>
        <div style={{height: 6, background: C.paper2, borderRadius: 3}}>
          <div style={{height: 6, width: `${(f / (d.total - 1)) * 100}%`, background: C.orange, borderRadius: 3}} />
        </div>
        <div style={{color: C.sub, fontSize: 22, marginTop: 12}}>{d.cta}</div>
      </div>
    </AbsoluteFill>
  );
};
