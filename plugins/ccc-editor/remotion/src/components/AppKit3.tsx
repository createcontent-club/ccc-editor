import React from 'react';
import {Img, OffthreadVideo, staticFile} from 'remotion';
import * as Ph from '@phosphor-icons/react';
import {
  W, H, PW, PH, Pal, Rect, Skin, ease, T, txt, RED, rgba, ui, abs, POP, Caret, countAt, fmtIG, fmtNum, arrivals, slotY,
} from './appCore';
import {ClaudeMark} from './appIcons';

/**
 * UI kit faza 3 (14. nov 2026):
 *   terminal          — Claude Code u terminalu: linije stižu (komanda, izlaz, ✓/✗, alat "Write(...)"), kucanje u promptu
 *   cursor / vscode   — editor koda: fajlovi, kod sa bojama, nove linije se kucaju (zeleni diff), AI panel sa promptom
 *   canva             — dizajn: elementi ulaze na platno, "Magic" pravi varijante
 *   capcut            — montaža: pregled + timeline, rez (playhead), auto-titlovi pune traku
 *   ads               — Meta Ads Manager: kampanje, potrošnja/ROAS broje, kampanja se gasi/pali
 *   ytstudio          — YouTube Studio: pregledi/sati/pretplatnici broje, grafik, top video
 *   tiktok (telefon)  — video u feed-u: srca broje, srce iskače, komentari izlaze u fioci
 */

const MONO = '"JetBrains Mono", "SF Mono", Menlo, "DejaVu Sans Mono", monospace';
const mono = (w: number, size: number, color: string, lh = 1.45): React.CSSProperties =>
  ({fontFamily: MONO, fontWeight: w, fontSize: size, color, lineHeight: lh, letterSpacing: 0, whiteSpace: 'pre'});
const file = (x: any): string | null => (x && typeof x === 'object' && x.src ? x.src : null);
const pal = (bg: string, ink: string, mut: string, line: string, bubble: string, card = bg): Pal => ({bg, rail: bg, card, line, ink, mut, bubble, menu: card});
const shown = (x: any, t: number) => typeof x?.atT !== 'number' || t >= x.atT - 0.05;
const kIn = (x: any, t: number, len = 0.35) => (typeof x?.atT === 'number' ? ease(t, x.atT - 0.05, len) : 1);

// ------------------------------------------------------------------ terminal (Claude Code)
const TERM_TOP = 96, TERM_ROW = 34, TERM_BOT = 470;
const termLineH = (l: any) => (l?.kind === 'tool' && txt(l?.sub) ? TERM_ROW * 2 : TERM_ROW);
const terminal: Skin = {
  menuFrom: 'input',
  chrome: false,
  pal: {light: pal('#1A1A1A', '#E8E6E3', '#8A8782', '#333333', '#262626'), dark: pal('#1A1A1A', '#E8E6E3', '#8A8782', '#333333', '#262626')},
  base: () => ({x: W / 2, y: 330, s: 1.26}),
  anchors: (st) => {
    const a: Record<string, Rect> = {window: {x: 0, y: 0, w: W, h: H}, lines: {x: 20, y: TERM_TOP, w: W - 40, h: TERM_BOT - TERM_TOP},
      input: {x: 44, y: 492, w: W - 88, h: 64}, send: {x: W - 80, y: 500, w: 48, h: 48}, header: {x: 44, y: 52, w: 520, h: 40}};
    (st.d.lines ?? []).forEach((_: any, i: number) => { a[`line${i}`] = {x: 20, y: TERM_TOP + i * TERM_ROW, w: W - 40, h: TERM_ROW}; });
    return a;
  },
  Body: ({st, a}) => {
    const p = st.pal, d = st.d, t = st.t;
    const all: any[] = [...(d.lines ?? [])];
    if (d.send && st.sendP > 0) all.push({kind: 'prompt', text: st.sent, atT: T(d.send, 0)});
    const vis = all.filter((l) => shown(l, t));
    const total = vis.reduce((s0, l) => s0 + termLineH(l), 0);
    let y = TERM_TOP - Math.max(0, total - (TERM_BOT - TERM_TOP));
    const has = st.typed.length > 0;
    const ORANGE = '#D97757';
    return (
      <>
        <div style={{position: 'absolute', left: 0, top: 0, width: W, height: 40, background: '#262626', borderBottom: '1px solid #333'}}>
          <div style={{position: 'absolute', left: 18, top: 13, display: 'flex', gap: 8}}>
            {['#FF5F57', '#FEBC2E', '#28C840'].map((c) => <div key={c} style={{width: 13, height: 13, borderRadius: 7, background: c}} />)}</div>
          <div style={{position: 'absolute', left: 0, right: 0, top: 10, textAlign: 'center', ...mono(500, 15, '#A8A6A1')}}>{txt(d.title) || '~/my-app — claude'}</div>
        </div>
        <div style={{...abs(a.header), border: `1.5px solid ${ORANGE}`, borderRadius: 8, display: 'flex', alignItems: 'center', gap: 10, paddingLeft: 12}}>
          <span style={mono(700, 17, ORANGE)}>✻</span><span style={mono(600, 17, p.ink)}>Welcome to Claude Code</span>
          <span style={mono(400, 15, p.mut)}>{txt(d.model) || ''}</span>
        </div>
        <div style={{position: 'absolute', left: 44, top: TERM_TOP, width: W - 88, height: TERM_BOT - TERM_TOP, overflow: 'hidden'}}>
          {vis.map((l, i) => {
            const top = y - TERM_TOP;
            y += termLineH(l);
            const k = kIn(l, t, 0.25);
            const kind = l?.kind ?? 'out';
            const s0 = txt(l);
            const typed = kind === 'cmd' && typeof l?.atT === 'number' ? s0.slice(0, Math.round(Math.min(1, (t - l.atT) / Math.max(0.3, s0.length * 0.035)) * s0.length)) : s0;
            const row = (pre: React.ReactNode, body: React.ReactNode) => (
              <div key={i} style={{position: 'absolute', left: 0, top, width: W - 40, height: termLineH(l), opacity: k, display: 'flex', flexDirection: 'column'}}>
                <div style={{display: 'flex', gap: 10, height: TERM_ROW, alignItems: 'center'}}>{pre}{body}</div>
                {kind === 'tool' && txt(l?.sub) ? <div style={{height: TERM_ROW, display: 'flex', alignItems: 'center', paddingLeft: 26, ...mono(400, 17, p.mut)}}>⎿  {txt(l.sub)}</div> : null}
              </div>
            );
            if (kind === 'cmd') return row(<span style={mono(700, 18, '#4EC9B0')}>$</span>, <span style={mono(500, 18, p.ink)}>{typed}</span>);
            if (kind === 'prompt') return row(<span style={mono(700, 18, p.mut)}>&gt;</span>, <span style={mono(500, 18, p.ink)}>{s0}</span>);
            if (kind === 'ok') return row(<span style={mono(700, 18, '#4ADE80')}>✓</span>, <span style={mono(500, 18, '#4ADE80')}>{s0}</span>);
            if (kind === 'err') return row(<span style={mono(700, 18, RED)}>✗</span>, <span style={mono(500, 18, RED)}>{s0}</span>);
            if (kind === 'claude' || kind === 'tool') return row(<span style={mono(700, 18, kind === 'tool' ? '#4ADE80' : p.ink)}>⏺</span>,
              <span style={mono(kind === 'tool' ? 700 : 400, 18, p.ink)}>{s0}</span>);
            return row(<span style={{width: 14}} />, <span style={mono(400, 18, p.mut)}>{s0}</span>);
          })}
        </div>
        <div style={abs(a.input, {border: `1.5px solid ${has ? p.mut : '#444'}`, borderRadius: 8, display: 'flex', alignItems: 'center', gap: 12, paddingLeft: 16})}>
          <span style={mono(700, 19, p.mut)}>&gt;</span>
          <span style={{...mono(500, 19, has ? p.ink : '#666'), overflow: 'hidden'}}>{has ? st.typed : txt(d.placeholder) || 'Try "build a landing page"'}</span>
          <Caret st={st} size={19} color={p.ink} />
        </div>
        <div style={{position: 'absolute', left: 50, top: 566, ...mono(400, 14, '#6B6964')}}>? for shortcuts</div>
        {t >= 0 ? <div style={{position: 'absolute', right: 50, top: 566, display: 'flex', alignItems: 'center', gap: 6}}><ClaudeMark size={16} /><span style={mono(400, 14, '#6B6964')}>{txt(d.model) || 'claude'}</span></div> : null}
      </>
    );
  },
};

