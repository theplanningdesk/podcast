import React, {useEffect, useRef, useState} from 'react';
import {AbsoluteFill, continueRender, delayRender} from 'remotion';
import {C, FONT, HEAD} from './theme.js';
import {Mark} from './components/Chrome.jsx';

// Still cover for a Reel (render-cover.mjs), handed to Instagram as cover_url so the profile
// grid shows the headline instead of the video's empty first frame.
// The frame is 1080x1920, but the grid crops it from the centre: to 3:4 (y 240 to 1680) on
// current profiles and to a square (y 420 to 1500) in older views. Everything that has to be
// read sits inside the square; the rest is background only.
const SAFE = {top: 420, h: 1080, pad: 76};
const BARS_H = 210;   // bottom of the square, kept for the planning-bars texture
const HEAD_MAX = 190, HEAD_MIN = 64;

const VARIANTS = {
  daily: {bg: C.paper, head: C.ink, kicker: C.orange, topic: C.sub, mark: C.orange, word: C.ink, rule: C.orange, ghost: C.band},
  book: {bg: C.ink, head: C.paper, kicker: C.sand, topic: C.sage, mark: C.orange, word: C.paper, rule: C.orange, ghost: '#245A64'},
  research: {bg: C.orange, head: '#FFF7F2', kicker: C.ink, topic: C.ink, mark: C.ink, word: C.ink, rule: C.ink, ghost: '#F07A52'},
};

export const Cover = ({variant = 'daily', kicker = '', topic = '', title = '', show = 'The Planning Desk'}) => {
  const v = VARIANTS[variant] || VARIANTS.daily;
  const box = useRef(null), head = useRef(null);
  const [handle] = useState(() => delayRender('cover fonts and fit'));
  // Once the fonts are in, set the headline as large as its box allows: a grid tile is about
  // a third of a phone's width, so every pixel of type counts.
  useEffect(() => {
    const fit = () => {
      const b = box.current, h = head.current;
      if (b && h) {
        let size = HEAD_MAX;
        const apply = () => { h.style.fontSize = `${size}px`; h.style.letterSpacing = `${-size * 0.018}px`; };
        apply();
        while (size > HEAD_MIN && (b.scrollHeight > b.clientHeight || h.scrollWidth > h.clientWidth)) { size -= 2; apply(); }
      }
      continueRender(handle);
    };
    Promise.all([...[400, 700].map((w) => `${w} 40px Arimo`), ...[400, 700, 900].map((w) => `${w} 40px Lato`)].map((f) => document.fonts.load(f))).then(fit, fit);
  }, [handle, title, topic, kicker]);

  const bx = SAFE.top + SAFE.h - BARS_H;
  return (
    <AbsoluteFill style={{backgroundColor: v.bg, fontFamily: FONT}}>
      {/* Oversized planning bars, bleeding off the right edge, as a quiet texture. */}
      <svg width={1080} height={1920} style={{position: 'absolute', left: 0, top: 0}}>
        <rect x={SAFE.pad} y={bx + 20} width={520} height={42} rx={6} fill={v.ghost} />
        <rect x={SAFE.pad + 190} y={bx + 78} width={700} height={42} rx={6} fill={v.ghost} />
        <rect x={SAFE.pad + 90} y={bx + 136} width={380} height={42} rx={6} fill={v.ghost} />
      </svg>
      <div style={{position: 'absolute', top: SAFE.top, left: SAFE.pad, right: SAFE.pad, height: SAFE.h - BARS_H, display: 'flex', flexDirection: 'column'}}>
        <div style={{display: 'flex', alignItems: 'center', gap: 20, marginTop: 30, flex: 'none'}}>
          <Mark size={64} color={v.mark} />
          <div style={{fontFamily: HEAD, fontWeight: 700, fontSize: 42, color: v.word, letterSpacing: 0.2}}>{show}</div>
        </div>
        <div ref={box} style={{flex: 1, minHeight: 0, marginTop: 44, display: 'flex', flexDirection: 'column', justifyContent: 'center', overflow: 'hidden'}}>
          <div style={{color: v.kicker, fontSize: 36, fontWeight: 900, letterSpacing: 4, textTransform: 'uppercase', flex: 'none'}}>{kicker}</div>
          <div style={{height: 10, width: 150, background: v.rule, borderRadius: 5, marginTop: 24, flex: 'none'}} />
          {topic && <div style={{fontFamily: HEAD, color: v.topic, fontSize: 54, fontWeight: 700, lineHeight: 1.1, marginTop: 30, flex: 'none'}}>{topic}</div>}
          <div ref={head} style={{fontFamily: HEAD, color: v.head, fontSize: HEAD_MAX, fontWeight: 700, lineHeight: 1.03, marginTop: topic ? 12 : 30, paddingBottom: 12, textWrap: 'balance', flex: 'none'}}>{title}</div>
        </div>
      </div>
    </AbsoluteFill>
  );
};
