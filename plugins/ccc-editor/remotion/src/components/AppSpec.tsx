import React from 'react';
import {Img, staticFile} from 'remotion';
import * as Ph from '@phosphor-icons/react';
import {
  W, H, Pal, Rect, St, Skin, ease, T, txt, RED, rgba, ui, abs, POP, Caret, arrivals, slotY, countAt, fmtNum, ReplyText, UserBubble,
} from './appCore';

/**
 * UI kit faza B (14. nov 2026): aplikacije kao PODACI. Tri univerzalna šablona — AI chat, lista (inbox / CRM / zadaci),
 * dashboard (prihod / pretplatnici) — i nova aplikacija istog tipa je samo opis od ~10 linija (ime, boje, logo, meni,
 * kolone). `app: "custom"` gradi isti šablon iz plana (`type` + `brand: {name, color, logo}`), pa se može pokazati
 * BILO KOJI alat koji klijent pomene, sa njegovim imenom, bojom i pravim logom (`ccc logo`).
 */

type Mark = (size: number) => React.ReactNode;
const file = (x: any): string | null => (x && typeof x === 'object' && x.src ? x.src : null);
const pal = (bg: string, ink: string, mut: string, line: string, bubble: string, card = '#FFFFFF'): Pal => ({bg, rail: bg, card, line, ink, mut, bubble, menu: card});
const LIGHT = pal('#FFFFFF', '#1F1F1F', '#6B6B6B', '#E5E5E5', '#F3F3F3');
const DARK = pal('#141414', '#ECECEC', '#9A9A9A', '#2E2E2E', '#232323', '#1E1E1E');
// svetla boja brenda (žuta, roze) → tamna slova na njoj, tamnija nijansa za tekst na beloj (čitljivost)
const lum = (hex: string) => { const n = parseInt(hex.slice(1), 16); return (0.2126 * ((n >> 16) & 255) + 0.7152 * ((n >> 8) & 255) + 0.0722 * (n & 255)) / 255; };
const onAcc = (hex: string) => (lum(hex) > 0.62 ? '#1A1A1A' : '#FFFFFF');
const inkOf = (hex: string) => { if (lum(hex) <= 0.55) return hex; const n = parseInt(hex.slice(1), 16); const f = 0.42;
  return `rgb(${Math.round(((n >> 16) & 255) * f)},${Math.round(((n >> 8) & 255) * f)},${Math.round((n & 255) * f)})`; };
const mix = (a: {x: number; y: number; s: number}, b: {x: number; y: number; s: number}, k: number) =>
  ({x: a.x + (b.x - a.x) * k, y: a.y + (b.y - a.y) * k, s: a.s + (b.s - a.s) * k});

/** Znak: pravi logo (fajl iz `ccc logo`) ili slovo u boji brenda — nikad izmišljen crtež tuđeg logoa. */
const letterMark = (name: string, color: string, round = false): Mark => (size) => (
  <div style={{width: size, height: size, borderRadius: round ? size / 2 : size * 0.26, background: color, display: 'grid', placeItems: 'center',
    ...ui(800, size * 0.5, '#fff', 1)}}>{name.slice(0, 1).toUpperCase()}</div>
);
const logoMark = (src: string): Mark => (size) => <Img src={staticFile(src)} style={{width: size, height: size, objectFit: 'contain'}} />;
const gradMark = (name: string, grad: string): Mark => (size) => (
  <div style={{width: size, height: size, borderRadius: size * 0.3, background: grad, display: 'grid', placeItems: 'center', ...ui(800, size * 0.48, '#fff', 1)}}>
    {name.slice(0, 1).toUpperCase()}</div>
);