// ------------------------------------------------------------------ editor koda (Cursor / VS Code)
const KW = /\b(const|let|var|function|return|import|from|export|default|if|else|await|async|def|class|for|while|new|true|false|null)\b/;
const tokens = (s: string) => {
  const out: {t: string; c: string}[] = [];
  const re = /(\/\/.*$|#.*$|"[^"]*"|'[^']*'|`[^`]*`|\b\d+(?:\.\d+)?\b|\b[A-Za-z_]\w*\b|\s+|.)/g;
  let m: RegExpExecArray | null;
  while ((m = re.exec(s))) {
    const x = m[0];
    const c = /^(\/\/|#)/.test(x) ? '#6A9955' : /^["'`]/.test(x) ? '#CE9178' : /^\d/.test(x) ? '#B5CEA8' : KW.test(x) && x.match(KW)?.[0] === x ? '#C586C0'
      : /^[A-Z]/.test(x) ? '#4EC9B0' : /^\w+$/.test(x) && s[m.index + x.length] === '(' ? '#DCDCAA' : '#D4D4D4';
    out.push({t: x, c});
  }
  return out;
};
const ED_X = 214, ED_Y = 92, ED_ROW = 32;
const codeSkin = (kind: 'cursor' | 'vscode'): Skin => ({
  menuFrom: 'chat',
  pal: {light: pal('#1E1E1E', '#D4D4D4', '#858585', '#2B2B2B', '#252526', '#252526'), dark: pal('#1E1E1E', '#D4D4D4', '#858585', '#2B2B2B', '#252526', '#252526')},
  base: (st) => (st.d.input ? {x: 540, y: 290, s: 1.22} : {x: 500, y: 290, s: 1.32}),
  anchors: (st) => {
    const code: any[] = st.d.code ?? [];
    const add: any[] = st.d.add ?? [];
    const chatW = st.d.input ? 264 : 0;
    const a: Record<string, Rect> = {window: {x: 0, y: 0, w: W, h: H}, tree: {x: 48, y: 44, w: 164, h: H - 44},
      editor: {x: ED_X, y: 44, w: W - ED_X - chatW, h: H - 44}, chat: {x: W - chatW, y: 44, w: chatW, h: H - 44},
      input: {x: W - chatW + 14, y: 470, w: chatW - 28, h: 90}, send: {x: W - 54, y: 520, w: 34, h: 34}};
    [...code, ...add].forEach((_, i) => { a[`line${i}`] = {x: ED_X, y: ED_Y + i * ED_ROW, w: W - ED_X - chatW, h: ED_ROW}; });
    if (add.length) a.diff = {x: ED_X, y: ED_Y + code.length * ED_ROW, w: W - ED_X - chatW, h: add.length * ED_ROW};
    return a;
  },
  Body: ({st, a}) => {
    const p = st.pal, d = st.d, t = st.t;
    const files: string[] = (d.files ?? ['app.tsx', 'api.ts', 'utils.ts', 'package.json']).map(txt);
    const active = txt(d.file) || files[0];
    const code: string[] = (d.code ?? []).map(txt);
    const add: any[] = d.add ?? [];
    const chatW = d.input ? 264 : 0;
    const acc = kind === 'cursor' ? '#FFFFFF' : '#0078D4';
    return (
      <>
        <div style={{position: 'absolute', left: 0, top: 44, width: 48, height: H - 44, background: kind === 'cursor' ? '#181818' : '#333333'}}>
          {[Ph.Files, Ph.MagnifyingGlass, Ph.GitBranch, Ph.Bug, Ph.PuzzlePiece].map((I, i) => (
            <div key={i} style={{position: 'absolute', left: 11, top: 14 + i * 48}}><I size={26} color={i === 0 ? '#E0E0E0' : '#858585'} /></div>))}
        </div>
        <div style={abs(a.tree, {background: kind === 'cursor' ? '#181818' : '#252526', borderRight: `1px solid ${p.line}`})}>
          <div style={{position: 'absolute', left: 16, top: 12, ...ui(700, 13, p.mut), letterSpacing: '0.08em'}}>{(txt(d.project) || 'MY-APP').toUpperCase()}</div>
          {files.slice(0, 8).map((f, i) => (
            <div key={f} style={{position: 'absolute', left: 6, right: 6, top: 40 + i * 30, height: 28, borderRadius: 4, background: f === active ? '#37373D' : undefined,
              display: 'flex', alignItems: 'center', gap: 8, paddingLeft: 14, ...ui(500, 16, f === active ? '#FFFFFF' : '#CCCCCC')}}>
              <Ph.FileCode size={16} color={/\.json$/.test(f) ? '#CBCB41' : /\.py$/.test(f) ? '#3776AB' : '#519ABA'} />{f}</div>
          ))}
        </div>
        <div style={{position: 'absolute', left: ED_X, top: 44, width: W - ED_X - chatW, height: 40, background: '#252526', borderBottom: `1px solid ${p.line}`}}>
          <div style={{height: 40, width: 170, background: '#1E1E1E', borderTop: `2px solid ${acc}`, display: 'flex', alignItems: 'center', gap: 8, paddingLeft: 14, ...ui(500, 16, '#FFFFFF')}}>
            <Ph.FileCode size={16} color="#519ABA" />{active}</div>
        </div>
        {[...code.map((c) => ({text: c, add: false})), ...add.map((x) => ({...x, text: txt(x), add: true}))].map((ln: any, i) => {
          if (ln.add && !shown(ln, t)) return null;
          const s0 = String(ln.text);
          const full = ln.add && typeof ln.atT === 'number' ? s0.slice(0, Math.round(Math.min(1, (t - ln.atT) / Math.max(0.3, s0.length * 0.03)) * s0.length)) : s0;
          const typing = ln.add && full.length < s0.length;
          return (
            <div key={i} style={{position: 'absolute', left: ED_X, top: ED_Y + i * ED_ROW, width: W - ED_X - chatW, height: ED_ROW, display: 'flex', alignItems: 'center',
              background: ln.add ? 'rgba(46,160,67,0.22)' : undefined, borderLeft: ln.add ? '3px solid #2EA043' : '3px solid transparent'}}>
              <span style={{width: 44, textAlign: 'right', paddingRight: 14, ...mono(400, 16, '#6E7681')}}>{i + 1}</span>
              <span style={{overflow: 'hidden'}}>{tokens(full).map((tk, j) => <span key={j} style={mono(400, 16, tk.c)}>{tk.t}</span>)}
                {typing ? <span style={{display: 'inline-block', width: 2, height: 18, background: '#FFF', verticalAlign: 'middle'}} /> : null}</span>
            </div>
          );
        })}
        {chatW ? (
          <div style={abs(a.chat, {background: '#181818', borderLeft: `1px solid ${p.line}`})}>
            <div style={{position: 'absolute', left: 14, top: 12, display: 'flex', alignItems: 'center', gap: 8, ...ui(700, 16, '#E0E0E0')}}>
              {kind === 'cursor' ? <><Ph.Cube size={18} weight="fill" color="#E0E0E0" />Agent</> : <><Ph.Sparkle size={18} weight="fill" color="#E0E0E0" />Copilot Chat</>}</div>
            {st.sendP > 0 ? (
              <>
                <div style={{position: 'absolute', left: 14, right: 14, top: 52, padding: '10px 12px', borderRadius: 10, background: '#2A2A2A', opacity: st.sendP, ...ui(500, 16, '#E0E0E0', 1.35)}}>{st.sent}</div>
                <div style={{position: 'absolute', left: 14, right: 14, top: 140, opacity: ease(t, T(d.send, 0) + 0.4, 0.4), ...ui(400, 16, '#CCCCCC', 1.45)}}>
                  {txt(d.reply) || 'Editing app.tsx…'}
                  {add.length ? <div style={{marginTop: 10, padding: '6px 10px', borderRadius: 8, background: 'rgba(46,160,67,0.18)', display: 'inline-flex', gap: 8, ...ui(600, 15, '#3FB950')}}>
                    +{add.filter((x) => shown(x, t)).length} lines</div> : null}
                </div>
              </>
            ) : null}
            <div style={abs({x: 14, y: a.input.y - 44, w: chatW - 28, h: 90}, {borderRadius: 10, border: '1.5px solid #3C3C3C', background: '#222', padding: '10px 12px'})}>
              <span style={ui(st.typed ? 500 : 400, 16, st.typed ? '#E0E0E0' : '#777')}>{st.typed || (kind === 'cursor' ? 'Plan, search, build anything' : 'Ask Copilot')}</span>
              <Caret st={st} size={16} color="#E0E0E0" />
            </div>
          </div>
        ) : null}
      </>
    );
  },
});

// ------------------------------------------------------------------ Canva
const CV_ART: Rect = {x: 330, y: 120, w: 300, h: 375};
const canva: Skin = {
  menuFrom: 'toolbar',
  chrome: false,
  pal: {light: pal('#EBECF0', '#0E1318', '#5E6D7A', '#D6D9DE', '#FFFFFF', '#FFFFFF'), dark: pal('#EBECF0', '#0E1318', '#5E6D7A', '#D6D9DE', '#FFFFFF', '#FFFFFF')},
  base: (st) => (st.d.variants ? {x: 480, y: 310, s: 1.15} : {x: 480, y: 308, s: 1.38}),
  anchors: (st) => {
    const a: Record<string, Rect> = {window: {x: 0, y: 0, w: W, h: H}, toolbar: {x: 0, y: 56, w: 84, h: H - 56}, canvas: CV_ART, share: {x: 780, y: 10, w: 100, h: 38},
      magic: {x: 96, y: 70, w: 200, h: 48}, variants: {x: 110, y: 110, w: 740, h: 400}};
    return a;
  },
  Body: ({st, a}) => {
    const d = st.d, t = st.t;
    const els: any[] = d.elements ?? [];
    const v = d.variants;
    const vT = v ? T(v, 1e9) : 1e9;
    const vk = ease(t, vT, 0.6);
    const n = Math.min(3, Number(v?.n ?? 3));
    const bg = txt(d.background) || `linear-gradient(160deg, ${rgba(st.acc, 0.9)} 0%, #1B1F3B 100%)`;
    const Art: React.FC<{r: Rect; i: number}> = ({r, i}) => (
      <div style={{...abs(r), background: i === 0 ? bg : ['linear-gradient(160deg,#FFD166,#EF476F)', 'linear-gradient(160deg,#06D6A0,#118AB2)', 'linear-gradient(160deg,#F7F7F7,#D9D9D9)'][i % 3],
        boxShadow: '0 8px 24px rgba(0,0,0,0.18)', overflow: 'hidden'}}>
        {els.map((e, j) => {
          if (!shown(e, t) && i === 0) return null;
          const k = i === 0 ? kIn(e, t, 0.45) : 1;
          const sc = r.w / CV_ART.w;
          if (e?.type === 'image' || file(e)) {
            const src = file(e);
            return <div key={j} style={{position: 'absolute', left: 30 * sc, top: 120 * sc, width: 240 * sc, height: 170 * sc, borderRadius: 10 * sc, overflow: 'hidden',
              background: '#ccc', opacity: k, transform: `scale(${0.8 + 0.2 * k})`}}>{src ? <Img src={staticFile(src)} style={{width: '100%', height: '100%', objectFit: 'cover'}} /> : null}</div>;
          }
          const big = j === 0;
          return <div key={j} style={{position: 'absolute', left: 24 * sc, right: 24 * sc, top: (big ? 36 : 304) * sc, textAlign: 'center', opacity: k, transform: `translateY(${(1 - k) * 12}px)`,
            ...ui(big ? 800 : 600, (big ? 34 : 18) * sc, i === 2 ? '#111' : '#FFFFFF', 1.1)}}>{txt(e)}</div>;
        })}
      </div>
    );
    return (
      <>
        <div style={{position: 'absolute', left: 0, top: 0, width: W, height: 56, background: 'linear-gradient(90deg,#00C4CC,#7D2AE8)'}}>
          <div style={{position: 'absolute', left: 18, top: 16, display: 'flex', gap: 8}}>
            {['#FF5F57', '#FEBC2E', '#28C840'].map((c) => <div key={c} style={{width: 13, height: 13, borderRadius: 7, background: c}} />)}</div>
          <span style={{position: 'absolute', left: 90, top: 10, fontFamily: 'Georgia, serif', fontStyle: 'italic', fontWeight: 700, fontSize: 30, color: '#fff'}}>Canva</span>
          <span style={{position: 'absolute', left: 230, top: 18, ...ui(500, 17, 'rgba(255,255,255,0.9)')}}>{txt(d.title) || 'Instagram Post'}</span>
          <div style={{...abs(a.share), borderRadius: 8, background: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6, ...ui(700, 16, '#7D2AE8')}}>
            <Ph.UploadSimple size={16} weight="bold" />Share</div>
        </div>
        <div style={abs(a.toolbar, {background: '#FFFFFF', borderRight: '1px solid #E4E5E8'})}>
          {[[Ph.Layout, 'Design'], [Ph.Shapes, 'Elements'], [Ph.TextT, 'Text'], [Ph.CloudArrowUp, 'Uploads'], [Ph.Sparkle, 'Magic']].map(([I, s]: any, i) => (
            <div key={s} style={{position: 'absolute', left: 0, width: 84, top: 14 + i * 74, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4}}>
              <I size={26} color={i === 4 && v && t >= vT - 0.6 ? '#7D2AE8' : '#3D4752'} weight={i === 4 && v && t >= vT - 0.6 ? 'fill' : 'regular'} />
              <span style={ui(500, 13, '#3D4752')}>{s}</span></div>
          ))}
        </div>
        {v && t >= vT - 0.6 && vk < 1 ? (
          <div style={{...abs(a.magic), borderRadius: 24, background: 'linear-gradient(90deg,#7D2AE8,#C13584)', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
            opacity: 1 - vk, ...ui(700, 17, '#fff')}}><Ph.Sparkle size={18} weight="fill" />{txt(v?.label) || 'Magic Design'}</div>
        ) : null}
        {vk <= 0 ? <Art r={CV_ART} i={0} /> : (
          Array.from({length: n}).map((_, i) => {
            const target = {x: 120 + i * 250, y: 140, w: 220, h: 275};
            const from = i === 0 ? CV_ART : {...CV_ART, w: CV_ART.w * 0.6, h: CV_ART.h * 0.6, x: CV_ART.x + 60, y: CV_ART.y + 75};
            const k = ease(t, vT + i * 0.15, 0.6, POP);
            const r = {x: from.x + (target.x - from.x) * k, y: from.y + (target.y - from.y) * k, w: from.w + (target.w - from.w) * k, h: from.h + (target.h - from.h) * k};
            return <div key={i} style={{opacity: Math.min(1, k * 1.5)}}><Art r={r} i={i} /></div>;
          })
        )}
      </>
    );
  },
};

// ------------------------------------------------------------------ CapCut
const CC_PREV: Rect = {x: 340, y: 60, w: 220, h: 300};
const CC_TL = 392;
const capcut: Skin = {
  menuFrom: 'captions',
  chrome: false,
  pal: {light: pal('#18181B', '#F4F4F5', '#A1A1AA', '#2A2A2E', '#232327'), dark: pal('#18181B', '#F4F4F5', '#A1A1AA', '#2A2A2E', '#232327')},
  base: () => ({x: W / 2, y: 300, s: 1.18}),
  anchors: () => ({window: {x: 0, y: 0, w: W, h: H}, preview: CC_PREV, timeline: {x: 0, y: CC_TL, w: W, h: H - CC_TL},
    captions: {x: 24, y: 120, w: 170, h: 44}, track0: {x: 90, y: CC_TL + 40, w: 780, h: 46}, track1: {x: 90, y: CC_TL + 94, w: 780, h: 34}, track2: {x: 90, y: CC_TL + 136, w: 780, h: 34}}),
  Body: ({st, a}) => {
    const d = st.d, t = st.t, p = st.pal;
    const cuts: any[] = d.cuts ?? [];
    const cap = d.captions;
    const capT = cap ? T(cap, 1e9) : 1e9;
    const words: string[] = String(txt(cap?.text) || txt(d.caption) || 'This changed everything').split(/\s+/);
    const capK = Math.max(0, Math.min(1, (t - capT - 0.4) / 1.4));
    const head = 90 + 780 * Math.min(1, t / Math.max(1, Number(d.length ?? 6)));
    const src = file(d.media ?? (d.file ? d : null));
    const cutXs = cuts.map((c, i) => ({x: 90 + 780 * ((i + 1) / (cuts.length + 1)), T: T(c, 1e9)}));
    const wordAt = Math.floor(((t - capT) % 2.4) / 0.6);
    return (
      <>
        <div style={{position: 'absolute', left: 0, top: 0, width: W, height: 44, background: '#0F0F11', borderBottom: `1px solid ${p.line}`}}>
          <div style={{position: 'absolute', left: 18, top: 15, display: 'flex', gap: 8}}>
            {['#FF5F57', '#FEBC2E', '#28C840'].map((c) => <div key={c} style={{width: 13, height: 13, borderRadius: 7, background: c}} />)}</div>
          <span style={{position: 'absolute', left: 96, top: 11, ...ui(800, 18, '#fff')}}>CapCut</span>
          <div style={{position: 'absolute', right: 18, top: 7, padding: '6px 18px', borderRadius: 8, background: '#00C1CD', ...ui(700, 16, '#000')}}>Export</div>
        </div>
        <div style={{position: 'absolute', left: 14, top: 58, width: 196, ...ui(700, 15, p.mut)}}>Text</div>
        {['Auto captions', 'Text template', 'Effects'].map((s, i) => {
          const on = i === 0 && cap && t >= capT - 0.1;
          return <div key={s} style={{position: 'absolute', left: 24, top: 120 + i * 54, width: 170, height: 44, borderRadius: 10, background: on ? rgba('#00C1CD', 0.22) : p.bubble,
            border: on ? '2px solid #00C1CD' : '2px solid transparent', display: 'flex', alignItems: 'center', gap: 8, paddingLeft: 12, ...ui(600, 16, on ? '#00E0EE' : p.ink)}}>
            {i === 0 ? <Ph.Subtitles size={18} /> : i === 1 ? <Ph.TextAa size={18} /> : <Ph.MagicWand size={18} />}{s}</div>;
        })}
        <div style={abs(CC_PREV, {borderRadius: 12, overflow: 'hidden', background: src ? '#000' : `linear-gradient(170deg, ${rgba(st.acc, 0.7)}, #111)`})}>
          {src ? (d.mkind === 'video' || (d.media && d.media.mkind === 'video') ? <OffthreadVideo src={staticFile(src)} muted style={{width: '100%', height: '100%', objectFit: 'cover'}} />
            : <Img src={staticFile(src)} style={{width: '100%', height: '100%', objectFit: 'cover'}} />) : <Ph.User size={110} weight="fill" color="rgba(255,255,255,0.35)" style={{position: 'absolute', left: 55, top: 110}} />}
          {cap && capK > 0 ? (
            <div style={{position: 'absolute', left: 10, right: 10, top: 196, textAlign: 'center', ...ui(900, 22, '#fff', 1.15), textShadow: '0 2px 6px rgba(0,0,0,0.7)'}}>
              {words.slice(0, 4).map((w, i) => <span key={i} style={{color: i === wordAt ? st.acc : '#fff'}}>{w} </span>)}</div>
          ) : null}
        </div>
        <div style={abs(a.timeline, {background: '#111113', borderTop: `1px solid ${p.line}`})} />
        <div style={{position: 'absolute', left: 90, top: CC_TL + 10, width: 780, display: 'flex', justifyContent: 'space-between', ...mono(400, 12, '#71717A')}}>
          {['00:00', '00:02', '00:04', '00:06', '00:08'].map((s) => <span key={s}>{s}</span>)}</div>
        {[Ph.FilmStrip, Ph.Subtitles, Ph.MusicNotes].map((I, i) => <div key={i} style={{position: 'absolute', left: 36, top: [CC_TL + 50, CC_TL + 98, CC_TL + 140][i]}}><I size={22} color="#71717A" /></div>)}
        <div style={abs(a.track0, {borderRadius: 6, background: 'linear-gradient(180deg,#3B5BDB,#2B44A8)', overflow: 'hidden'})}>
          {Array.from({length: 12}).map((_, i) => <div key={i} style={{position: 'absolute', left: i * 65, top: 4, width: 60, height: 38, borderRadius: 3, background: 'rgba(255,255,255,0.12)'}} />)}
          {cutXs.map((c, i) => t >= c.T ? <div key={i} style={{position: 'absolute', left: c.x - 90 - 2, top: 0, width: 4, height: 46, background: '#18181B'}} /> : null)}
        </div>
        {cap ? Array.from({length: 7}).map((_, i) => {
          const k = Math.max(0, Math.min(1, capK * 7 - i));
          return <div key={i} style={{position: 'absolute', left: 90 + i * 112, top: CC_TL + 94, width: 104 * k, height: 34, borderRadius: 6, background: '#E8590C', opacity: k > 0 ? 1 : 0,
            overflow: 'hidden', ...ui(600, 13, '#fff'), display: 'flex', alignItems: 'center', paddingLeft: k > 0.6 ? 8 : 0, whiteSpace: 'nowrap'}}>{k > 0.6 ? words[i % words.length] : ''}</div>;
        }) : null}
        <div style={abs(a.track2, {borderRadius: 6, background: '#1F3A2E', overflow: 'hidden'})}>
          {Array.from({length: 90}).map((_, i) => <div key={i} style={{position: 'absolute', left: 4 + i * 8.6, top: 17 - 12 * Math.abs(Math.sin(i * 0.7) * Math.sin(i * 0.23)), width: 4,
            height: 24 * Math.abs(Math.sin(i * 0.7) * Math.sin(i * 0.23)) + 2, borderRadius: 2, background: '#37B24D'}} />)}
        </div>
        <div style={{position: 'absolute', left: head, top: CC_TL + 26, width: 2, height: H - CC_TL - 30, background: '#fff', zIndex: 5}}>
          <div style={{position: 'absolute', left: -7, top: -8, width: 16, height: 12, borderRadius: 3, background: '#fff'}} /></div>
      </>
    );
  },
};

// ------------------------------------------------------------------ Meta Ads Manager
const AD_TOP = 260, AD_ROW = 56;
const ads: Skin = {
  menuFrom: 'table',
  pal: {light: pal('#F0F2F5', '#1C2B33', '#65676B', '#DADDE1', '#FFFFFF', '#FFFFFF'), dark: pal('#F0F2F5', '#1C2B33', '#65676B', '#DADDE1', '#FFFFFF', '#FFFFFF')},
  base: () => ({x: 484, y: 300, s: 1.28}),
  anchors: (st) => {
    const a: Record<string, Rect> = {window: {x: 0, y: 0, w: W, h: H}, metrics: {x: 90, y: 80, w: 780, h: 110}, table: {x: 90, y: AD_TOP - 46, w: 790, h: 46 + 5 * AD_ROW}};
    ['spent', 'results', 'roas'].forEach((k, i) => { a[k] = {x: 90 + i * 262, y: 80, w: 250, h: 110}; });
    (st.d.campaigns ?? []).forEach((_: any, i: number) => { a[`row${i}`] = {x: 90, y: AD_TOP + i * AD_ROW, w: 790, h: AD_ROW}; });
    return a;
  },
  Body: ({st, a}) => {
    const p = st.pal, d = st.d, t = st.t;
    const camps: any[] = (d.campaigns ?? []).slice(0, 5);
    const mets: any[] = d.metrics ?? [{label: 'Amount spent', value: '$1,240.00'}, {label: 'Results', value: '312'}, {label: 'ROAS', value: '4.8'}];
    return (
      <>
        <div style={{position: 'absolute', left: 0, top: 44, width: 70, height: H - 44, background: '#FFFFFF', borderRight: `1px solid ${p.line}`}}>
          <div style={{position: 'absolute', left: 17, top: 14}}><Ph.MetaLogo size={36} weight="bold" color="#0866FF" /></div>
          {[Ph.House, Ph.ChartBar, Ph.Megaphone, Ph.Users].map((I, i) => <div key={i} style={{position: 'absolute', left: 22, top: 70 + i * 52}}><I size={26} color={i === 2 ? '#0866FF' : p.mut} /></div>)}
        </div>
        <div style={{position: 'absolute', left: 90, top: 52, ...ui(700, 20, p.ink)}}>{txt(d.title) || 'Campaigns'}</div>
        {mets.slice(0, 3).map((m, i) => {
          const r = a[['spent', 'results', 'roas'][i]];
          const v = countAt(m?.start != null ? m : {start: 0, to: m?.value, atT: typeof m?.atT === 'number' ? m.atT : 0.2}, t);
          return (
            <div key={i} style={{...abs(r), top: r.y + 12, height: r.h - 20, borderRadius: 10, background: '#FFFFFF', border: `1px solid ${p.line}`, padding: '12px 16px'}}>
              <div style={ui(500, 15, p.mut)}>{txt(m?.label)}</div>
              <div style={{...ui(700, 32, m?.tone === 'bad' ? RED : p.ink, 1.2), marginTop: 4}}>{isFinite(v) ? fmtNum(v, m?.value) : txt(m?.value)}</div>
            </div>
          );
        })}
        <div style={{position: 'absolute', left: 90, top: AD_TOP - 46, width: 790, height: 46, background: '#FFFFFF', borderRadius: '10px 10px 0 0', borderBottom: `1px solid ${p.line}`,
          display: 'flex', alignItems: 'center', ...ui(700, 14, p.mut)}}>
          <span style={{width: 70, paddingLeft: 16}}>Off/On</span><span style={{flex: 1}}>Campaign</span><span style={{width: 110, textAlign: 'right'}}>Results</span>
          <span style={{width: 120, textAlign: 'right'}}>Cost/result</span><span style={{width: 100, textAlign: 'right', paddingRight: 16}}>ROAS</span></div>
        {camps.map((c, i) => {
          const k = kIn(c, t, 0.4);
          const offT = c?.off ? T(c.off, 1e9) : 1e9, onT = c?.on ? T(c.on, 1e9) : 1e9;
          const on = c?.off ? t < offT : c?.on ? t >= onT : c?.active !== false;
          const sw = c?.off ? 1 - ease(t, offT, 0.25) : c?.on ? ease(t, onT, 0.25) : on ? 1 : 0;
          const tone = c?.tone;
          return (
            <div key={i} style={{position: 'absolute', left: 90, top: AD_TOP + i * AD_ROW, width: 790, height: AD_ROW, background: tone === 'good' ? rgba(st.acc, 0.14) : '#FFFFFF',
              borderBottom: `1px solid ${p.line}`, display: 'flex', alignItems: 'center', opacity: k * (on ? 1 : 0.6), boxShadow: tone === 'good' ? `inset 4px 0 0 ${st.acc}` : tone === 'bad' ? `inset 4px 0 0 ${RED}` : undefined}}>
              <div style={{width: 70, paddingLeft: 16}}>
                <div style={{width: 40, height: 22, borderRadius: 11, background: sw > 0.5 ? '#0866FF' : '#BCC0C4', position: 'relative'}}>
                  <div style={{position: 'absolute', top: 3, left: 3 + 18 * sw, width: 16, height: 16, borderRadius: 8, background: '#fff'}} /></div></div>
              <span style={{flex: 1, ...ui(600, 17, '#0866FF'), whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'}}>{txt(c?.name)}</span>
              <span style={{width: 110, textAlign: 'right', ...ui(600, 17, p.ink)}}>{txt(c?.results)}</span>
              <span style={{width: 120, textAlign: 'right', ...ui(500, 17, tone === 'bad' ? RED : p.ink)}}>{txt(c?.cost)}</span>
              <span style={{width: 100, textAlign: 'right', paddingRight: 16, ...ui(700, 17, tone === 'bad' ? RED : tone === 'good' ? '#00A86B' : p.ink)}}>{txt(c?.roas)}</span>
            </div>
          );
        })}
      </>
    );
  },
};

// ------------------------------------------------------------------ YouTube Studio
const ytstudio: Skin = {
  menuFrom: 'metrics',
  pal: {light: pal('#F9F9F9', '#0F0F0F', '#606060', '#E5E5E5', '#FFFFFF', '#FFFFFF'), dark: pal('#1F1F1F', '#F1F1F1', '#AAAAAA', '#3F3F3F', '#282828', '#282828')},
  base: () => ({x: 500, y: 290, s: 1.3}),
  anchors: (st) => {
    const a: Record<string, Rect> = {window: {x: 0, y: 0, w: W, h: H}, metrics: {x: 220, y: 112, w: 650, h: 96}, chart: {x: 220, y: 216, w: 650, h: 170},
      list: {x: 220, y: 400, w: 650, h: 180}};
    for (let i = 0; i < 3; i++) a[`m${i}`] = {x: 220 + i * 216, y: 112, w: 216, h: 96};
    for (let i = 0; i < 3; i++) a[`row${i}`] = {x: 220, y: 430 + i * 50, w: 650, h: 50};
    return a;
  },
  Body: ({st, a}) => {
    const p = st.pal, d = st.d, t = st.t;
    const mets: any[] = d.metrics ?? [{label: 'Views', value: '1.2M'}, {label: 'Watch time (hours)', value: '48.3K'}, {label: 'Subscribers', value: '+12.4K'}];
    const sel = Math.max(0, mets.findIndex((m) => m?.selected));
    const vals: number[] = (d.chart?.values ?? [1, 1.2, 1.1, 1.6, 2, 1.8, 2.9, 4.2, 6, 9]).map(Number);
    const ck = ease(t, T(d.chart, 0.3), 1.6);
    const r = a.chart;
    const mx = Math.max(...vals);
    const pts = vals.map((v, i) => ({x: 10 + (i / (vals.length - 1)) * (r.w - 20), y: r.h - 16 - (v / (mx || 1)) * (r.h - 34)}));
    const n = Math.max(1, ck * (pts.length - 1));
    const cut = pts.slice(0, Math.floor(n) + 1);
    if (Math.floor(n) < pts.length - 1) { const p0 = pts[Math.floor(n)], p1 = pts[Math.floor(n) + 1], f = n - Math.floor(n); cut.push({x: p0.x + (p1.x - p0.x) * f, y: p0.y + (p1.y - p0.y) * f}); }
    const line = cut.map((q, i) => `${i ? 'L' : 'M'}${q.x},${q.y}`).join(' ');
    const vids = arrivals(d.videos ?? [], t).slice(0, 3);
    return (
      <>
        <div style={{position: 'absolute', left: 0, top: 44, width: W, height: 56, borderBottom: `1px solid ${p.line}`, display: 'flex', alignItems: 'center', gap: 10, paddingLeft: 22}}>
          <Ph.YoutubeLogo size={34} weight="fill" color="#FF0000" /><span style={ui(700, 21, p.ink)}>Studio</span></div>
        <div style={{position: 'absolute', left: 0, top: 100, width: 200, height: H - 100, borderRight: `1px solid ${p.line}`}}>
          {[[Ph.SquaresFour, 'Dashboard'], [Ph.Play, 'Content'], [Ph.ChartBar, 'Analytics'], [Ph.ChatText, 'Comments'], [Ph.CurrencyDollar, 'Earn']].map(([I, s]: any, i) => (
            <div key={s} style={{position: 'absolute', left: 8, right: 8, top: 12 + i * 44, height: 40, borderRadius: 8, background: i === 2 ? p.bubble === '#FFFFFF' ? '#F2F2F2' : p.bubble : undefined,
              display: 'flex', alignItems: 'center', gap: 12, paddingLeft: 14, ...ui(i === 2 ? 700 : 500, 17, i === 2 ? '#FF0000' : p.ink)}}><I size={20} />{s}</div>))}
        </div>
        {mets.slice(0, 3).map((m, i) => {
          const rr = a[`m${i}`];
          const v = countAt(m?.start != null ? m : {start: 0, to: m?.value, atT: typeof m?.atT === 'number' ? m.atT : 0.2}, t);
          const delta = m?.delta ? (typeof m.delta === 'object' ? m.delta : {text: m.delta}) : null;
          const dk = delta ? ease(t, T(delta, (typeof m?.atT === 'number' ? m.atT : 0.2) + 1.1), 0.4, POP) : 0;
          const raw = String(txt(m?.value));
          return (
            <div key={i} style={{...abs(rr), padding: '10px 14px', borderBottom: i === sel ? '3px solid #065FD4' : `1px solid ${p.line}`, background: i === sel ? p.card : undefined}}>
              <div style={ui(500, 15, p.mut)}>{txt(m?.label)}</div>
              <div style={{display: 'flex', alignItems: 'center', gap: 8}}>
                <span style={ui(700, 30, p.ink, 1.3)}>{isFinite(v) ? (raw.startsWith('+') ? '+' : '') + fmtNum(v, raw.replace(/^\+/, '')) : raw}</span>
                {delta && dk > 0 ? <span style={{transform: `scale(${dk})`, display: 'inline-flex', alignItems: 'center', ...ui(700, 15, '#00A86B')}}><Ph.ArrowUp size={14} weight="bold" />{txt(delta)}</span> : null}
              </div>
            </div>
          );
        })}
        <div style={abs(r)}>
          <svg width={r.w} height={r.h} style={{overflow: 'visible'}}>
            <path d={`${line} L${cut[cut.length - 1].x},${r.h - 16} L${cut[0].x},${r.h - 16} Z`} fill="rgba(6,95,212,0.1)" />
            <path d={line} fill="none" stroke="#065FD4" strokeWidth={4} strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
        <div style={{position: 'absolute', left: 220, top: 398, ...ui(700, 18, p.ink)}}>{txt(d.title) || 'Top content'}</div>
        {vids.map((x, idx) => {
          const v0 = x.r ?? {};
          const y = 430 + slotY(vids, idx, 50);
          return (
            <div key={x.i} style={{position: 'absolute', left: 220, top: y, width: 650, height: 50, display: 'flex', alignItems: 'center', gap: 14, opacity: x.k, borderBottom: `1px solid ${p.line}`}}>
              <div style={{width: 64, height: 36, borderRadius: 6, overflow: 'hidden', background: ['#F59F00', '#7048E8', '#12B886'][x.i % 3]}}>
                {file(v0.thumb) ? <Img src={staticFile(file(v0.thumb)!)} style={{width: '100%', height: '100%', objectFit: 'cover'}} /> : null}</div>
              <span style={{flex: 1, ...ui(600, 17, p.ink), whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'}}>{txt(v0.title)}</span>
              <span style={{...ui(700, 17, p.ink), marginRight: 10}}>{txt(v0.views)}</span>
            </div>
          );
        })}
      </>
    );
  },
};

// ------------------------------------------------------------------ TikTok (telefon)
const tiktok: Skin = {
  menuFrom: 'caption',
  frame: 'phone',
  size: {w: PW, h: PH},
  maxZoom: 2.4,
  pal: {light: pal('#000000', '#FFFFFF', 'rgba(255,255,255,0.75)', '#2A2A2A', '#1A1A1A'), dark: pal('#000000', '#FFFFFF', 'rgba(255,255,255,0.75)', '#2A2A2A', '#1A1A1A')},
  base: () => ({x: PW / 2, y: 640, s: 1.9}),
  anchors: () => ({video: {x: 0, y: 0, w: PW, h: PH}, likes: {x: 360, y: 470, w: 62, h: 80}, comments: {x: 360, y: 560, w: 62, h: 80},
    share: {x: 360, y: 740, w: 62, h: 80}, caption: {x: 14, y: 750, w: 330, h: 110}, drawer: {x: 0, y: 560, w: PW, h: PH - 560}, rail: {x: 350, y: 380, w: 80, h: 470}}),
  Body: ({st}) => {
    const d = st.d, t = st.t;
    const src = file(d.media ?? (d.file ? d : null));
    const likeT = d.like ? T(d.like, 1e9) : 1e9;
    const liked = t >= likeT;
    const lk = ease(t, likeT, 0.45, POP);
    const likes = d.likes != null ? countAt(d.likes, t) : NaN;
    const comN = d.commentCount != null ? countAt(d.commentCount, t) : NaN;
    const coms: any[] = d.comments ?? [];
    const drT = coms.length ? Math.min(...coms.map((c) => T(c, 0.5))) - 0.3 : 1e9;
    const dk = ease(t, drT, 0.45);
    const comVis = arrivals(coms, t).slice(0, 4);
    const isVid = d.mkind === 'video' || d.media?.mkind === 'video';
    return (
      <>
        <div style={{position: 'absolute', inset: 0, background: src ? '#000' : `linear-gradient(170deg, ${rgba(st.acc, 0.55)} 0%, #121212 60%)`}}>
          {src ? (isVid ? <OffthreadVideo src={staticFile(src)} muted style={{width: '100%', height: '100%', objectFit: 'cover'}} />
            : <Img src={staticFile(src)} style={{width: '100%', height: '100%', objectFit: 'cover'}} />) : null}
          <div style={{position: 'absolute', inset: 0, background: 'linear-gradient(180deg, rgba(0,0,0,0.25) 0%, transparent 25%, transparent 60%, rgba(0,0,0,0.55) 100%)'}} />
        </div>
        <div style={{position: 'absolute', left: 0, top: 62, width: PW, display: 'flex', justifyContent: 'center', gap: 26, ...ui(700, 18, 'rgba(255,255,255,0.7)')}}>
          <span>Following</span><span style={{color: '#fff', borderBottom: '3px solid #fff', paddingBottom: 4}}>For You</span></div>
        <div style={{position: 'absolute', left: 362, top: 386, width: 58, height: 58, borderRadius: 29, border: '2px solid #fff', overflow: 'hidden',
          background: 'linear-gradient(135deg,#25F4EE,#FE2C55)', display: 'grid', placeItems: 'center', ...ui(800, 24, '#fff')}}>
          {file(d.avatar) ? <Img src={staticFile(file(d.avatar)!)} style={{width: '100%', height: '100%', objectFit: 'cover'}} /> : (txt(d.handle) || 'y').replace('@', '').slice(0, 1).toUpperCase()}</div>
        <div style={{position: 'absolute', left: 380, top: 432, width: 22, height: 22, borderRadius: 11, background: '#FE2C55', display: 'grid', placeItems: 'center'}}><Ph.Plus size={14} weight="bold" color="#fff" /></div>
        {([['likes', Ph.Heart, isFinite(likes) ? fmtIG(likes) : txt(d.likes) || '24.1K'], ['comments', Ph.ChatCircleDots, isFinite(comN) ? fmtIG(comN) : txt(d.commentCount) || '1,204'],
          ['save', Ph.BookmarkSimple, txt(d.saves) || '3,991'], ['share', Ph.ShareFat, txt(d.shares) || '812']] as any[]).map(([k, I, label], i) => (
          <div key={k} style={{position: 'absolute', left: 360, top: 476 + i * 90, width: 62, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2}}>
            <div style={{transform: k === 'likes' && liked ? `scale(${0.7 + 0.5 * lk - 0.2 * Math.max(0, lk - 1)})` : undefined}}>
              <I size={42} weight="fill" color={k === 'likes' && liked ? '#FE2C55' : '#fff'} style={{filter: 'drop-shadow(0 2px 4px rgba(0,0,0,0.4))'}} /></div>
            <span style={{...ui(700, 15, '#fff'), textShadow: '0 1px 3px rgba(0,0,0,0.6)'}}>{label}</span>
          </div>
        ))}
        {liked ? [0, 1, 2].map((i) => {
          const f = Math.max(0, Math.min(1, (t - likeT - i * 0.18) / 1.1));
          if (f <= 0 || f >= 1) return null;
          return <div key={i} style={{position: 'absolute', left: 372 + Math.sin(i * 2 + f * 6) * 18, top: 470 - f * 200, opacity: 1 - f, transform: `scale(${0.6 + f * 0.6})`}}>
            <Ph.Heart size={34} weight="fill" color="#FE2C55" /></div>;
        }) : null}
        <div style={{position: 'absolute', left: 16, top: 760, width: 330}}>
          <div style={{...ui(700, 18, '#fff'), textShadow: '0 1px 3px rgba(0,0,0,0.6)'}}>{txt(d.handle) || '@yourbrand'}</div>
          <div style={{...ui(400, 16, '#fff', 1.35), marginTop: 4, textShadow: '0 1px 3px rgba(0,0,0,0.6)'}}>{txt(d.caption) || 'This one change doubled my sales #smallbusiness'}</div>
          <div style={{display: 'flex', alignItems: 'center', gap: 6, marginTop: 6, ...ui(500, 15, '#fff')}}><Ph.MusicNotes size={15} weight="fill" />{txt(d.sound) || 'original sound'}</div>
        </div>
        {dk > 0 ? (
          <div style={{position: 'absolute', left: 0, top: 560 + (1 - dk) * 380, width: PW, height: PH - 560, borderRadius: '18px 18px 0 0', background: '#FFFFFF', zIndex: 10}}>
            <div style={{textAlign: 'center', marginTop: 14, ...ui(700, 15, '#161823')}}>{isFinite(comN) ? `${fmtIG(comN)} comments` : `${coms.length} comments`}</div>
            {comVis.map((x, idx) => {
              const c = x.r ?? {};
              const y = 50 + slotY(comVis, idx, 78);
              return (
                <div key={x.i} style={{position: 'absolute', left: 16, right: 16, top: y, height: 72, display: 'flex', gap: 12, opacity: x.k, transform: `translateY(${(1 - x.k) * -12}px)`}}>
                  <div style={{width: 40, height: 40, borderRadius: 20, background: ['#FE2C55', '#25F4EE', '#7C5CFF', '#F59F00'][x.i % 4], display: 'grid', placeItems: 'center', ...ui(700, 17, '#fff'), flex: 'none'}}>
                    {txt(c.name).slice(0, 1).toUpperCase()}</div>
                  <div style={{flex: 1, minWidth: 0}}>
                    <div style={ui(600, 15, '#8A8B91')}>{txt(c.name)}</div>
                    <div style={{...ui(500, 17, '#161823', 1.3), display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden'}}>{txt(c.text)}</div>
                  </div>
                  <div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', ...ui(500, 13, '#8A8B91')}}><Ph.Heart size={18} color="#8A8B91" />{txt(c.likes) || ''}</div>
                </div>
              );
            })}
          </div>
        ) : null}
      </>
    );
  },
};

export const KIT3_SKINS: Record<string, Skin> = {terminal, cursor: codeSkin('cursor'), vscode: codeSkin('vscode'), canva, capcut, ads, ytstudio, tiktok};
