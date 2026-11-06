import React, {useMemo} from 'react';
import {geoMercator, geoPath} from 'd3-geo';
import {feature} from 'topojson-client';
import world50 from 'world-atlas/countries-50m.json';
import {C, FONT, HEAD} from '../../theme.js';
import {fmt, mix, ramp} from '../kit.js';

const countries = feature(world50, world50.objects.countries);
const NORDIC = new Set(['752', '578', '246', '208']);
const BOX = {lon: [4.2, 31.8], lat: [54.4, 70.4]};
// Label placement per site: [dx, dy, anchor]
const LBL = {Helsinki: [0, -24, 'middle'], Stockholm: [0, 42, 'middle'], Oslo: [-22, 8, 'end'], Gothenburg: [22, 8, 'start'],
  'Malmö': [22, 8, 'start'], Copenhagen: [22, 8, 'start'], 'Jönköping': [22, 8, 'start'], 'Örebro': [22, 8, 'start']};

export const Network = ({d, f, w, h}) => {
  const M = d.model, A = d.acts.map((a) => a.start);
  const mapW = Math.round(w * 0.5), panelX = mapW + 34, panelW = w - panelX;
  const geo = useMemo(() => {
    const box = {type: 'Feature', geometry: {type: 'MultiPoint', coordinates: [[BOX.lon[0], BOX.lat[0]], [BOX.lon[1], BOX.lat[1]]]}};
    const proj = geoMercator().fitExtent([[0, 0], [mapW, h]], box);
    const path = geoPath(proj);
    return {
      land: countries.features.map((c) => ({nordic: NORDIC.has(String(c.id)), d: path(c)})).filter((c) => c.d),
      P: (name) => { const c = M.cities[name]; return proj([c[1], c[0]]); },
    };
  }, [mapW, h]);
  const pOpt = ramp(f, A[2] + 16, 44), pFuel = ramp(f, A[3] + 20, 40);
  const S = M.states;
  const inSet = (st, s) => (S[st].sites.includes(s) ? 1 : 0);
  const sites = [...new Set([...S.today.sites, ...S.opt.sites, ...S.fuel.sites])];
  const linesO = ramp(f, 24, 40), dcIn = ramp(f, 6, 22);

  // Cost curve
  const cw = panelW, ch = h - 210, cm = {l: 54, r: 14, t: 20, b: 46};
  const pw = cw - cm.l - cm.r, ph = ch - cm.t - cm.b;
  const YMIN = 20, YMAX = 34;
  const cx = (n) => cm.l + ((n - 1) / 5) * pw;
  const cy = (v) => cm.t + ph - ((Math.min(Math.max(v, YMIN), YMAX) - YMIN) / (YMAX - YMIN)) * ph;
  const curve = mix(M.curve, M.curveFuel, pFuel);
  const curveIn = ramp(f, A[1] + 14, 50);
  const bestN = pFuel > 0.5 ? 4 : 3;
  const bestO = ramp(f, A[2] + 10, 20);
  const today = mix(S.today.total, M.todayFuel, pFuel);
  const shown = curve.slice(0, Math.max(1, Math.ceil(6 * curveIn)));

  return (
    <div style={{position: 'relative', width: w, height: h, fontFamily: FONT}}>
      <svg width={mapW} height={h} style={{position: 'absolute', left: 0, top: 0}}>
        <defs><clipPath id="mapclip"><rect width={mapW} height={h} rx={10} /></clipPath></defs>
        <g clipPath="url(#mapclip)">
          <rect width={mapW} height={h} fill="#E9DDD7" />
          {geo.land.map((c, i) => <path key={i} d={c.d} fill={c.nordic ? '#F6EEE9' : '#E3D6CF'} stroke={C.grid} strokeWidth={1.2} />)}
          {Object.keys(M.cities).map((c) => {
            const pick = (st) => geo.P(S[st].assign[c]);
            const a = pick('today'), b = pick('opt'), e = pick('fuel');
            const s = [mix(mix(a[0], b[0], pOpt), e[0], pFuel), mix(mix(a[1], b[1], pOpt), e[1], pFuel)];
            const t = geo.P(c);
            return <line key={c} x1={s[0]} y1={s[1]} x2={s[0] + (t[0] - s[0]) * linesO} y2={s[1] + (t[1] - s[1]) * linesO} stroke={C.ink} strokeWidth={1.6} opacity={0.38} />;
          })}
          {Object.entries(M.cities).map(([c, v]) => {
            const [x, y] = geo.P(c);
            return <circle key={c} cx={x} cy={y} r={2.5 + Math.sqrt(v[2]) * 1.6} fill={C.sub} opacity={0.75} />;
          })}
          {sites.map((s) => {
            const m = mix(mix(inSet('today', s), inSet('opt', s), pOpt), inSet('fuel', s), pFuel) * dcIn;
            if (m < 0.02) return null;
            const [x, y] = geo.P(s);
            const isNew = (inSet('opt', s) && !inSet('today', s) && pOpt > 0 && pFuel < 1) || (inSet('fuel', s) && !inSet('opt', s) && pFuel > 0);
            const [lx, ly, la] = LBL[s] || [22, 8, 'start'];
            return (
              <g key={s} opacity={Math.min(1, m * 1.3)} transform={`translate(${x},${y}) scale(${0.4 + 0.6 * m})`}>
                <rect x={-13} y={-13} width={26} height={26} rx={4} fill={isNew ? C.orange : C.ink} stroke="#F6EEE9" strokeWidth={4} />
                <text x={lx} y={ly} textAnchor={la} fill={C.ink} fontSize={23} fontWeight={700} fontFamily={HEAD}
                  style={{paintOrder: 'stroke', stroke: '#F6EEE9', strokeWidth: 7, strokeLinejoin: 'round'}}>{s}</text>
              </g>
            );
          })}
        </g>
      </svg>
      <div style={{position: 'absolute', left: panelX, top: 0, width: panelW}}>
        <div style={{color: C.sub, fontSize: 25, lineHeight: 1.2}}>Network cost a year, €M,<br />by number of DCs</div>
        <svg width={cw} height={ch} style={{marginTop: 12, overflow: 'visible', opacity: ramp(f, A[1] + 6, 16)}}>
          {[20, 25, 30].map((v) => (
            <g key={v}>
              <line x1={cm.l} x2={cw - cm.r} y1={cy(v)} y2={cy(v)} stroke={C.grid} strokeWidth={1.5} />
              <text x={cm.l - 10} y={cy(v) + 8} textAnchor="end" fill={C.muted} fontSize={22}>{v}</text>
            </g>
          ))}
          {[1, 2, 3, 4, 5, 6].map((n) => <text key={n} x={cx(n)} y={ch - cm.b + 34} textAnchor="middle" fill={C.muted} fontSize={22}>{n}</text>)}
          <path d={shown.map((v, i) => `${i ? 'L' : 'M'}${cx(i + 1)},${cy(v)}`).join(' ')} fill="none" stroke={C.ink} strokeWidth={4} strokeLinejoin="round" />
          {shown.map((v, i) => <circle key={i} cx={cx(i + 1)} cy={cy(v)} r={7} fill={C.ink} />)}
          <g opacity={curveIn}>
            <circle cx={cx(5)} cy={cy(today)} r={11} fill="none" stroke={C.orange} strokeWidth={4} />
            <text x={cx(5)} y={cy(today) - 20} textAnchor="middle" fill={C.orange} fontSize={21} fontWeight={700}>today</text>
          </g>
          {bestO > 0 && (
            <g opacity={bestO}>
              <circle cx={cx(bestN)} cy={cy(curve[bestN - 1])} r={13} fill={C.ink} stroke={C.paper} strokeWidth={4} />
              <text x={cx(bestN)} y={cy(curve[bestN - 1]) + 40} textAnchor="middle" fill={C.ink} fontSize={21} fontWeight={700}>best</text>
            </g>
          )}
        </svg>
        <div style={{display: 'flex', flexDirection: 'column', gap: 10, marginTop: 18, fontSize: 21, color: C.sub}}>
          <div style={{display: 'flex', alignItems: 'center', gap: 10}}><div style={{width: 18, height: 18, borderRadius: 3, background: C.ink}} />Distribution centre</div>
          <div style={{display: 'flex', alignItems: 'center', gap: 10}}><div style={{width: 12, height: 12, borderRadius: 6, background: C.sub, marginLeft: 3}} />Customers, sized by demand</div>
          <div style={{color: C.text, fontSize: 22, fontWeight: 700, marginTop: 4}}>Today: €{fmt(today, 1)}M</div>
        </div>
      </div>
    </div>
  );
};
