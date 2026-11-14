import React from 'react';
import {Img, staticFile} from 'remotion';
import * as Ph from '@phosphor-icons/react';
import {
  W, H, Pal, Rect, Skin, ease, T, txt, RED, rgba, ui, abs, POP, Caret, arrivals, slotY, countAt, fmtNum, ReplyText, UserBubble,
} from './appCore';

/**
 * UI kit faza 2 (14. nov 2026): još alata o kojima klijenti pričaju.
 *   gemini, perplexity  — AI chat (Perplexity: izvori stižu kao kartice pa odgovor)
 *   midjourney          — prompt → 4 slike se "razvijaju" (šum → oštro), izabrana se uveća
 *   slack               — kanal, poruke stižu dole hronološki, reakcije, kucanje + slanje
 *   calendar            — Google Calendar nedelja, pozivi se zakazuju na reč (popunjava se)
 *   stripe, shopify     — dashboard: prihod broji, grafik se crta, uplate/porudžbine stižu
 *   google              — pretraga: upit se kuca, AI Overview, rezultati (istaknut "tvoj" rezultat)
 */

// kadar pre i posle slanja: kamera klizi zajedno sa porukom (sendP 0→1), nikad skok
const mix = (a: {x: number; y: number; s: number}, b: {x: number; y: number; s: number}, k: number) =>
  ({x: a.x + (b.x - a.x) * k, y: a.y + (b.y - a.y) * k, s: a.s + (b.s - a.s) * k});
const file = (x: any): string | null => (x && typeof x === 'object' && x.src ? x.src : null);
const light = (bg: string, ink = '#1F1F1F', mut = '#6B6B6B', line = '#E3E3E3', bubble = '#F0F0F0'): Pal =>
  ({bg, rail: bg, card: '#FFFFFF', line, ink, mut, bubble, menu: '#FFFFFF'});