// ================================================================== 1) AI chat
export type ChatSpec = {
  name: string; mark: Mark; accent: string; light?: Pal; dark?: Pal; greeting?: string; placeholder?: string; model?: string;
  chips?: string[]; gradientGreeting?: string; rail?: React.FC<any>[]; dark0?: boolean;
};
export const chatApp = (c: ChatSpec): Skin => ({
  menuFrom: 'plus',
  pal: {light: c.light ?? LIGHT, dark: c.dark ?? DARK},
  base: (st) => mix({x: W / 2 + 10, y: 296, s: 1.3}, {x: 468, y: 200, s: 1.38}, st.sendP),
  anchors: (st) => {
    const dy = st.sendP * 160;
    return {window: {x: 0, y: 0, w: W, h: H}, rail: {x: 0, y: 44, w: 72, h: H - 44}, main: {x: 72, y: 44, w: W - 72, h: H - 44},
      greeting: {x: 130, y: 150, w: 700, h: 80}, input: {x: 124, y: 270 + dy, w: 676, h: 130}, plus: {x: 144, y: 344 + dy, w: 44, h: 44},
      mic: {x: 690, y: 344 + dy, w: 44, h: 44}, send: {x: 740, y: 342 + dy, w: 48, h: 48}, model: {x: 92, y: 54, w: 260, h: 40}, chat: {x: 100, y: 70, w: 780, h: 300}};
  },
  Body: ({st, a}) => {
    const p = st.pal, d = st.d, t = st.t;
    const has = st.typed.length > 0;
    const Rail = c.rail ?? [Ph.List, Ph.NotePencil, Ph.MagnifyingGlass, Ph.ClockCounterClockwise];
    const g = txt(d.greeting) || c.greeting || `How can I help, ${txt(d.user) || 'today'}?`;
    return (
      <>
        <div style={abs(a.rail, {background: p.bubble})}>
          <div style={{position: 'absolute', left: 16, top: 14}}>{c.mark(40)}</div>
          {Rail.map((I, i) => <div key={i} style={{position: 'absolute', left: 21, top: 78 + i * 56}}><I size={28} color={p.mut} /></div>)}
        </div>
        <div style={{...abs(a.model), display: 'flex', alignItems: 'center', gap: 10}}>
          <span style={ui(600, 25, p.ink)}>{c.name}</span>
          {(txt(d.model) || c.model) ? <span style={{padding: '4px 12px', borderRadius: 999, background: p.bubble, display: 'flex', alignItems: 'center', gap: 4, ...ui(600, 16, p.mut)}}>
            {txt(d.model) || c.model}<Ph.CaretDown size={13} weight="bold" /></span> : null}
        </div>
        <div style={{...abs(a.greeting), display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 16, opacity: 1 - st.sendP}}>
          {c.mark(48)}
          <span style={{...ui(600, 44, p.ink, 1.15), ...(c.gradientGreeting ? {background: c.gradientGreeting, WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', paddingBottom: 4} : {})}}>{g}</span>
        </div>
        <UserBubble st={st} right={836} top={80} maxW={540} />
        {st.sendP > 0 ? (
          <>
            <div style={{position: 'absolute', left: 102, top: 166, opacity: st.sendP, transform: `scale(${0.9 + 0.1 * Math.sin(t * 6)})`}}>{c.mark(36)}</div>
            <ReplyText st={st} x={154} y={168} w={680} T0={T(d.send, 0) + 0.45} />
          </>
        ) : null}
        <div style={abs(a.input, {background: p.card, border: `1.5px solid ${p.line}`, borderRadius: 30, boxShadow: '0 6px 24px rgba(0,0,0,0.06)'})}>
          <div style={{position: 'absolute', left: 30, top: 24, right: 30, ...ui(has ? 500 : 400, 27, has ? p.ink : p.mut, 1.3)}}>
            {has ? st.typed : txt(d.placeholder) || c.placeholder || `Message ${c.name}`}<Caret st={st} size={27} color={p.ink} /></div>
        </div>
        <div style={{...abs(a.plus), display: 'grid', placeItems: 'center'}}><Ph.Plus size={28} color={p.ink} /></div>
        <div style={{position: 'absolute', left: 200, top: a.plus.y + 4, display: 'flex', gap: 10}}>
          {(c.chips ?? []).map((s) => <span key={s} style={{padding: '6px 14px', borderRadius: 999, border: `1.5px solid ${p.line}`, ...ui(500, 17, p.ink)}}>{s}</span>)}
        </div>
        <div style={{...abs(a.mic), display: 'grid', placeItems: 'center'}}><Ph.Microphone size={26} color={p.mut} /></div>
        <div style={abs(a.send, {borderRadius: 24, background: has || st.sendP > 0 ? c.accent : p.bubble, display: 'grid', placeItems: 'center'})}>
          <Ph.ArrowUp size={24} weight="bold" color={has || st.sendP > 0 ? onAcc(c.accent) : p.mut} /></div>
      </>
    );
  },
});

// ================================================================== 2) lista (inbox / CRM / zadaci)
export type Col = {key: string; label?: string; w: number; bold?: boolean; chip?: boolean; right?: boolean; muted?: boolean};
export type ListSpec = {
  name: string; mark: Mark; accent: string; side?: string; sideInk?: string; light?: Pal; nav: string[]; navIcons?: React.FC<any>[];
  title?: string; cols: Col[]; button?: string; chipColors?: Record<string, [string, string]>;
};
const L_TOP = 168, L_ROW = 52;
export const listApp = (c: ListSpec): Skin => ({
  menuFrom: 'button',
  pal: {light: c.light ?? pal('#F7F8FA', '#1F2328', '#656D76', '#E3E6EA', '#EEF1F4'), dark: c.light ?? pal('#F7F8FA', '#1F2328', '#656D76', '#E3E6EA', '#EEF1F4')},
  base: (st) => {
    const n = Math.max(3, Math.min(7, (st.d.rows ?? []).length));
    return {x: 548, y: Math.max(250, (60 + L_TOP + n * L_ROW) / 2 + 10), s: 1.36};
  },
  anchors: () => {
    const a: Record<string, Rect> = {window: {x: 0, y: 0, w: W, h: H}, sidebar: {x: 0, y: 44, w: 196, h: H - 44}, header: {x: 214, y: 56, w: 670, h: 56},
      button: {x: 750, y: 64, w: 130, h: 40}, list: {x: 214, y: L_TOP - 40, w: 670, h: 40 + 8 * L_ROW}};
    for (let i = 0; i < 8; i++) a[`row${i}`] = {x: 214, y: L_TOP + i * L_ROW, w: 670, h: L_ROW};
    return a;
  },
  Body: ({st, a}) => {
    const p = st.pal, d = st.d, t = st.t;
    const rows = arrivals(d.rows ?? [], t).slice(0, 7);
    const side = c.side ?? '#FFFFFF', sInk = c.sideInk ?? p.ink;
    const icons = c.navIcons ?? [Ph.Tray, Ph.Users, Ph.ChartBar, Ph.Gear, Ph.Folder];
    const newN = (d.rows ?? []).filter((r: any) => typeof r?.atT === 'number' && t >= r.atT).length;
    const chipC = (v: string): [string, string] => c.chipColors?.[v.toLowerCase()] ?? [rgba(c.accent, 0.18), inkOf(c.accent)];
    return (
      <>
        <div style={abs(a.sidebar, {background: side, borderRight: `1px solid ${p.line}`})}>
          <div style={{position: 'absolute', left: 16, top: 14, display: 'flex', alignItems: 'center', gap: 10}}>{c.mark(30)}<span style={ui(800, 20, sInk)}>{c.name}</span></div>
          {c.nav.slice(0, 6).map((s, i) => {
            const I = icons[i % icons.length];
            return <div key={s} style={{position: 'absolute', left: 8, right: 8, top: 64 + i * 42, height: 38, borderRadius: 8, background: i === 0 ? rgba(c.accent, side === '#FFFFFF' ? 0.12 : 0.3) : undefined,
              display: 'flex', alignItems: 'center', gap: 10, paddingLeft: 12, ...ui(i === 0 ? 700 : 500, 17, i === 0 && side === '#FFFFFF' ? c.accent : sInk)}}>
              <I size={19} />{s}
              {i === 0 && newN > 0 ? <span style={{marginLeft: 'auto', marginRight: 10, padding: '1px 8px', borderRadius: 10, background: c.accent, ...ui(700, 13, onAcc(c.accent))}}>{newN}</span> : null}
            </div>;
          })}
        </div>
        <div style={{...abs(a.header), display: 'flex', alignItems: 'center', gap: 12}}>
          {c.mark(40)}
          <div style={{display: 'flex', flexDirection: 'column'}}>
            <span style={ui(700, 15, inkOf(c.accent), 1.1)}>{c.name}</span>
            <span style={ui(800, 24, p.ink, 1.15)}>{txt(d.title) || c.title || c.nav[0]}</span>
          </div>
        </div>
        <div style={{...abs(a.button), borderRadius: 8, background: c.accent, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6, ...ui(700, 16, onAcc(c.accent))}}>
          <Ph.Plus size={16} weight="bold" />{txt(d.button) || c.button || 'New'}</div>
        <div style={{position: 'absolute', left: 214, top: L_TOP - 40, width: 670, height: 40, borderRadius: '10px 10px 0 0', background: p.card, borderBottom: `1px solid ${p.line}`,
          display: 'flex', alignItems: 'center', paddingLeft: 14, gap: 12, ...ui(700, 14, p.mut)}}>
          {c.cols.map((col) => <span key={col.key} style={{width: col.w, flex: col.w ? 'none' : 1, textAlign: col.right ? 'right' : 'left'}}>{col.label ?? col.key}</span>)}
        </div>
        <div style={{position: 'absolute', left: 214, top: L_TOP, width: 670, height: 7 * L_ROW, background: p.card}} />
        {rows.map((x, idx) => {
          const r = x.r ?? {};
          const y = L_TOP + slotY(rows, idx, L_ROW);
          const fresh = x.T >= 0 ? ease(t, x.T, 0.25) * (1 - ease(t, x.T + 1.3, 0.8)) : 0;
          const bad = r.tone === 'bad', good = r.tone === 'good';
          return (
            <div key={x.i} style={{position: 'absolute', left: 214, top: y, width: 670, height: L_ROW, display: 'flex', alignItems: 'center', gap: 12, paddingLeft: 14, boxSizing: 'border-box',
              borderBottom: `1px solid ${p.line}`, opacity: x.k, transform: `translateY(${(1 - x.k) * -14}px)`,
              background: fresh > 0 ? rgba(st.acc, 0.14 * fresh) : good ? rgba(st.acc, 0.1) : undefined, boxShadow: good ? `inset 4px 0 0 ${st.acc}` : bad ? `inset 4px 0 0 ${RED}` : undefined}}>
              {c.cols.map((col) => {
                const v = txt(r[col.key]);
                if (col.chip) {
                  const [bg, ink] = bad ? [rgba(RED, 0.14), RED] : chipC(v);
                  return <span key={col.key} style={{width: col.w, flex: 'none'}}><span style={{padding: '3px 10px', borderRadius: 6, background: bg, ...ui(700, 14, ink)}}>{v}</span></span>;
                }
                return <span key={col.key} style={{width: col.w, flex: col.w ? 'none' : 1, textAlign: col.right ? 'right' : 'left', whiteSpace: 'nowrap', overflow: 'hidden',
                  textOverflow: 'ellipsis', ...ui(col.bold ? 700 : 500, 17, bad && col.bold ? RED : col.muted ? p.mut : p.ink)}}>{v}</span>;
              })}
            </div>
          );
        })}
      </>
    );
  },
});

// ================================================================== 3) dashboard (prihod / pretplatnici / prodaja)
export type DashSpec = {name: string; mark: Mark; accent: string; side?: string; nav: string[]; metric: string; list: string; chip: string;
  cols?: {key: string; w: number; bold?: boolean}[]; light?: Pal};
const DL = 352, DR = 46;
export const dashApp = (c: DashSpec): Skin => ({
  menuFrom: 'metric',
  pal: {light: c.light ?? pal('#FFFFFF', '#1A1F36', '#697386', '#E3E8EE', c.side ?? '#F6F8FA'), dark: c.light ?? pal('#FFFFFF', '#1A1F36', '#697386', '#E3E8EE', c.side ?? '#F6F8FA')},
  base: () => ({x: 548, y: 296, s: 1.32}),
  anchors: () => {
    const a: Record<string, Rect> = {window: {x: 0, y: 0, w: W, h: H}, sidebar: {x: 0, y: 44, w: 190, h: H - 44}, metric: {x: 214, y: 84, w: 400, h: 100},
      value: {x: 214, y: 112, w: 360, h: 64}, chart: {x: 214, y: 186, w: 660, h: 140}, list: {x: 214, y: DL - 34, w: 660, h: 34 + 5 * DR}};
    for (let i = 0; i < 5; i++) a[`row${i}`] = {x: 214, y: DL + i * DR, w: 660, h: DR};
    return a;
  },
  Body: ({st, a}) => {
    const p = st.pal, d = st.d, t = st.t;
    const m = d.metric ?? {label: c.metric, value: '0'};
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
    if (Math.floor(n) < pts.length - 1) { const p0 = pts[Math.floor(n)], p1 = pts[Math.floor(n) + 1], f = n - Math.floor(n); cut.push({x: p0.x + (p1.x - p0.x) * f, y: p0.y + (p1.y - p0.y) * f}); }
    const line = cut.map((q, i) => `${i ? 'L' : 'M'}${q.x},${q.y}`).join(' ');
    const rows = arrivals(d.payments ?? d.rows ?? [], t).slice(0, 5);
    const cols = c.cols ?? [{key: 'amount', w: 120, bold: true}, {key: 'customer', w: 0}];
    return (
      <>
        <div style={abs(a.sidebar, {background: c.side ?? '#F6F8FA', borderRight: `1px solid ${p.line}`})}>
          <div style={{position: 'absolute', left: 18, top: 14, display: 'flex', alignItems: 'center', gap: 10}}>{c.mark(30)}<span style={ui(800, 20, p.ink)}>{c.name}</span></div>
          {c.nav.map((s, i) => <div key={s} style={{position: 'absolute', left: 10, right: 10, top: 64 + i * 40, height: 36, borderRadius: 8, background: i === 0 ? '#FFFFFF' : undefined,
            display: 'flex', alignItems: 'center', paddingLeft: 12, ...ui(i === 0 ? 700 : 500, 17, p.ink)}}>{s}</div>)}
        </div>
        <div style={{position: 'absolute', left: 214, top: 50, display: 'flex', alignItems: 'center', gap: 10}}>{c.mark(30)}<span style={ui(800, 20, inkOf(c.accent))}>{c.name}</span></div>
        <div style={abs(a.metric)}>
          <div style={ui(500, 18, p.mut)}>{txt(m.label) || c.metric}</div>
          <div style={{display: 'flex', alignItems: 'center', gap: 12, marginTop: 2}}>
            <span style={ui(700, 46, p.ink, 1.15)}>{isFinite(val) ? fmtNum(val, m.value ?? m.to) : txt(m.value)}</span>
            {delta && dk > 0 ? <span style={{padding: '4px 10px', borderRadius: 8, background: bad ? rgba(RED, 0.14) : 'rgba(0,168,107,0.14)', transform: `scale(${dk})`,
              ...ui(700, 16, bad ? RED : '#00A86B')}}>{txt(delta)}</span> : null}
          </div>
        </div>
        <div style={abs(r)}>
          <svg width={r.w} height={r.h} style={{overflow: 'visible'}}>
            <path d={`${line} L${cut[cut.length - 1].x},${r.h - 14} L${cut[0].x},${r.h - 14} Z`} fill={rgba(c.accent, 0.12)} />
            <path d={line} fill="none" stroke={c.accent} strokeWidth={4} strokeLinecap="round" strokeLinejoin="round" />
            <line x1={0} y1={r.h - 14} x2={r.w} y2={r.h - 14} stroke={p.line} strokeWidth={1.5} />
          </svg>
        </div>
        <div style={{position: 'absolute', left: 214, top: DL - 34, ...ui(700, 19, p.ink)}}>{txt(d.title) || c.list}</div>
        {rows.map((x, idx) => {
          const e = x.r ?? {};
          const y = DL + slotY(rows, idx, DR);
          const fresh = x.T >= 0 ? ease(t, x.T, 0.25) * (1 - ease(t, x.T + 1.3, 0.8)) : 0;
          const ebad = e.tone === 'bad';
          return (
            <div key={x.i} style={{position: 'absolute', left: 214, top: y, width: 660, height: DR, display: 'flex', alignItems: 'center', gap: 18, paddingLeft: 10, boxSizing: 'border-box',
              borderBottom: `1px solid ${p.line}`, opacity: x.k, transform: `translateY(${(1 - x.k) * -14}px)`, background: fresh > 0 ? rgba(c.accent, 0.1 * fresh) : undefined}}>
              {cols.map((col, j) => <span key={col.key} style={{width: col.w || undefined, flex: col.w ? 'none' : 1, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
                ...ui(col.bold ? 700 : 500, col.bold ? 19 : 17, col.bold ? (ebad ? RED : p.ink) : p.mut)}}>{txt(e[col.key])}</span>).concat(
                <span key="chip" style={{padding: '2px 10px', borderRadius: 6, background: ebad ? rgba(RED, 0.14) : rgba(c.accent, 0.18), ...ui(700, 14, ebad ? RED : inkOf(c.accent))}}>{txt(e.status) || c.chip}</span>,
                <span key="time" style={{...ui(500, 15, p.mut), marginRight: 14}}>{txt(e.time) || (x.T >= 0 ? 'Just now' : 'Today')}</span>)}
            </div>
          );
        })}
      </>
    );
  },
});

// ================================================================== aplikacije kao podaci (svaka ~5–10 linija)
const SPEC_SKINS: Record<string, Skin> = {
  // AI chat
  copilot: chatApp({name: 'Copilot', accent: '#2563EB', mark: gradMark('C', 'conic-gradient(from 200deg,#2563EB,#7C3AED,#F59E0B,#10B981,#2563EB)'),
    greeting: 'Hey, what\'s on your mind today?', placeholder: 'Message Copilot', chips: ['Think Deeper'], light: pal('#FAF8F5', '#1F1F1F', '#6B6B6B', '#E7E2DA', '#F1EDE6')}),
  grok: chatApp({name: 'Grok', accent: '#111111', mark: (s) => <div style={{width: s, height: s, borderRadius: s * 0.26, background: '#111', display: 'grid', placeItems: 'center'}}>
    <Ph.XLogo size={s * 0.55} weight="bold" color="#fff" /></div>, greeting: 'What do you want to know?', placeholder: 'Ask anything', chips: ['DeepSearch', 'Think'], model: 'Grok 4'}),
  deepseek: chatApp({name: 'DeepSeek', accent: '#4D6BFE', mark: letterMark('D', '#4D6BFE', true), greeting: 'How can I help you today?', placeholder: 'Message DeepSeek', chips: ['DeepThink', 'Search']}),
  metaai: chatApp({name: 'Meta AI', accent: '#0866FF', mark: (s) => <div style={{width: s, height: s, borderRadius: s / 2, background: 'conic-gradient(#0866FF,#A033FF,#FF5C87,#0866FF)', padding: s * 0.14, boxSizing: 'border-box'}}>
    <div style={{width: '100%', height: '100%', borderRadius: '50%', background: '#fff'}} /></div>, greeting: 'Ask Meta AI anything', placeholder: 'Ask Meta AI…'}),
  lechat: chatApp({name: 'Le Chat', accent: '#FA520F', mark: letterMark('M', '#FA520F'), greeting: 'Bonjour! How can I help?', placeholder: 'Ask Le Chat', chips: ['Think', 'Research'], model: 'Mistral'}),
  // liste
  outlook: listApp({name: 'Outlook', accent: '#0F6CBD', mark: letterMark('O', '#0F6CBD'), nav: ['Inbox', 'Drafts', 'Sent Items', 'Archive'], navIcons: [Ph.Tray, Ph.File, Ph.PaperPlaneRight, Ph.Archive],
    button: 'New mail', cols: [{key: 'from', label: 'From', w: 170, bold: true}, {key: 'subject', label: 'Subject', w: 0}, {key: 'time', label: 'Received', w: 90, right: true, muted: true}]}),
  hubspot: listApp({name: 'HubSpot', accent: '#FF7A59', mark: letterMark('H', '#FF7A59', true), side: '#2D3E50', sideInk: '#FFFFFF', nav: ['Deals', 'Contacts', 'Companies', 'Reports'],
    navIcons: [Ph.Handshake, Ph.Users, Ph.Buildings, Ph.ChartBar], title: 'Deals', button: 'Create deal',
    cols: [{key: 'name', label: 'Deal name', w: 0, bold: true}, {key: 'stage', label: 'Stage', w: 150, chip: true}, {key: 'amount', label: 'Amount', w: 110, right: true, bold: true}],
    chipColors: {'closed won': ['#D6F5E3', '#00A86B'], 'closed lost': [rgba(RED, 0.14), RED]}}),
  linear: listApp({name: 'Linear', accent: '#5E6AD2', mark: letterMark('L', '#5E6AD2', true), nav: ['My issues', 'Inbox', 'Projects', 'Cycles'], navIcons: [Ph.CircleDashed, Ph.Tray, Ph.Cube, Ph.ArrowsClockwise],
    title: 'Issues', button: 'New issue', cols: [{key: 'id', label: 'ID', w: 80, muted: true}, {key: 'title', label: 'Title', w: 0, bold: true}, {key: 'status', label: 'Status', w: 130, chip: true}],
    chipColors: {done: ['#E8E6FB', '#5E6AD2'], 'in progress': ['#FFF4D6', '#B7791F'], todo: ['#EEF1F4', '#656D76']}}),
  // dashboard
  gumroad: dashApp({name: 'Gumroad', accent: '#FF90E8', mark: letterMark('G', '#000000', true), nav: ['Home', 'Products', 'Sales', 'Customers'], metric: 'Revenue', list: 'Recent sales', chip: 'Paid',
    cols: [{key: 'amount', w: 110, bold: true}, {key: 'product', w: 200}, {key: 'customer', w: 0}]}),
  kajabi: dashApp({name: 'Kajabi', accent: '#2E73F7', mark: letterMark('K', '#2E73F7'), nav: ['Dashboard', 'Products', 'Sales', 'Contacts'], metric: 'Net revenue', list: 'New purchases', chip: 'Purchased',
    cols: [{key: 'amount', w: 110, bold: true}, {key: 'product', w: 200}, {key: 'customer', w: 0}]}),
  paypal: dashApp({name: 'PayPal', accent: '#0070E0', mark: (s) => <div style={{width: s, height: s, borderRadius: s * 0.26, background: '#003087', display: 'grid', placeItems: 'center'}}>
    <Ph.PaypalLogo size={s * 0.6} weight="fill" color="#fff" /></div>, nav: ['Home', 'Activity', 'Wallet', 'Payments'], metric: 'PayPal balance', list: 'Recent activity', chip: 'Completed'}),
  analytics: dashApp({name: 'Analytics', accent: '#E8710A', mark: (s) => <div style={{width: s, height: s, display: 'flex', alignItems: 'flex-end', gap: s * 0.08}}>
    {[0.45, 0.7, 1].map((h, i) => <div key={i} style={{width: s * 0.26, height: s * h, borderRadius: s * 0.13, background: ['#F9AB00', '#E37400', '#E37400'][i]}} />)}</div>,
    nav: ['Home', 'Reports', 'Explore', 'Advertising'], metric: 'Users', list: 'Top pages', chip: 'Views', cols: [{key: 'page', w: 0, bold: true}, {key: 'views', w: 120}]}),
  beehiiv: dashApp({name: 'beehiiv', accent: '#FFB800', mark: letterMark('b', '#000000', true), nav: ['Dashboard', 'Posts', 'Audience', 'Grow'], metric: 'Subscribers', list: 'New subscribers', chip: 'Active',
    cols: [{key: 'email', w: 0, bold: true}, {key: 'source', w: 160}]}),
};

// ================================================================== custom: bilo koji alat iz plana
const customCache = new Map<string, Skin>();
export const customSkin = (d: any): Skin => {
  const b = d.brand ?? {};
  const name = txt(b.name) || 'App';
  const color = /^#[0-9a-f]{6}$/i.test(String(b.color ?? '')) ? String(b.color) : '#5B5BD6';
  const src = file(b.logo) ?? null;
  const type = ['chat', 'list', 'dashboard'].includes(d.type) ? d.type : 'list';
  const key = JSON.stringify([type, name, color, src, b.nav, d.columns]);
  const hit = customCache.get(key);
  if (hit) return hit;
  const mark = src ? logoMark(src) : letterMark(name, color);
  const nav: string[] = (b.nav ?? (type === 'dashboard' ? ['Dashboard', 'Sales', 'Customers', 'Settings'] : ['Inbox', 'Contacts', 'Reports', 'Settings'])).map(txt);
  const cols: Col[] = (d.columns ?? []).map((c0: any, i: number) => ({key: String(c0.key ?? c0), label: txt(c0.label) || String(c0.key ?? c0), w: Number(c0.w ?? (i === 0 ? 0 : 140)),
    bold: c0.bold ?? i === 0, chip: Boolean(c0.chip), right: Boolean(c0.right)}));
  const skin = type === 'chat' ? chatApp({name, mark, accent: color, greeting: txt(b.greeting) || undefined, placeholder: txt(b.placeholder) || undefined})
    : type === 'dashboard' ? dashApp({name, mark, accent: color, nav, metric: txt(b.metric) || 'Revenue', list: txt(b.list) || 'Recent activity', chip: txt(b.chip) || 'New',
      cols: cols.length ? cols.map((c0) => ({key: c0.key, w: c0.w, bold: c0.bold})) : undefined})
      : listApp({name, mark, accent: color, nav, button: txt(b.button) || undefined, cols: cols.length ? cols : [{key: 'name', label: 'Name', w: 0, bold: true}, {key: 'status', label: 'Status', w: 140, chip: true}, {key: 'time', label: 'Updated', w: 100, right: true, muted: true}]});
  customCache.set(key, skin);
  return skin;
};

export const SPEC_APPS = Object.keys(SPEC_SKINS);
export {SPEC_SKINS};
export type {St};
