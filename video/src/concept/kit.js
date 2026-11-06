import {interpolate} from 'remotion';
export const PAD = 80, CW = 920;
export const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'};
export const ease = (x) => (x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2);
export const ramp = (f, a, len = 30) => ease(interpolate(f, [a, a + len], [0, 1], clamp));
export const mix = (a, b, t) => (Array.isArray(a) ? a.map((v, i) => v + (b[i] - v) * t) : a + (b - a) * t);
export const fmt = (v, dec = 0) => Number(v).toLocaleString('en-US', {minimumFractionDigits: dec, maximumFractionDigits: dec});
// Value that steps through [[frame, value], ...]: counts up from 0 at the first step, then eases to each next value.
export const stepped = (f, steps, len = 36) => {
  let v = steps[0][1] * ramp(f, steps[0][0], 45);
  for (let i = 1; i < steps.length; i++) v += (steps[i][1] - steps[i - 1][1]) * ramp(f, steps[i][0], len);
  return v;
};
// Layout per format: v = 1080x1920 (clear of Shorts/Reels UI), p = 1080x1350 (LinkedIn 4:5).
export const LAYOUT = {
  v: {header: 150, text: 250, textH: 330, head: 64, sub: 34, viz: 610, vizH: 630, kpis: 1262, kpiSize: 96, footer: 1440},
  p: {header: 44, text: 116, textH: 260, head: 54, sub: 30, viz: 392, vizH: 572, kpis: 984, kpiSize: 86, footer: 1236},
};