// ------------------------------------------------------------------ Gemini
const GemMark: React.FC<{size: number}> = ({size}) => (
  <svg width={size} height={size} viewBox="0 0 100 100">
    <defs><linearGradient id="gem" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stopColor="#4285F4" /><stop offset="0.55" stopColor="#9B72CB" /><stop offset="1" stopColor="#D96570" /></linearGradient></defs>
    <path d="M50 0 C53 28 72 47 100 50 C72 53 53 72 50 100 C47 72 28 53 0 50 C28 47 47 28 50 0 Z" fill="url(#gem)" />
  </svg>
);
const gemini: Skin = {
  menuFrom: 'plus',
  pal: {light: light('#FFFFFF', '#1F1F1F', '#5F6368', '#E0E3E7', '#F0F4F9'), dark: light('#131314', '#E3E3E3', '#9AA0A6', '#3C4043', '#1E1F20')},
  base: (st) => mix({x: W / 2 + 10, y: 300, s: 1.3}, {x: 480, y: 200, s: 1.4}, st.sendP),
  anchors: (st) => {
    const dy = st.sendP * 160;
    return {
      window: {x: 0, y: 0, w: W, h: H}, rail: {x: 0, y: 44, w: 72, h: H - 44}, main: {x: 72, y: 44, w: W - 72, h: H - 44},
      greeting: {x: 130, y: 150, w: 700, h: 80}, input: {x: 124, y: 270 + dy, w: 676, h: 130}, plus: {x: 144, y: 344 + dy, w: 44, h: 44},
      mic: {x: 690, y: 344 + dy, w: 44, h: 44}, send: {x: 740, y: 342 + dy, w: 48, h: 48}, model: {x: 92, y: 54, w: 220, h: 40},
      chat: {x: 100, y: 70, w: 780, h: 300},
    };
  },
  Body: ({st, a}) => {
    const p = st.pal, d = st.d;
    const has = st.typed.length > 0;
    return (
      <>
        <div style={abs(a.rail, {background: p.bubble})}>
          {[Ph.List, Ph.NotePencil, Ph.Diamond, Ph.ClockCounterClockwise].map((I, i) => (
            <div key={i} style={{position: 'absolute', left: 21, top: 22 + i * 58}}><I size={30} color={p.mut} /></div>))}
        </div>
        <div style={{...abs(a.model), display: 'flex', alignItems: 'center', gap: 10}}>
          <span style={ui(500, 26, p.ink)}>Gemini</span>
          <span style={{padding: '4px 12px', borderRadius: 999, background: p.bubble, display: 'flex', alignItems: 'center', gap: 4, ...ui(600, 16, p.mut)}}>
            {txt(d.model) || '2.5 Pro'}<Ph.CaretDown size={13} weight="bold" /></span>
        </div>
        <div style={{...abs(a.greeting), display: 'grid', placeItems: 'center', opacity: 1 - st.sendP}}>
          <span style={{...ui(500, 54, '#4285F4', 1.1), background: 'linear-gradient(90deg,#4285F4 0%,#9B72CB 45%,#D96570 80%)', WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent', paddingBottom: 6}}>{txt(d.greeting) || `Hello, ${txt(d.user) || 'there'}`}</span>
        </div>
        <UserBubble st={st} right={860} top={80} maxW={560} />
        {st.sendP > 0 ? (
          <>
            <div style={{position: 'absolute', left: 104, top: 170, opacity: st.sendP, transform: `rotate(${st.t * 60}deg)`}}><GemMark size={34} /></div>
            <ReplyText st={st} x={154} y={168} w={680} T0={T(d.send, 0) + 0.45} />
          </>
        ) : null}
        <div style={abs(a.input, {background: p.card, border: `1.5px solid ${p.line}`, borderRadius: 32, boxShadow: '0 6px 24px rgba(0,0,0,0.06)'})}>
          <div style={{position: 'absolute', left: 30, top: 24, right: 30, ...ui(has ? 500 : 400, 27, has ? p.ink : p.mut, 1.3)}}>
            {has ? st.typed : txt(d.placeholder) || 'Ask Gemini'}<Caret st={st} size={27} color={p.ink} /></div>
        </div>
        <div style={{...abs(a.plus), display: 'grid', placeItems: 'center'}}><Ph.Plus size={28} color={p.ink} /></div>
        <div style={{position: 'absolute', left: 200, top: a.plus.y + 4, display: 'flex', gap: 10}}>
          {['Deep Research', 'Canvas'].map((s) => (
            <span key={s} style={{padding: '6px 14px', borderRadius: 999, border: `1.5px solid ${p.line}`, ...ui(500, 17, p.ink)}}>{s}</span>))}
        </div>
        <div style={{...abs(a.mic), display: 'grid', placeItems: 'center'}}><Ph.Microphone size={26} color={p.ink} /></div>
        <div style={abs(a.send, {borderRadius: 24, background: has ? '#0B57D0' : 'transparent', display: 'grid', placeItems: 'center'})}>
          {has ? <Ph.PaperPlaneRight size={22} weight="fill" color="#fff" /> : null}
        </div>
      </>
    );
  },
};

// ------------------------------------------------------------------ Perplexity
const PPX = '#20808D';
const PpxMark: React.FC<{size: number; color?: string}> = ({size, color = PPX}) => (
  <svg width={size} height={size} viewBox="0 0 100 100" fill="none" stroke={color} strokeWidth={7} strokeLinejoin="round">
    <path d="M50 6 V94 M20 22 L50 46 L80 22 V60 L50 46 L20 60 Z M20 60 V86 L50 64 L80 86 V60" />
  </svg>
);
const perplexity: Skin = {
  menuFrom: 'input',
  pal: {light: light('#FCFCF9', '#13343B', '#64645F', '#E5E3D8', '#F3F3EE'), dark: light('#191A1A', '#E8E8E6', '#9A9A96', '#2F3031', '#202222')},
  base: (st) => mix({x: W / 2 + 10, y: 290, s: 1.3}, {x: 440, y: 232, s: 1.55}, st.sendP),
  anchors: (st) => {
    const srcs: any[] = st.d.sources ?? [];
    const a: Record<string, Rect> = {
      window: {x: 0, y: 0, w: W, h: H}, rail: {x: 0, y: 44, w: 72, h: H - 44}, logo: {x: 200, y: 150, w: 500, h: 70},
      input: st.sendP > 0 ? {x: 150, y: 506, w: 640, h: 70} : {x: 150, y: 250, w: 640, h: 130},
      send: st.sendP > 0 ? {x: 732, y: 518, w: 46, h: 46} : {x: 728, y: 324, w: 46, h: 46},
      question: {x: 110, y: 64, w: 720, h: 50}, sources: {x: 110, y: 128, w: 720, h: 86}, answer: {x: 110, y: 236, w: 720, h: 250},
    };
    srcs.slice(0, 4).forEach((_, i) => { a[`src${i}`] = {x: 110 + i * 182, y: 140, w: 172, h: 70}; });
    return a;
  },
  Body: ({st, a}) => {
    const p = st.pal, d = st.d, t = st.t;
    const has = st.typed.length > 0;
    const sent = st.sendP > 0;
    const srcs: any[] = (d.sources ?? []).slice(0, 4);
    const sT = T(d.send, 0);
    return (
      <>
        <div style={abs(a.rail, {background: p.bubble, borderRight: `1px solid ${p.line}`})}>
          <div style={{position: 'absolute', left: 18, top: 16}}><PpxMark size={36} color={p.ink} /></div>
          {[Ph.Plus, Ph.House, Ph.Compass, Ph.Books].map((I, i) => <div key={i} style={{position: 'absolute', left: 21, top: 80 + i * 56}}><I size={28} color={p.mut} /></div>)}
        </div>
        {!sent || st.sendP < 1 ? (
          <div style={{...abs(a.logo), display: 'grid', placeItems: 'center', opacity: 1 - st.sendP}}>
            <span style={{fontFamily: 'Georgia, serif', fontSize: 54, color: p.ink, letterSpacing: '-0.02em'}}>perplexity</span></div>
        ) : null}
        {sent ? (
          <div style={{opacity: st.sendP}}>
            <div style={{...abs(a.question), ...ui(600, 32, p.ink), whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'}}>{st.sent}</div>
            <div style={{position: 'absolute', left: 110, top: 118, display: 'flex', alignItems: 'center', gap: 8, ...ui(600, 17, p.ink)}}>
              <Ph.ListBullets size={20} />Sources</div>
            {srcs.map((s0, i) => {
              const r = a[`src${i}`];
              const k = ease(t, T(s0, sT + 0.5 + i * 0.25), 0.4, POP);
              return (
                <div key={i} style={{...abs(r), borderRadius: 12, background: p.bubble, padding: '9px 12px', opacity: Math.min(1, k * 1.3), transform: `translateY(${(1 - k) * 12}px)`}}>
                  <div style={{...ui(600, 16, p.ink, 1.2), display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden'}}>{txt(s0?.title) || txt(s0)}</div>
                  <div style={{display: 'flex', alignItems: 'center', gap: 6, marginTop: 3, ...ui(500, 13, p.mut)}}>
                    <div style={{width: 12, height: 12, borderRadius: 6, background: ['#E8710A', '#1A73E8', '#188038', '#A142F4'][i % 4]}} />
                    {txt(s0?.name) || txt(s0?.url)} · {i + 1}</div>
                </div>
              );
            })}
            <div style={{position: 'absolute', left: 110, top: 230, display: 'flex', alignItems: 'center', gap: 8, ...ui(600, 17, p.ink)}}>
              <PpxMark size={20} color={PPX} />Answer</div>
            <ReplyText st={st} x={110} y={262} w={720} T0={sT + 0.6 + srcs.length * 0.25} />
          </div>
        ) : null}
        <div style={abs(a.input, {background: p.card, border: `1.5px solid ${p.line}`, borderRadius: 18, boxShadow: '0 4px 18px rgba(0,0,0,0.05)'})}>
          <div style={{position: 'absolute', left: 24, top: sent ? 20 : 22, right: 90, ...ui(has ? 500 : 400, sent ? 22 : 26, has ? p.ink : p.mut, 1.3)}}>
            {has ? st.typed : sent ? 'Ask a follow-up' : txt(d.placeholder) || 'Ask anything…'}<Caret st={st} size={26} color={p.ink} /></div>
          {!sent ? <div style={{position: 'absolute', left: 18, bottom: 14, display: 'flex', gap: 8}}>
            {['Search', 'Research'].map((s, i) => <span key={s} style={{padding: '5px 12px', borderRadius: 10, background: i === 0 ? rgba(PPX, 0.14) : 'transparent',
              border: `1.5px solid ${i === 0 ? rgba(PPX, 0.5) : p.line}`, ...ui(600, 15, i === 0 ? PPX : p.mut)}}>{s}</span>)}</div> : null}
        </div>
        <div style={abs(a.send, {borderRadius: 23, background: has ? PPX : p.bubble, display: 'grid', placeItems: 'center'})}>
          <Ph.ArrowUp size={24} weight="bold" color={has ? '#fff' : p.mut} /></div>
      </>
    );
  },
};

// ------------------------------------------------------------------ Midjourney
const ART = ['radial-gradient(circle at 30% 30%, #FFB347 0%, #FF5E62 40%, #2B1055 100%)', 'radial-gradient(circle at 70% 40%, #7BF1A8 0%, #1E8C93 45%, #0B1D3A 100%)',
  'radial-gradient(circle at 40% 70%, #F9D423 0%, #E65C00 50%, #3A0F1F 100%)', 'radial-gradient(circle at 60% 30%, #A1C4FD 0%, #6A5AE0 45%, #1A1033 100%)'];
const MJ_GRID: Rect = {x: 150, y: 132, w: 640, h: 440};
const mjTile = (i: number): Rect => ({x: MJ_GRID.x + (i % 2) * 324, y: MJ_GRID.y + Math.floor(i / 2) * 224, w: 316, h: 216});
const midjourney: Skin = {
  menuFrom: 'input',
  pal: {light: light('#0E0E0F', '#F2F2F2', '#9A9A9A', '#262628', '#1C1C1E'), dark: light('#0E0E0F', '#F2F2F2', '#9A9A9A', '#262628', '#1C1C1E')},
  base: () => ({x: W / 2 + 20, y: 330, s: 1.2}),
  anchors: (st) => {
    const a: Record<string, Rect> = {window: {x: 0, y: 0, w: W, h: H}, input: {x: 130, y: 60, w: 680, h: 54}, send: {x: 762, y: 66, w: 42, h: 42}, grid: MJ_GRID};
    for (let i = 0; i < 4; i++) a[`tile${i}`] = mjTile(i);
    return a;
  },
  Body: ({st, a}) => {
    const p = st.pal, d = st.d, t = st.t;
    const has = st.typed.length > 0;
    const genT = d.send ? T(d.send, 1e9) : d.generate ? T(d.generate, 1e9) : 1e9;
    const imgs: any[] = d.images ?? [];
    const pick = d.upscale ? (typeof d.upscale.index === 'number' ? d.upscale.index : 0) : -1;
    const upT = d.upscale ? T(d.upscale, 1e9) : 1e9;
    const uk = ease(t, upT, 0.6);
    return (
      <>
        <div style={{position: 'absolute', left: 0, top: 44, width: 96, height: H - 44, borderRight: `1px solid ${p.line}`}}>
          <div style={{position: 'absolute', left: 30, top: 16, ...ui(800, 26, p.ink)}}>⛵</div>
          {[Ph.Compass, Ph.PaintBrush, Ph.PencilSimple, Ph.Images].map((I, i) => <div key={i} style={{position: 'absolute', left: 33, top: 76 + i * 56}}><I size={30} color={i === 1 ? p.ink : p.mut} /></div>)}
        </div>
        <div style={abs(a.input, {borderRadius: 27, background: p.bubble, border: `1.5px solid ${p.line}`, display: 'flex', alignItems: 'center', paddingLeft: 24})}>
          <span style={{...ui(has ? 500 : 400, 22, has ? p.ink : p.mut), whiteSpace: 'nowrap', overflow: 'hidden', maxWidth: 600}}>
            {has ? st.typed : st.sendP > 0 ? st.sent : 'What will you imagine?'}<Caret st={st} size={22} color={p.ink} /></span>
        </div>
        <div style={abs(a.send, {borderRadius: 21, background: has ? '#F2F2F2' : 'transparent', display: 'grid', placeItems: 'center'})}>
          {has ? <Ph.ArrowUp size={22} weight="bold" color="#111" /> : <Ph.Sliders size={24} color={p.mut} />}</div>
        {[0, 1, 2, 3].map((i) => {
          const r = a[`tile${i}`];
          const g = Math.min(1, Math.max(0, (t - genT - i * 0.12) / 2.4));  // razvijanje slike: šum → oštro
          if (t < genT) return null;
          const src = file(imgs[i]);
          const isPick = i === pick;
          const big = isPick ? uk : 0;
          const rr = isPick && big > 0 ? {x: r.x + (MJ_GRID.x - r.x) * big, y: r.y + (MJ_GRID.y - r.y) * big, w: r.w + (MJ_GRID.w - r.w) * big, h: r.h + (MJ_GRID.h - r.h) * big} : r;
          const fade = pick >= 0 && !isPick ? 1 - 0.85 * uk : 1;
          return (
            <div key={i} style={{...abs(rr), borderRadius: 14, overflow: 'hidden', background: '#1A1A1A', opacity: fade, zIndex: isPick ? 5 : 1,
              boxShadow: isPick && big > 0 ? `0 0 0 4px ${st.acc}` : undefined}}>
              {src ? <Img src={staticFile(src)} style={{width: '100%', height: '100%', objectFit: 'cover', filter: `blur(${(1 - g) * 22}px) saturate(${0.4 + 0.6 * g})`}} />
                : <div style={{width: '100%', height: '100%', background: ART[i], filter: `blur(${(1 - g) * 22}px)`, transform: `scale(${1.15 - 0.15 * g})`}} />}
              {g < 1 ? (
                <>
                  <div style={{position: 'absolute', inset: 0, opacity: 0.55 * (1 - g), backgroundImage: 'repeating-radial-gradient(circle at 17% 32%, rgba(255,255,255,0.18) 0 1px, transparent 1px 3px)'}} />
                  <span style={{position: 'absolute', left: 14, bottom: 10, ...ui(700, 18, '#fff')}}>{Math.round(g * 100)}%</span>
                </>
              ) : null}
            </div>
          );
        })}
      </>
    );
  },
};

// ------------------------------------------------------------------ Slack
const SL_SIDE = '#3F0E40';
const SL_TOP = 112, SL_BOTTOM = 506;
const slack: Skin = {
  menuFrom: 'input',
  pal: {light: light('#FFFFFF', '#1D1C1D', '#616061', '#DDDDDD', '#F8F8F8'), dark: light('#1A1D21', '#D1D2D3', '#ABABAD', '#35373B', '#222529')},
  base: () => ({x: 560, y: 330, s: 1.45}),
  anchors: (st) => {
    const a: Record<string, Rect> = {window: {x: 0, y: 0, w: W, h: H}, sidebar: {x: 0, y: 44, w: 240, h: H - 44}, channel: {x: 240, y: 44, w: W - 240, h: 56},
      list: {x: 240, y: SL_TOP, w: W - 240, h: SL_BOTTOM - SL_TOP}, input: {x: 258, y: 520, w: 624, h: 62}, send: {x: 836, y: 532, w: 38, h: 38}};
    const msgs: any[] = st.d.messages ?? [];
    msgs.forEach((_, i) => { a[`msg${i}`] = {x: 240, y: SL_TOP + i * 80, w: W - 240, h: 80}; });
    return a;
  },
  Body: ({st, a}) => {
    const p = st.pal, d = st.d, t = st.t;
    const chans: string[] = (d.channels ?? ['general', txt(d.channel) || 'sales', 'leads', 'wins']).map(txt);
    const ch = txt(d.channel) || chans[1] || 'general';
    const all: any[] = [...(d.messages ?? [])];
    if (d.send && st.sendP > 0) all.push({name: txt(d.user) || 'You', text: st.sent, atT: T(d.send, 0), me: true});
    const vis = all.filter((m) => typeof m?.atT !== 'number' || t >= m.atT - 0.05);
    const msgH = (m: any) => (m?.reactions?.length ? 104 : 80);
    const total = vis.reduce((s0, m) => s0 + msgH(m), 0);
    const over = Math.max(0, total - (SL_BOTTOM - SL_TOP));
    let y = SL_TOP - over;
    const has = st.typed.length > 0;
    return (
      <>
        <div style={abs(a.sidebar, {background: st.dark ? '#19171D' : SL_SIDE})}>
          <div style={{position: 'absolute', left: 18, top: 14, display: 'flex', alignItems: 'center', gap: 8, ...ui(800, 21, '#fff')}}>{txt(d.workspace) || 'Acme Inc'}<Ph.CaretDown size={15} weight="bold" /></div>
          {[[Ph.ChatsCircle, 'Threads'], [Ph.Bell, 'Activity']].map(([I, s]: any, i) => (
            <div key={s} style={{position: 'absolute', left: 18, top: 60 + i * 36, display: 'flex', alignItems: 'center', gap: 10, ...ui(500, 18, 'rgba(255,255,255,0.75)')}}><I size={20} />{s}</div>))}
          <div style={{position: 'absolute', left: 18, top: 150, ...ui(600, 16, 'rgba(255,255,255,0.65)')}}>Channels</div>
          {chans.slice(0, 6).map((c, i) => {
            const on = c === ch;
            return <div key={c} style={{position: 'absolute', left: 8, right: 8, top: 178 + i * 36, height: 32, borderRadius: 6, background: on ? '#1164A3' : undefined,
              display: 'flex', alignItems: 'center', gap: 8, paddingLeft: 12, ...ui(on ? 700 : 500, 18, on ? '#fff' : 'rgba(255,255,255,0.75)')}}># {c}</div>;
          })}
        </div>
        <div style={{...abs(a.channel), borderBottom: `1px solid ${p.line}`, display: 'flex', alignItems: 'center', paddingLeft: 20, gap: 8, ...ui(800, 22, p.ink)}}>
          # {ch}<Ph.CaretDown size={15} weight="bold" color={p.mut} /></div>
        <div style={{position: 'absolute', left: 240, top: SL_TOP, width: W - 240, height: SL_BOTTOM - SL_TOP, overflow: 'hidden'}}>
          {vis.map((m, i) => {
            const top = y - SL_TOP;
            y += msgH(m);
            const k = typeof m?.atT === 'number' ? ease(t, m.atT - 0.05, 0.4) : 1;
            const reacts: any[] = m?.reactions ?? [];
            return (
              <div key={i} style={{position: 'absolute', left: 0, top, width: W - 240, height: msgH(m), display: 'flex', gap: 14, padding: '10px 20px', boxSizing: 'border-box',
                opacity: k, transform: `translateY(${(1 - k) * 18}px)`, background: k < 1 || (typeof m?.atT === 'number' && t < m.atT + 1.2) ? rgba(st.acc, 0.07) : undefined}}>
                <div style={{width: 44, height: 44, borderRadius: 9, overflow: 'hidden', flex: 'none', background: ['#E8912D', '#2BAC76', '#36C5F0', '#E01E5A', '#4A154B'][i % 5],
                  display: 'grid', placeItems: 'center', ...ui(700, 20, '#fff')}}>
                  {file(m?.avatar) ? <Img src={staticFile(file(m.avatar)!)} style={{width: '100%', height: '100%', objectFit: 'cover'}} /> : txt(m?.name).slice(0, 1).toUpperCase()}
                </div>
                <div style={{flex: 1, minWidth: 0}}>
                  <div style={{display: 'flex', alignItems: 'baseline', gap: 8}}>
                    <span style={ui(800, 19, p.ink)}>{txt(m?.name)}</span>
                    {m?.app ? <span style={{padding: '1px 5px', borderRadius: 4, background: p.bubble, ...ui(700, 12, p.mut)}}>APP</span> : null}
                    <span style={ui(400, 14, p.mut)}>{txt(m?.time) || (typeof m?.atT === 'number' ? 'now' : '9:41 AM')}</span>
                  </div>
                  <div style={{...ui(400, 19, p.ink, 1.35), whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'}}>{txt(m?.text)}</div>
                  {reacts.length ? <div style={{display: 'flex', gap: 6, marginTop: 6}}>
                    {reacts.map((r0, j) => {
                      const rk = ease(t, T(r0, -1), 0.35, POP);
                      return <span key={j} style={{padding: '2px 10px', borderRadius: 12, background: rgba('#1264A3', 0.1), border: '1.5px solid rgba(18,100,163,0.45)',
                        transform: `scale(${rk})`, display: 'inline-flex', gap: 6, alignItems: 'center', ...ui(600, 15, '#1264A3')}}>
                        <span>{txt(r0?.emoji) || '🎉'}</span>{txt(r0?.count) || '1'}</span>;
                    })}
                  </div> : null}
                </div>
              </div>
            );
          })}
        </div>
        <div style={abs(a.input, {borderRadius: 10, border: `1.5px solid ${has ? p.mut : p.line}`, background: p.card})}>
          <div style={{position: 'absolute', left: 16, top: 17, right: 60, ...ui(has ? 500 : 400, 19, has ? p.ink : p.mut), whiteSpace: 'nowrap', overflow: 'hidden'}}>
            {has ? st.typed : `Message #${ch}`}<Caret st={st} size={19} color={p.ink} /></div>
        </div>
        <div style={abs(a.send, {borderRadius: 6, background: has ? '#007A5A' : 'transparent', display: 'grid', placeItems: 'center'})}>
          <Ph.PaperPlaneRight size={20} weight="fill" color={has ? '#fff' : p.mut} /></div>
      </>
    );
  },
};

// ------------------------------------------------------------------ Google Calendar (nedelja)
const CAL_X = 110, CAL_Y = 158, DAY_W = 156, HOUR_H = 50, H0 = 9, H1 = 17;
const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri'];
const hourOf = (v: any): number => {
  if (typeof v === 'number') return v;
  const m = /^(\d{1,2})(?::(\d{2}))?\s*(am|pm)?$/i.exec(String(v ?? '').trim());
  if (!m) return 10;
  let h = parseInt(m[1], 10) + (m[2] ? parseInt(m[2], 10) / 60 : 0);
  if (m[3]?.toLowerCase() === 'pm' && h < 12) h += 12;
  return h;
};
const dayOf = (v: any): number => (typeof v === 'number' ? v : Math.max(0, DAYS.findIndex((x) => String(v ?? '').toLowerCase().startsWith(x.toLowerCase()))));
const evRect = (e: any): Rect => {
  const d = Math.min(4, dayOf(e?.day));
  const s = hourOf(e?.start), en = e?.end != null ? hourOf(e.end) : s + 0.5;
  return {x: CAL_X + d * DAY_W + 4, y: CAL_Y + (s - H0) * HOUR_H + 1, w: DAY_W - 10, h: Math.max(26, (en - s) * HOUR_H - 3)};
};
const calendar: Skin = {
  menuFrom: 'header',
  pal: {light: light('#FFFFFF', '#1F1F1F', '#70757A', '#E3E3E3', '#F1F3F4'), dark: light('#1F1F1F', '#E3E3E3', '#9AA0A6', '#3C4043', '#2D2E30')},
  base: () => ({x: 500, y: 330, s: 1.32}),
  anchors: (st) => {
    const a: Record<string, Rect> = {window: {x: 0, y: 0, w: W, h: H}, header: {x: 0, y: 44, w: W, h: 60},
      week: {x: CAL_X, y: CAL_Y - 50, w: 5 * DAY_W, h: (H1 - H0) * HOUR_H + 50}};
    DAYS.forEach((_, i) => { a[`day${i}`] = {x: CAL_X + i * DAY_W, y: CAL_Y - 50, w: DAY_W, h: (H1 - H0) * HOUR_H + 50}; });
    (st.d.events ?? []).forEach((e: any, i: number) => { a[`ev${i}`] = evRect(e); });
    return a;
  },
  Body: ({st}) => {
    const p = st.pal, d = st.d, t = st.t;
    const evs: any[] = d.events ?? [];
    const booked = evs.filter((e) => typeof e?.atT === 'number' && t >= e.atT).length;
    const dates: string[] = (d.dates ?? ['17', '18', '19', '20', '21']).map(txt);
    return (
      <>
        <div style={{position: 'absolute', left: 0, top: 44, width: W, height: 60, display: 'flex', alignItems: 'center', gap: 16, paddingLeft: 22, borderBottom: `1px solid ${p.line}`}}>
          <div style={{width: 34, height: 34, borderRadius: 6, background: '#fff', border: '2px solid #4285F4', display: 'grid', placeItems: 'center', ...ui(700, 15, '#4285F4')}}>31</div>
          <span style={ui(400, 24, p.ink)}>Calendar</span>
          <span style={{marginLeft: 20, padding: '6px 16px', borderRadius: 18, border: `1.5px solid ${p.line}`, ...ui(500, 17, p.ink)}}>Today</span>
          <Ph.CaretLeft size={20} color={p.mut} /><Ph.CaretRight size={20} color={p.mut} />
          <span style={ui(400, 24, p.ink)}>{txt(d.month) || 'November 2026'}</span>
          {d.counter !== false && evs.some((e) => typeof e?.atT === 'number') ? (
            <span style={{marginLeft: 'auto', marginRight: 20, padding: '6px 14px', borderRadius: 18, background: rgba(st.acc, 0.18), ...ui(700, 17, p.ink)}}>
              {booked} {txt(d.label) || (booked === 1 ? 'call booked' : 'calls booked')}</span>
          ) : null}
        </div>
        {DAYS.map((s, i) => (
          <div key={s} style={{position: 'absolute', left: CAL_X + i * DAY_W, top: 108, width: DAY_W, textAlign: 'center'}}>
            <div style={ui(600, 14, p.mut)}>{s.toUpperCase()}</div>
            <div style={ui(400, 24, p.ink, 1.2)}>{dates[i]}</div>
          </div>
        ))}
        {Array.from({length: H1 - H0 + 1}).map((_, i) => (
          <React.Fragment key={i}>
            <div style={{position: 'absolute', left: 30, top: CAL_Y + i * HOUR_H - 9, width: 70, textAlign: 'right', ...ui(400, 13, p.mut)}}>
              {((H0 + i - 1) % 12) + 1} {H0 + i < 12 ? 'AM' : 'PM'}</div>
            <div style={{position: 'absolute', left: CAL_X, top: CAL_Y + i * HOUR_H, width: 5 * DAY_W, borderTop: `1px solid ${p.line}`}} />
          </React.Fragment>
        ))}
        {DAYS.map((_, i) => <div key={i} style={{position: 'absolute', left: CAL_X + i * DAY_W, top: CAL_Y, height: (H1 - H0) * HOUR_H, borderLeft: `1px solid ${p.line}`}} />)}
        {evs.map((e, i) => {
          const r = evRect(e);
          const k = typeof e?.atT === 'number' ? ease(t, e.atT, 0.45, POP) : 1;
          const bad = e?.tone === 'bad';
          const col = bad ? RED : txt(e?.color) || (typeof e?.atT === 'number' ? st.acc : '#039BE5');
          return (
            <div key={i} style={{...abs(r), borderRadius: 7, background: bad ? rgba(RED, 0.16) : col, padding: '4px 8px', overflow: 'hidden',
              opacity: Math.min(1, k * 1.3), transform: `scale(${0.7 + 0.3 * k})`, transformOrigin: '50% 0%',
              textDecoration: bad ? 'line-through' : undefined, boxShadow: '0 2px 6px rgba(0,0,0,0.15)'}}>
              <div style={{...ui(700, 17, bad ? RED : '#111', 1.15), whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'}}>{txt(e?.title)}</div>
              {r.h > 40 ? <div style={ui(500, 13, bad ? RED : 'rgba(0,0,0,0.7)')}>{txt(e?.start)}{e?.end ? ` – ${txt(e.end)}` : ''}</div> : null}
            </div>
          );
        })}
      </>
    );
  },
};

// ------------------------------------------------------------------ dashboard (Stripe / Shopify)
type Dash = 'stripe' | 'shopify';
const DASH = {
  stripe: {acc: '#635BFF', bg: '#FFFFFF', side: '#F6F8FA', nav: ['Home', 'Balances', 'Transactions', 'Customers', 'Products'], metric: 'Gross volume',
    list: 'Recent payments', chip: 'Succeeded', chipBg: '#D7F7C2', chipInk: '#05690D'},
  shopify: {acc: '#008060', bg: '#F1F1F1', side: '#EBEBEB', nav: ['Home', 'Orders', 'Products', 'Customers', 'Analytics'], metric: 'Total sales',
    list: 'Orders', chip: 'Paid', chipBg: '#E3E3E3', chipInk: '#303030'},
};
const D_LIST = 352, D_ROW = 46;
const dashSkin = (kind: Dash): Skin => ({
  menuFrom: 'metric',
  pal: {light: light(DASH[kind].bg, '#1A1F36', '#697386', '#E3E8EE', DASH[kind].side), dark: light(DASH[kind].bg, '#1A1F36', '#697386', '#E3E8EE', DASH[kind].side)},
  base: () => ({x: 540, y: 300, s: 1.32}),
  anchors: (st) => {
    const a: Record<string, Rect> = {window: {x: 0, y: 0, w: W, h: H}, sidebar: {x: 0, y: 44, w: 190, h: H - 44},
      metric: {x: 214, y: 84, w: 400, h: 100}, value: {x: 214, y: 112, w: 360, h: 64}, chart: {x: 214, y: 186, w: 660, h: 140},
      list: {x: 214, y: D_LIST - 34, w: 660, h: 34 + 5 * D_ROW}};
    for (let i = 0; i < 5; i++) a[`row${i}`] = {x: 214, y: D_LIST + i * D_ROW, w: 660, h: D_ROW};
    return a;
  },
  Body: ({st, a}) => {
    const p = st.pal, d = st.d, t = st.t;
    const B = DASH[kind];
    const m = d.metric ?? {label: B.metric, value: '$0'};
    const mT = T(m, 0.2);
    const val = countAt(m.start != null ? m : {start: 0, to: m.value ?? m.to, atT: mT}, t, mT);
    const delta = m.delta ? (typeof m.delta === 'object' ? m.delta : {text: m.delta}) : null;
    const dk = delta ? ease(t, T(delta, mT + 1.1), 0.4, POP) : 0;
    const bad = delta?.tone === 'bad' || /^-/.test(txt(delta));
    const vals: number[] = (d.chart?.values ?? [2, 2.4, 2.2, 3, 3.6, 3.3, 4.4, 5.2, 6.8, 8]).map(Number);
    const ck = ease(t, T(d.chart, mT), 1.6);
    const r = a.chart;
    const mx = Math.max(...vals);
    const pts = vals.map((v, i) => ({x: 10 + (i / (vals.length - 1)) * (r.w - 20), y: r.h - 14 - (v / (mx || 1)) * (r.h - 30)}));
    const n = Math.max(1, ck * (pts.length - 1));
    const cut = pts.slice(0, Math.floor(n) + 1);
    if (Math.floor(n) < pts.length - 1) {
      const p0 = pts[Math.floor(n)], p1 = pts[Math.floor(n) + 1], f = n - Math.floor(n);
      cut.push({x: p0.x + (p1.x - p0.x) * f, y: p0.y + (p1.y - p0.y) * f});
    }
    const line = cut.map((q, i) => `${i ? 'L' : 'M'}${q.x},${q.y}`).join(' ');
    const rows = arrivals(d.payments ?? [], t).slice(0, 5);
    const newOrders = (d.payments ?? []).filter((x: any) => typeof x?.atT === 'number' && t >= x.atT).length;
    return (
      <>
        <div style={abs(a.sidebar, {background: B.side, borderRight: `1px solid ${p.line}`})}>
          <div style={{position: 'absolute', left: 20, top: 16, display: 'flex', alignItems: 'center', gap: 8}}>
            {kind === 'stripe' ? <span style={{...ui(800, 26, B.acc), letterSpacing: '-0.04em'}}>stripe</span>
              : <><Ph.ShoppingBag size={26} weight="fill" color="#5E8E3E" /><span style={ui(800, 22, '#303030')}>shopify</span></>}
          </div>
          {B.nav.map((s, i) => (
            <div key={s} style={{position: 'absolute', left: 10, right: 10, top: 66 + i * 40, height: 36, borderRadius: 8, background: i === (kind === 'shopify' ? 1 : 0) ? '#FFFFFF' : undefined,
              display: 'flex', alignItems: 'center', gap: 10, paddingLeft: 12, ...ui(i === 0 ? 700 : 500, 17, p.ink)}}>
              {s}
              {kind === 'shopify' && s === 'Orders' && newOrders > 0 ? <span style={{marginLeft: 'auto', marginRight: 10, padding: '1px 8px', borderRadius: 10, background: '#303030', ...ui(700, 13, '#fff')}}>{newOrders}</span> : null}
            </div>
          ))}
        </div>
        <div style={{position: 'absolute', left: 200, top: 52, right: 12, bottom: 12, borderRadius: 14, background: kind === 'shopify' ? '#FFFFFF' : 'transparent'}} />
        <div style={abs(a.metric)}>
          <div style={ui(500, 18, p.mut)}>{txt(m.label) || B.metric}</div>
          <div style={{display: 'flex', alignItems: 'center', gap: 12, marginTop: 2}}>
            <span style={ui(700, 46, p.ink, 1.15)}>{isFinite(val) ? fmtNum(val, m.value ?? m.to) : txt(m.value)}</span>
            {delta && dk > 0 ? <span style={{padding: '4px 10px', borderRadius: 8, background: bad ? rgba(RED, 0.14) : 'rgba(0,168,107,0.14)', transform: `scale(${dk})`,
              ...ui(700, 16, bad ? RED : '#00A86B')}}>{txt(delta)}</span> : null}
          </div>
        </div>
        <div style={abs(r)}>
          <svg width={r.w} height={r.h} style={{overflow: 'visible'}}>
            <path d={`${line} L${cut[cut.length - 1].x},${r.h - 14} L${cut[0].x},${r.h - 14} Z`} fill={rgba(B.acc, 0.12)} />
            <path d={line} fill="none" stroke={B.acc} strokeWidth={4} strokeLinecap="round" strokeLinejoin="round" />
            <line x1={0} y1={r.h - 14} x2={r.w} y2={r.h - 14} stroke={p.line} strokeWidth={1.5} />
          </svg>
        </div>
        <div style={{position: 'absolute', left: 214, top: D_LIST - 34, ...ui(700, 19, p.ink)}}>{txt(d.title) || B.list}</div>
        {rows.map((x, idx) => {
          const e = x.r ?? {};
          const y = D_LIST + slotY(rows, idx, D_ROW);
          const fresh = x.T >= 0 ? ease(t, x.T, 0.25) * (1 - ease(t, x.T + 1.3, 0.8)) : 0;
          const ebad = e.tone === 'bad';
          return (
            <div key={x.i} style={{position: 'absolute', left: 214, top: y, width: 660, height: D_ROW, display: 'flex', alignItems: 'center', gap: 18, paddingLeft: 10,
              boxSizing: 'border-box', borderBottom: `1px solid ${p.line}`, opacity: x.k, transform: `translateY(${(1 - x.k) * -14}px)`, background: fresh > 0 ? rgba(B.acc, 0.1 * fresh) : undefined}}>
              <span style={{...ui(700, 19, p.ink), width: 110}}>{txt(e.amount)}</span>
              {kind === 'shopify' && txt(e.order) ? <span style={{...ui(600, 17, p.ink), width: 70}}>{txt(e.order)}</span> : null}
              <span style={{padding: '2px 10px', borderRadius: 6, background: ebad ? rgba(RED, 0.14) : B.chipBg, ...ui(700, 14, ebad ? RED : B.chipInk)}}>{txt(e.status) || B.chip}</span>
              <span style={{...ui(500, 17, p.mut), flex: 1, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'}}>{txt(e.customer)}</span>
              <span style={{...ui(500, 15, p.mut), marginRight: 14}}>{txt(e.time) || (x.T >= 0 ? 'Just now' : 'Today')}</span>
            </div>
          );
        })}
      </>
    );
  },
});

// ------------------------------------------------------------------ Google pretraga
const G_TOP = 168;
const GLogo: React.FC<{size: number}> = ({size}) => (
  <span style={{...ui(600, size, '#4285F4', 1), letterSpacing: '-0.03em', fontFamily: '"Product Sans", "CCC UI", sans-serif'}}>
    {[['G', '#4285F4'], ['o', '#EA4335'], ['o', '#FBBC05'], ['g', '#4285F4'], ['l', '#34A853'], ['e', '#EA4335']].map(([c, col], i) => <span key={i} style={{color: col}}>{c}</span>)}
  </span>
);
const google: Skin = {
  menuFrom: 'search',
  pal: {light: light('#FFFFFF', '#202124', '#4D5156', '#DADCE0', '#F1F3F4'), dark: light('#202124', '#E8EAED', '#BDC1C6', '#3C4043', '#303134')},
  base: () => ({x: 430, y: 300, s: 1.35}),
  anchors: (st) => {
    const ov = st.d.overview ? 1 : 0;
    const a: Record<string, Rect> = {window: {x: 0, y: 0, w: W, h: H}, search: {x: 150, y: 54, w: 600, h: 50}, input: {x: 150, y: 54, w: 600, h: 50},
      overview: {x: 150, y: G_TOP - 18, w: 660, h: 150}, results: {x: 150, y: G_TOP + ov * 160, w: 660, h: 300}};
    (st.d.results ?? []).forEach((_: any, i: number) => { a[`res${i}`] = {x: 140, y: G_TOP + ov * 160 + i * 112, w: 680, h: 104}; });
    return a;
  },
  Body: ({st, a}) => {
    const p = st.pal, d = st.d, t = st.t;
    const q = st.typed || (st.typing ? '' : txt(d.input) || txt(d.query));
    const res: any[] = d.results ?? [];
    const ov = d.overview;
    const ovT = ov ? T(ov, 0.6) : 1e9;
    const ovTxt = ov ? txt(ov) : '';
    const ovK = ov ? Math.min(1, Math.max(0, (t - ovT) / Math.min(2.2, ovTxt.length * 0.025))) : 0;
    return (
      <>
        <div style={{position: 'absolute', left: 26, top: 60}}><GLogo size={38} /></div>
        <div style={abs(a.search, {borderRadius: 25, background: p.card, boxShadow: '0 1px 6px rgba(32,33,36,0.28)', display: 'flex', alignItems: 'center', paddingLeft: 22, gap: 12})}>
          <span style={{...ui(400, 20, p.ink), flex: 1, whiteSpace: 'nowrap', overflow: 'hidden'}}>{q}<Caret st={st} size={20} color={p.ink} /></span>
          <Ph.X size={20} color={p.mut} /><Ph.Microphone size={22} color="#4285F4" /><Ph.MagnifyingGlass size={22} color="#4285F4" style={{marginRight: 18}} />
        </div>
        <div style={{position: 'absolute', left: 160, top: 116, display: 'flex', gap: 26, ...ui(500, 16, p.mut)}}>
          {['AI Mode', 'All', 'Images', 'News', 'Videos'].map((s, i) => <span key={s} style={{color: i === 1 ? '#1A73E8' : p.mut, borderBottom: i === 1 ? '3px solid #1A73E8' : undefined, paddingBottom: 8}}>{s}</span>)}
        </div>
        <div style={{position: 'absolute', left: 0, top: 148, width: W, borderTop: `1px solid ${p.line}`}} />
        {ov && t >= ovT - 0.1 ? (
          <div style={abs(a.overview, {borderRadius: 16, background: st.dark ? '#1E2A3A' : '#F0F4F9', padding: '14px 18px', opacity: ease(t, ovT - 0.1, 0.35)})}>
            <div style={{display: 'flex', alignItems: 'center', gap: 8, ...ui(600, 17, p.ink)}}><Ph.Sparkle size={20} weight="fill" color="#4285F4" />AI Overview</div>
            <div style={{marginTop: 8, ...ui(400, 18, p.ink, 1.45)}}>{ovTxt.slice(0, Math.round(ovK * ovTxt.length))}</div>
          </div>
        ) : null}
        {res.map((r0, i) => {
          const r = a[`res${i}`];
          const k = typeof r0?.atT === 'number' ? ease(t, r0.atT, 0.4) : ease(t, (ov ? ovT + 0.8 : 0.3) + i * 0.15, 0.4);
          const hi = r0?.tone === 'good' || r0?.highlight;
          const hk = hi ? ease(t, T(r0, 0.5) + 0.3, 0.4) : 0;
          const host = String(r0?.url || '').replace(/^https?:\/\//, '').replace(/^www\./, '').split('/')[0];
          return (
            <div key={i} style={{...abs(r), borderRadius: 14, padding: '8px 12px', opacity: k, transform: `translateY(${(1 - k) * 12}px)`,
              boxShadow: hk > 0 ? `inset 0 0 0 ${3 * hk}px ${st.acc}` : undefined, background: hk > 0 ? rgba(st.acc, 0.08 * hk) : undefined}}>
              <div style={{display: 'flex', alignItems: 'center', gap: 10}}>
                <div style={{width: 28, height: 28, borderRadius: 14, background: p.bubble, display: 'grid', placeItems: 'center', ...ui(700, 14, p.mut)}}>{(host || '?').slice(0, 1).toUpperCase()}</div>
                <div style={{lineHeight: 1.1}}>
                  <div style={ui(500, 15, p.ink)}>{txt(r0?.site) || host}</div>
                  <div style={ui(400, 13, p.mut)}>{r0?.label ? <b style={{color: p.ink}}>{txt(r0.label)} · </b> : null}{txt(r0?.url)}</div>
                </div>
              </div>
              <div style={{marginTop: 6, ...ui(400, 22, st.dark ? '#8AB4F8' : '#1A0DAB'), whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'}}>{txt(r0?.title)}</div>
              <div style={{...ui(400, 15, p.mut, 1.35), whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'}}>{txt(r0?.snippet)}</div>
            </div>
          );
        })}
      </>
    );
  },
};

export const DESK2_SKINS: Record<string, Skin> = {gemini, perplexity, midjourney, slack, calendar, stripe: dashSkin('stripe'), shopify: dashSkin('shopify'), google};
