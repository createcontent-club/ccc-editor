import {Img, staticFile} from 'remotion';
import * as Ph from '@phosphor-icons/react';
import {W, H, PW, PH, Pal, Rect, St, Skin, ease, T, txt, RED, rgba, ui, abs, POP, Caret, arrivals, slotY} from './appCore';
import {AppIcon, GmailMark} from './appIcons';

/**
 * Desktop skinovi faze 1 (14. nov 2026):
 *   gmail:            inbox (mejlovi stižu na reč) + Compose (kucanje, Send, "Message sent")
 *   n8n/zapier/make:  automatizacija — čvorovi se spajaju na reč, `run` pušta tok kroz njih (✓ / crveni čvor staje)
 *   web:              PRAVA stranica (screenshot iz `ccc shot`) u pregledaču + kursor, klik, marker i skrol do izgovorene fraze
 */

// ------------------------------------------------------------------ Gmail
const GM_PAL: {light: Pal; dark: Pal} = {
  light: {bg: '#F8FAFD', rail: '#F8FAFD', card: '#FFFFFF', line: '#E5E7EB', ink: '#1F1F1F', mut: '#5E5E5E', bubble: '#EAF1FB', menu: '#FFFFFF'},
  dark: {bg: '#1F1F1F', rail: '#1F1F1F', card: '#2D2D2D', line: '#3C3C3C', ink: '#E3E3E3', mut: '#A8A8A8', bubble: '#2D2F31', menu: '#2D2D2D'},
};
const GM_TOP = 156, GM_ROW = 50;
const DRAFT: Rect = {x: 446, y: 150, w: 438, h: 438};

const gmail: Skin = {
  menuFrom: 'compose',
  pal: GM_PAL,
  // ceo prozor je sitan na telefonu: početni kadar = pošiljaoci + naslovi krupno; Compose → zoom na njega, posle slanja nazad
  base: () => ({x: 492, y: 290, s: 1.72}),
  autoZoom: (st) => {
    const z: {to: string; T: number; scale?: number}[] = [];
    if (st.d.compose) z.push({to: 'draft', T: T(st.d.compose, 1e9) + 0.1, scale: 1.75});
    if (st.d.send) z.push({to: 'main', T: T(st.d.send, 1e9) + 0.35, scale: 1.72});
    return z;
  },
  anchors: (st) => {
    const a: Record<string, Rect> = {
      compose: {x: 16, y: 114, w: 156, h: 58}, inbox: {x: 8, y: 188, w: 184, h: 40}, search: {x: 232, y: 54, w: 520, h: 46},
      list: {x: 200, y: GM_TOP, w: 700, h: 8 * GM_ROW}, sidebar: {x: 0, y: 104, w: 200, h: 496},
      draft: DRAFT, input: {x: DRAFT.x + 16, y: DRAFT.y + 140, w: DRAFT.w - 32, h: 200}, send: {x: DRAFT.x + 18, y: DRAFT.y + DRAFT.h - 58, w: 96, h: 42},
      toast: {x: 214, y: 486, w: 300, h: 50}, main: {x: 186, y: 100, w: 612, h: 440},
    };
    for (let i = 0; i < 8; i++) a[`row${i}`] = {x: 200, y: GM_TOP + i * GM_ROW, w: 700, h: GM_ROW};
    if (st.d.compose) (a as any).__taps = [{x: a.compose.x + 70, y: a.compose.y + 29, T: T(st.d.compose, 1e9) - 0.05, click: true}];
    return a;
  },
  Body: ({st, a}) => {
    const d = st.d, p = st.pal, t = st.t;
    const list = arrivals(d.emails ?? [], t).slice(0, 8);
    const unreadN = (d.emails ?? []).filter((e: any) => e?.unread !== false && (typeof e?.atT !== 'number' || t >= e.atT)).length;
    const inboxN = d.count != null ? Number(String(txt(d.count)).replace(/,/g, '')) + 0 : unreadN;
    const cT = d.compose ? T(d.compose, 1e9) : 1e9;
    const sendT = d.send ? T(d.send, 1e9) : 1e9;
    const ck = ease(t, cT, 0.4) * (1 - ease(t, sendT, 0.35));
    const toast = ease(t, sendT + 0.2, 0.35) * (1 - ease(t, sendT + 2.6, 0.4));
    return (
      <>
        <div style={{position: 'absolute', left: 0, top: 44, width: W, height: 60, display: 'flex', alignItems: 'center', gap: 16, paddingLeft: 24}}>
          <Ph.List size={28} color={p.mut} />
          <GmailMark size={38} />
          <span style={{...ui(400, 26, p.mut), marginRight: 30}}>Gmail</span>
        </div>
        <div style={{...abs(a.search), borderRadius: 23, background: p.bubble, display: 'flex', alignItems: 'center', gap: 14, paddingLeft: 18}}>
          <Ph.MagnifyingGlass size={22} color={p.mut} /><span style={ui(400, 19, p.mut)}>Search mail</span>
        </div>
        <div style={{...abs(a.compose), borderRadius: 18, background: st.dark ? '#004A77' : '#C2E7FF', display: 'flex', alignItems: 'center', gap: 12, paddingLeft: 20,
          boxShadow: '0 1px 3px rgba(0,0,0,0.12)'}}>
          <Ph.PencilSimple size={24} color={p.ink} /><span style={ui(600, 20, p.ink)}>Compose</span>
        </div>
        {([['Inbox', Ph.Tray], ['Starred', Ph.Star], ['Snoozed', Ph.Clock], ['Sent', Ph.PaperPlaneRight], ['Drafts', Ph.File]] as any[]).map(([s, I], i) => (
          <div key={s} style={{position: 'absolute', left: 8, top: 188 + i * 42, width: 184, height: 40, borderRadius: 20, background: i === 0 ? (st.dark ? '#004A77' : '#D3E3FD') : undefined,
            display: 'flex', alignItems: 'center', gap: 14, paddingLeft: 16, boxSizing: 'border-box'}}>
            <I size={22} weight={i === 0 ? 'fill' : 'regular'} color={p.ink} />
            <span style={{...ui(i === 0 ? 700 : 500, 18, p.ink), flex: 1}}>{s}</span>
            {i === 0 && inboxN > 0 ? <span style={{...ui(700, 16, p.ink), marginRight: 14}}>{inboxN.toLocaleString('en-US')}</span> : null}
          </div>
        ))}
        <div style={{position: 'absolute', left: 200, top: 110, width: 690, height: GM_TOP - 110 + 8 * GM_ROW, borderRadius: 16, background: p.card}} />
        <div style={{position: 'absolute', left: 216, top: 118, display: 'flex', gap: 24, alignItems: 'center'}}>
          <Ph.Square size={22} color={p.mut} /><Ph.ArrowClockwise size={22} color={p.mut} /><Ph.DotsThreeVertical size={22} color={p.mut} />
        </div>
        {list.map((x, idx) => {
          const e = x.r ?? {};
          const y = GM_TOP + slotY(list, idx, GM_ROW);
          const unread = e.unread !== false;
          const fresh = x.T >= 0 ? ease(t, x.T, 0.25) * (1 - ease(t, x.T + 1.4, 0.8)) : 0;
          const bad = e.tone === 'bad';
          return (
            <div key={x.i} style={{position: 'absolute', left: 200, top: y, width: 690, height: GM_ROW, display: 'flex', alignItems: 'center', gap: 16, paddingLeft: 16,
              boxSizing: 'border-box', borderBottom: `1px solid ${p.line}`, background: fresh > 0 ? rgba(st.acc, 0.16 * fresh) : unread ? p.card : (st.dark ? '#262626' : '#F2F6FC'),
              opacity: x.k, transform: `translateY(${(1 - x.k) * -16}px)`}}>
              <Ph.Square size={20} color={p.mut} />
              <Ph.Star size={20} weight={e.star ? 'fill' : 'regular'} color={e.star ? '#F4B400' : p.mut} />
              <span style={{...ui(unread ? 700 : 500, 18, bad ? RED : p.ink), width: 150, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'}}>{txt(e.from)}</span>
              <span style={{flex: 1, minWidth: 0, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', ...ui(400, 18, p.mut)}}>
                {txt(e.label) ? <span style={{padding: '2px 8px', borderRadius: 6, marginRight: 8, background: rgba(st.acc, 0.22), ...ui(700, 14, p.ink)}}>{txt(e.label)}</span> : null}
                <span style={{fontWeight: unread ? 700 : 500, color: bad ? RED : p.ink}}>{txt(e.subject)}</span>{txt(e.snippet) ? ` - ${txt(e.snippet)}` : ''}
              </span>
              <span style={{...ui(unread ? 700 : 500, 15, p.ink), width: 66, textAlign: 'right', marginRight: 16}}>{txt(e.time) || (x.T >= 0 ? 'now' : '9:12 AM')}</span>
            </div>
          );
        })}
        {ck > 0 ? (
          <div style={{...abs(DRAFT), borderRadius: '14px 14px 0 0', background: p.card, boxShadow: '0 12px 40px rgba(0,0,0,0.28)', overflow: 'hidden', zIndex: 10,
            opacity: Math.min(1, ck * 1.4), transform: `translateY(${(1 - ck) * 120}px)`}}>
            <div style={{height: 46, background: p.bubble, display: 'flex', alignItems: 'center', paddingLeft: 18, ...ui(600, 18, p.ink)}}>{txt(d.compose?.title) || 'New Message'}</div>
            <div style={{height: 44, borderBottom: `1px solid ${p.line}`, display: 'flex', alignItems: 'center', gap: 10, padding: '0 18px', ...ui(400, 18, p.mut)}}>
              To <span style={{color: p.ink}}>{txt(d.compose?.to)}</span></div>
            <div style={{height: 44, borderBottom: `1px solid ${p.line}`, display: 'flex', alignItems: 'center', padding: '0 18px', ...ui(500, 18, txt(d.compose?.subject) ? p.ink : p.mut)}}>
              {txt(d.compose?.subject) || 'Subject'}</div>
            <div style={{position: 'absolute', left: 18, right: 18, top: 150, ...ui(400, 20, p.ink, 1.45)}}>{st.typed}<Caret st={st} size={20} color={p.ink} /></div>
            <div style={{position: 'absolute', left: 18, bottom: 16, height: 42, padding: '0 26px', borderRadius: 21, background: '#0B57D0', display: 'flex', alignItems: 'center',
              ...ui(600, 18, '#fff')}}>Send</div>
          </div>
        ) : null}
        {toast > 0 ? (
          <div style={{...abs(a.toast), borderRadius: 8, background: '#323232', display: 'flex', alignItems: 'center', gap: 16, paddingLeft: 20, zIndex: 12,
            opacity: toast, transform: `translateY(${(1 - toast) * 20}px)`, ...ui(500, 18, '#fff')}}>
            Message sent<span style={{color: '#A8C7FA', fontWeight: 600}}>Undo</span></div>
        ) : null}
      </>
    );
  },
};

// ------------------------------------------------------------------ automatizacija (n8n / Zapier / Make)
type Style = 'n8n' | 'zapier' | 'make';
const AUTO_PAL: Record<Style, Pal> = {
  n8n: {bg: '#2E2E2E', rail: '#262626', card: '#414244', line: '#5E5F61', ink: '#F2F2F2', mut: '#A3A3A3', bubble: '#3A3A3A', menu: '#3A3A3A'},
  zapier: {bg: '#F6F5F2', rail: '#FFFFFF', card: '#FFFFFF', line: '#D7D3CB', ink: '#201515', mut: '#6B6460', bubble: '#ECE9E3', menu: '#FFFFFF'},
  make: {bg: '#F3F1FA', rail: '#FFFFFF', card: '#FFFFFF', line: '#C9C2E6', ink: '#1E1B3A', mut: '#6E6990', bubble: '#E7E3F5', menu: '#FFFFFF'},
};
const GREEN = '#22C55E';

const nodeLayout = (style: Style, n: number): Rect[] => {
  if (style === 'zapier') {
    const h = 96, gap = Math.min(40, (H - 120 - n * h) / Math.max(1, n - 1));
    const total = n * h + (n - 1) * gap;
    const y0 = 72 + Math.max(0, (H - 72 - total) / 2);
    return Array.from({length: n}).map((_, i) => ({x: (W - 500) / 2, y: y0 + i * (h + gap), w: 500, h}));
  }
  const size = n <= 3 ? 150 : n === 4 ? 132 : 112;
  const span = W - 120;
  const gap = n > 1 ? Math.max(48, Math.min(150, (span - n * size) / (n - 1))) : 0;
  const total = n * size + (n - 1) * gap;
  const x0 = (W - total) / 2;
  return Array.from({length: n}).map((_, i) => ({x: x0 + i * (size + gap), y: 250, w: size, h: size}));
};

const autoSkin = (style: Style): Skin => ({
  menuFrom: 'node0',
  // kadar = ceo tok, što krupnije (natpisi čvorova ≥ ~30 px na videu)
  base: (st, a) => {
    const f = a.flow ?? a.canvas;
    return {x: f.x + f.w / 2, y: f.y + f.h / 2, s: Math.max(0.9, Math.min(1.9, 1010 / f.w, 860 / f.h))};
  },
  pal: {light: AUTO_PAL[style], dark: AUTO_PAL[style]},
  anchors: (st) => {
    const nodes: any[] = (st.d.nodes ?? []).slice(0, 6);
    const rs = nodeLayout(style, nodes.length || 1);
    const a: Record<string, Rect> = {canvas: {x: 0, y: 44, w: W, h: H - 44}, title: {x: 20, y: 52, w: 520, h: 40}};
    rs.forEach((r, i) => { a[`node${i}`] = style === 'zapier' ? r : {x: r.x - 30, y: r.y - 10, w: r.w + 60, h: r.h + 96}; });
    if (rs.length) {
      const l = rs[0], rr = rs[rs.length - 1];
      a.flow = style === 'zapier' ? {x: l.x - 30, y: l.y - 24, w: l.w + 60, h: rr.y + rr.h - l.y + 48}
        : {x: l.x - 40, y: Math.min(l.y, rr.y) - 30, w: rr.x + rr.w - l.x + 80, h: Math.max(l.y + l.h, rr.y + rr.h) - Math.min(l.y, rr.y) + 120};
    }
    return a;
  },
  Body: ({st}) => {
    const d = st.d, p = st.pal, t = st.t;
    const nodes: any[] = (d.nodes ?? []).slice(0, 6);
    const rs = nodeLayout(style, nodes.length || 1);
    const ins = nodes.map((n, i) => (typeof n?.atT === 'number' ? ease(t, n.atT, 0.45, POP) : ease(t, 0.1 + i * 0.12, 0.45, POP)));
    const runT = d.run ? T(d.run, 1e9) : 1e9;
    const badAt = nodes.findIndex((n) => n?.tone === 'bad');
    const reachT = (i: number) => runT + i * 0.55;
    const reached = (i: number) => t >= reachT(i) && (badAt < 0 || i <= badAt);
    const ok = (i: number) => reached(i) && i !== badAt;
    const dark = style === 'n8n';
    const dots = style !== 'zapier';
    const conn = (i: number) => {  // linija od čvora i-1 do i: crta se kad čvor i uđe
      const A = rs[i - 1], B = rs[i];
      const k = ins[i];
      const live = reached(i);
      const col = live ? (i === badAt ? RED : GREEN) : style === 'make' ? '#A79BDF' : p.line;
      if (style === 'zapier') {
        const x = A.x + A.w / 2, y1 = A.y + A.h, y2 = B.y;
        return (
          <g key={`c${i}`}>
            <line x1={x} y1={y1} x2={x} y2={y1 + (y2 - y1) * k} stroke={col} strokeWidth={3} />
            {k > 0.9 ? <circle cx={x} cy={(y1 + y2) / 2} r={11} fill={p.card} stroke={p.line} strokeWidth={2} /> : null}
            {k > 0.9 ? <path d={`M${x - 5},${(y1 + y2) / 2} H${x + 5} M${x},${(y1 + y2) / 2 - 5} V${(y1 + y2) / 2 + 5}`} stroke={p.mut} strokeWidth={2} /> : null}
          </g>
        );
      }
      const x1 = A.x + A.w, y = A.y + A.h / 2, x2 = B.x;
      const xm = x1 + (x2 - x1) * k;
      const ball = d.run && t >= reachT(i - 1) && t < reachT(i) + 0.05 && (badAt < 0 || i <= badAt)
        ? x1 + (x2 - x1) * Math.min(1, (t - reachT(i - 1)) / 0.55) : null;
      return (
        <g key={`c${i}`}>
          {style === 'make'
            ? <path d={`M${x1},${y} C${x1 + 40},${y - 30} ${xm - 40},${y + 30} ${xm},${y}`} fill="none" stroke={col} strokeWidth={5} strokeDasharray="2 12" strokeLinecap="round" />
            : <line x1={x1} y1={y} x2={xm} y2={y} stroke={col} strokeWidth={3} />}
          {style === 'n8n' && k > 0.95 ? <path d={`M${x2 - 12},${y - 7} L${x2 - 1},${y} L${x2 - 12},${y + 7}`} fill="none" stroke={col} strokeWidth={3} /> : null}
          {ball != null ? <circle cx={ball} cy={y} r={8} fill={GREEN} /> : null}
        </g>
      );
    };
    return (
      <>
        {dots ? <div style={{position: 'absolute', left: 0, top: 44, width: W, height: H - 44,
          backgroundImage: `radial-gradient(${dark ? 'rgba(255,255,255,0.12)' : 'rgba(80,60,160,0.14)'} 1.5px, transparent 1.6px)`, backgroundSize: '24px 24px'}} /> : null}
        <div style={{position: 'absolute', left: 20, top: 52, height: 40, display: 'flex', alignItems: 'center', gap: 12}}>
          {style === 'n8n' ? <span style={{...ui(800, 22, '#EA4B71'), letterSpacing: '-0.03em'}}>n8n</span>
            : style === 'zapier' ? <span style={{...ui(800, 22, '#FF4F00'), letterSpacing: '-0.03em'}}>_zapier</span>
              : <span style={{...ui(800, 22, '#6D00CC'), letterSpacing: '-0.02em'}}>make</span>}
          <span style={ui(600, 20, p.ink)}>{txt(d.title) || 'Lead follow-up'}</span>
        </div>
        <div style={{position: 'absolute', right: 22, top: 56, display: 'flex', alignItems: 'center', gap: 10, ...ui(600, 17, p.mut)}}>
          {d.run && t >= runT ? (badAt >= 0 && t >= reachT(badAt) ? <span style={{color: RED}}>Error</span> : t >= reachT(nodes.length - 1) + 0.3
            ? <span style={{color: GREEN}}>Success</span> : <span>Running…</span>) : <span>{style === 'zapier' ? 'Published' : 'Active'}</span>}
          <div style={{width: 46, height: 26, borderRadius: 13, background: GREEN, position: 'relative'}}>
            <div style={{position: 'absolute', right: 3, top: 3, width: 20, height: 20, borderRadius: 10, background: '#fff'}} /></div>
        </div>
        <svg width={W} height={H} style={{position: 'absolute', left: 0, top: 0}}>{rs.map((_, i) => (i ? conn(i) : null))}</svg>
        {nodes.map((n, i) => {
          const r = rs[i];
          const k = ins[i];
          const isOk = ok(i), isBad = reached(i) && i === badAt;
          const ring = isBad ? RED : isOk ? GREEN : undefined;
          const app = txt(n?.app) || txt(n?.icon) || 'webhook';
          const badge = (isOk || isBad) ? ease(t, reachT(i) + 0.15, 0.3, POP) : 0;
          if (style === 'zapier') {
            return (
              <div key={i} style={{...abs(r), borderRadius: 14, background: p.card, border: `2px solid ${ring ?? p.line}`, display: 'flex', alignItems: 'center', gap: 16,
                padding: '0 18px', opacity: Math.min(1, k * 1.3), transform: `translateY(${(1 - k) * 16}px)`, boxShadow: '0 2px 6px rgba(0,0,0,0.06)'}}>
                <AppIcon app={app} size={50} />
                <div style={{flex: 1, minWidth: 0}}>
                  <div style={ui(700, 16, i === 0 ? '#FF4F00' : p.mut)}>{i === 0 ? '1. Trigger' : `${i + 1}. Action`}</div>
                  <div style={{...ui(700, 22, isBad ? RED : p.ink), whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'}}>{txt(n)}</div>
                  {txt(n?.sub) ? <div style={{...ui(400, 15, p.mut), whiteSpace: 'nowrap', overflow: 'hidden'}}>{txt(n.sub)}</div> : null}
                </div>
                {badge > 0 ? <div style={{transform: `scale(${badge})`}}>{isBad ? <Ph.WarningCircle size={30} weight="fill" color={RED} />
                  : <Ph.CheckCircle size={30} weight="fill" color={GREEN} />}</div> : null}
              </div>
            );
          }
          const round = style === 'make';
          return (
            <div key={i} style={{position: 'absolute', left: r.x, top: r.y, width: r.w, opacity: Math.min(1, k * 1.3), transform: `scale(${0.8 + 0.2 * k})`}}>
              <div style={{width: r.w, height: r.h, borderRadius: round ? r.w / 2 : i === 0 && style === 'n8n' ? '50px 18px 18px 50px' : 18,
                background: round ? '#FFFFFF' : p.card, border: `${round ? 5 : 2.5}px solid ${ring ?? (round ? '#B7ACE8' : p.line)}`, boxSizing: 'border-box',
                display: 'grid', placeItems: 'center', boxShadow: ring ? `0 0 0 6px ${rgba(ring, 0.22)}` : '0 6px 16px rgba(0,0,0,0.18)', position: 'relative'}}>
                <AppIcon app={app} size={Math.round(r.w * (round ? 0.6 : 0.56))} radius={round ? r.w * 0.3 : undefined} />
                {i === 0 && style === 'n8n' ? <div style={{position: 'absolute', left: -14, top: r.h / 2 - 14, width: 28, height: 28, borderRadius: 14, background: '#FF6D5A',
                  display: 'grid', placeItems: 'center'}}><Ph.Lightning size={16} weight="fill" color="#fff" /></div> : null}
                {badge > 0 ? <div style={{position: 'absolute', right: -12, top: -12, transform: `scale(${badge})`}}>
                  {isBad ? <Ph.WarningCircle size={34} weight="fill" color={RED} /> : <Ph.CheckCircle size={34} weight="fill" color={GREEN} />}</div> : null}
                {round && badge > 0 && !isBad ? <div style={{position: 'absolute', top: -16, left: r.w / 2 - 14, width: 28, height: 28, borderRadius: 14, background: '#6D00CC',
                  display: 'grid', placeItems: 'center', transform: `scale(${badge})`, ...ui(700, 15, '#fff')}}>1</div> : null}
              </div>
              <div style={{width: r.w + 60, marginLeft: -30, marginTop: 14, textAlign: 'center', ...ui(700, 23, isBad ? RED : p.ink, 1.2)}}>{txt(n)}</div>
              {txt(n?.sub) ? <div style={{width: r.w + 60, marginLeft: -30, textAlign: 'center', ...ui(400, 18, p.mut, 1.2)}}>{txt(n.sub)}</div> : null}
            </div>
          );
        })}
      </>
    );
  },
});

// ------------------------------------------------------------------ živa stranica (pravi screenshot + kursor)
const PAGE_TOP = 96;
const webGeo = (st: St, phone: boolean) => {
  const d = st.d;
  const fw = phone ? PW : W, top = phone ? 104 : PAGE_TOP;
  const sc = d.w ? fw / d.w : 1;
  const pageH = (d.h ?? 1000) * sc;
  const marks: any[] = (d.marks ?? []).filter((m: any) => m?.rect);
  const rectOf = (to: any): Rect | null => {
    if (to == null) return null;
    const s = String(to);
    if (s === 'focus' && d.focus) return {x: d.focus.x * sc, y: d.focus.y * sc, w: d.focus.w * sc, h: d.focus.h * sc};
    const mi = /^mark(\d+)$/.exec(s);
    const m = mi ? marks[parseInt(mi[1], 10)] : marks.find((x: any) => String(x.text).toLowerCase() === s.toLowerCase());
    return m ? {x: m.rect.x * sc, y: m.rect.y * sc, w: m.rect.w * sc, h: m.rect.h * sc} : null;
  };
  // skrol: stranica se pomera na reč tako da cilj stoji u gornjoj trećini (nikad ispod dna stranice)
  const viewH = (phone ? PH : H) - top;
  let scroll = 0;
  for (const sc0 of ([] as any[]).concat(d.scroll ?? [])) {
    const r = rectOf(sc0?.to);
    if (!r) continue;
    const target = Math.max(0, Math.min(pageH - viewH, r.y - viewH * 0.3));
    scroll = scroll + (target - scroll) * ease(st.t, T(sc0, 0), 0.9);
  }
  return {sc, pageH, marks, rectOf, scroll, top, fw};
};

const webSkin = (phone: boolean): Skin => ({
  menuFrom: 'page',
  frame: phone ? 'phone' : 'window',
  size: phone ? {w: PW, h: PH} : undefined,
  chrome: false,
  maxZoom: phone ? 2.6 : 2.4,
  pal: {light: {bg: '#FFFFFF', rail: '#F1F3F4', card: '#FFFFFF', line: '#DADCE0', ink: '#202124', mut: '#5F6368', bubble: '#F1F3F4', menu: '#FFFFFF'},
    dark: {bg: '#FFFFFF', rail: '#35363A', card: '#FFFFFF', line: '#4A4C50', ink: '#E8EAED', mut: '#9AA0A6', bubble: '#202124', menu: '#FFFFFF'}},
  anchors: (st) => {
    const g = webGeo(st, phone);
    const a: Record<string, Rect> = {page: {x: 0, y: g.top, w: g.fw, h: (phone ? PH : H) - g.top}, bar: {x: 0, y: 0, w: g.fw, h: g.top}};
    const put = (k: string, r: Rect | null) => { if (r) a[k] = {x: r.x, y: r.y + g.top - g.scroll, w: r.w, h: r.h}; };
    put('focus', g.rectOf('focus'));
    g.marks.forEach((_, i) => put(`mark${i}`, g.rectOf(`mark${i}`)));
    const taps = g.marks.map((m, i) => (m.click && typeof m.atT === 'number' && a[`mark${i}`]
      ? {x: a[`mark${i}`].x + a[`mark${i}`].w / 2, y: a[`mark${i}`].y + a[`mark${i}`].h / 2, T: m.atT - 0.05, click: true} : null)).filter(Boolean);
    if (taps.length) (a as any).__taps = taps;
    return a;
  },
  base: (st, a) => {
    const f = a.focus ?? a.page;
    return phone ? {x: PW / 2, y: Math.max(330, Math.min(PH - 330, f.y + f.h / 2)), s: 2.0}
      : {x: W / 2, y: H / 2, s: 1.0};
  },
  Body: ({st}) => {
    const d = st.d, p = st.pal, t = st.t;
    const g = webGeo(st, phone);
    const host = String(d.url || '').replace(/^https?:\/\//, '').replace(/^www\./, '').split('/')[0] || 'example.com';
    return (
      <>
        <div style={{position: 'absolute', left: 0, top: g.top, width: g.fw, height: (phone ? PH : H) - g.top, overflow: 'hidden', background: '#fff'}}>
          <div style={{position: 'absolute', left: 0, top: -g.scroll, width: g.fw, height: g.pageH}}>
            {d.src ? <Img src={staticFile(d.src)} style={{width: g.fw, height: g.pageH, display: 'block'}} /> : null}
            {g.marks.map((m, i) => {
              const r = g.rectOf(`mark${i}`)!;
              const k = ease(t, T(m, 0.4), 0.45);
              if (k <= 0) return null;
              return <div key={i} style={{position: 'absolute', left: r.x - 4, top: r.y - 2, width: (r.w + 8) * k, height: r.h + 4, borderRadius: 6,
                background: rgba(st.acc, 0.42), mixBlendMode: 'multiply'}} />;
            })}
          </div>
        </div>
        {phone ? (
          <div style={{position: 'absolute', left: 0, top: 54, width: PW, height: 50, background: '#F2F2F7', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
            ...ui(500, 17, '#111')}}><Ph.LockSimple size={14} weight="fill" color="#555" />{host}</div>
        ) : (
          <div style={{position: 'absolute', left: 0, top: 0, width: W, height: PAGE_TOP, background: p.rail, borderBottom: `1px solid ${p.line}`}}>
            <div style={{position: 'absolute', left: 20, top: 16, display: 'flex', gap: 9}}>
              {['#FF5F57', '#FEBC2E', '#28C840'].map((c) => <div key={c} style={{width: 14, height: 14, borderRadius: 7, background: c}} />)}
            </div>
            <div style={{position: 'absolute', left: 96, top: 6, width: 260, height: 38, borderRadius: '10px 10px 0 0', background: '#fff', display: 'flex', alignItems: 'center',
              gap: 8, paddingLeft: 14, ...ui(500, 16, '#202124'), whiteSpace: 'nowrap', overflow: 'hidden'}}>
              <div style={{width: 16, height: 16, borderRadius: 4, background: st.acc, flex: 'none'}} />{txt(d.title) || host}</div>
            <div style={{position: 'absolute', left: 0, top: 44, width: W, height: 52, background: '#fff', display: 'flex', alignItems: 'center', gap: 14, paddingLeft: 18}}>
              <Ph.ArrowLeft size={20} color="#5F6368" /><Ph.ArrowRight size={20} color="#BDC1C6" /><Ph.ArrowClockwise size={20} color="#5F6368" />
              <div style={{flex: 1, marginRight: 18, height: 36, borderRadius: 18, background: '#F1F3F4', display: 'flex', alignItems: 'center', gap: 10, paddingLeft: 16,
                ...ui(400, 17, '#202124')}}><Ph.LockSimple size={15} weight="fill" color="#5F6368" />{host}</div>
            </div>
          </div>
        )}
      </>
    );
  },
});

export const DESK_SKINS: Record<string, Skin> = {gmail, n8n: autoSkin('n8n'), zapier: autoSkin('zapier'), make: autoSkin('make'),
  web: webSkin(false), webphone: webSkin(true)};
