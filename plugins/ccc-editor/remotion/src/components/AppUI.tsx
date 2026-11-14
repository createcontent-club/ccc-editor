import React from 'react';
import {Easing, interpolate} from 'remotion';
import * as Ph from '@phosphor-icons/react';
import {SERIF_FONT, UI_FONT} from '../style';

/**
 * App UI kit (principles.md 45–47, recenzija test-video-petar v1): verne rekreacije alata o kojima klijenti pričaju
 * (Claude, ChatGPT, Notion, Google Sheets), da se proces koji govornik opisuje ODIGRA na pravom interfejsu umesto
 * ikonica. Jedan moment `app` = prozor alata + događaji na reč: kursor i klik, meni sa osvetljenom stavkom, kucanje,
 * slanje, snimanje (REC okvir + tajmer), glas (talas), beleške "zašto" uz kursor, skill kartica sa koracima
 * (dodaj / štikliraj sam / crveni korak), tabovi pregledača i kamera (zoom na deo interfejsa).
 *
 * Koordinate su "dizajn" pikseli prozora 900×600; kamera ga skalira i pomera unutar gornje polovine (1080 × height).
 * Tekst je krupan (≥ 22 px na skali 1) jer se gleda na telefonu.
 */

type P = {d: any; t: number; dur: number; acc: string; dark: boolean; height: number};
type Rect = {x: number; y: number; w: number; h: number};

const W = 900, H = 600;
const EO = Easing.bezier(0.16, 1, 0.3, 1);
const GLIDE = Easing.bezier(0.42, 0.08, 0.22, 1);
const ease = (t: number, from: number, len: number, curve: (n: number) => number = EO) =>
  interpolate(t - from, [0, len], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: curve});
const T = (x: any, fb: number) => (typeof x?.atT === 'number' ? x.atT : fb);
const txt = (x: any) => (typeof x === 'string' ? x : String(x?.text ?? x?.label ?? ''));
const RED = '#FF4D4D';
const rgba = (hex: string, a: number) =>
  `rgba(${parseInt(hex.slice(1, 3), 16)},${parseInt(hex.slice(3, 5), 16)},${parseInt(hex.slice(5, 7), 16)},${a})`;
const ui = (w: number, size: number, color: string, lh = 1.25): React.CSSProperties =>
  ({fontFamily: `"${UI_FONT}", "Inter", sans-serif`, fontWeight: w, fontSize: size, color, lineHeight: lh, letterSpacing: '-0.01em'});
const center = (r: Rect) => ({x: r.x + r.w / 2, y: r.y + r.h / 2});
const abs = (r: Rect, extra: React.CSSProperties = {}): React.CSSProperties =>
  ({position: 'absolute', left: r.x, top: r.y, width: r.w, height: r.h, boxSizing: 'border-box', ...extra});

export const APPS = ['claude', 'chatgpt', 'notion', 'sheets'] as const;

// ------------------------------------------------------------------ logotipi (crtani, bez preuzimanja)
const ClaudeMark: React.FC<{size: number; spin?: number}> = ({size, spin = 0}) => {
  const rays = [1, 0.78, 0.95, 0.72, 1, 0.82, 0.92, 0.7, 0.98, 0.8, 0.9, 0.74];
  return (
    <svg width={size} height={size} viewBox="-50 -50 100 100" style={{transform: `rotate(${spin}deg)`}}>
      {rays.map((r, i) => (
        <rect key={i} x={-4.2} y={-48 * r} width={8.4} height={44 * r} rx={4.2} fill="#D97757"
          transform={`rotate(${(i * 360) / rays.length + (i % 2 ? 6 : 0)})`} />
      ))}
    </svg>
  );
};
const OpenAIMark: React.FC<{size: number; color: string}> = ({size, color}) => (
  <svg width={size} height={size} viewBox="-50 -50 100 100">
    {[0, 60, 120, 180, 240, 300].map((a) => (
      <rect key={a} x={-11} y={-40} width={22} height={52} rx={11} fill="none" stroke={color} strokeWidth={7}
        transform={`rotate(${a}) translate(0 -2)`} />
    ))}
  </svg>
);
const NotionMark: React.FC<{size: number}> = ({size}) => (
  <svg width={size} height={size} viewBox="0 0 100 100">
    <rect x={8} y={8} width={84} height={84} rx={14} fill="#fff" stroke="#111" strokeWidth={7} />
    <text x={50} y={72} textAnchor="middle" fontFamily="Georgia, serif" fontWeight={700} fontSize={58} fill="#111">N</text>
  </svg>
);
const SheetsMark: React.FC<{size: number}> = ({size}) => (
  <svg width={size * 0.78} height={size} viewBox="0 0 78 100">
    <path d="M6 0 H52 L78 26 V94 a6 6 0 0 1 -6 6 H6 a6 6 0 0 1 -6 -6 V6 a6 6 0 0 1 6 -6 Z" fill="#0F9D58" />
    <path d="M52 0 V20 a6 6 0 0 0 6 6 H78 Z" fill="#87CEAC" />
    <rect x={16} y={44} width={46} height={36} rx={3} fill="#fff" />
    <rect x={20} y={48} width={17} height={12} fill="#0F9D58" /><rect x={41} y={48} width={17} height={12} fill="#0F9D58" />
    <rect x={20} y={64} width={17} height={12} fill="#0F9D58" /><rect x={41} y={64} width={17} height={12} fill="#0F9D58" />
  </svg>
);

// ------------------------------------------------------------------ palete
const PAL = {
  claude: {
    light: {bg: '#FAF9F5', rail: '#F3F1EA', card: '#FFFFFF', line: '#E4E1D7', ink: '#141413', mut: '#87857E', bubble: '#EFECE3', menu: '#FFFFFF'},
    dark: {bg: '#262624', rail: '#1F1E1D', card: '#30302E', line: '#45443F', ink: '#F5F4EE', mut: '#A3A19A', bubble: '#141413', menu: '#30302E'},
  },
  chatgpt: {
    light: {bg: '#FFFFFF', rail: '#F9F9F9', card: '#FFFFFF', line: '#E3E3E3', ink: '#0D0D0D', mut: '#8F8F8F', bubble: '#F1F1F1', menu: '#FFFFFF'},
    dark: {bg: '#212121', rail: '#181818', card: '#303030', line: '#424242', ink: '#ECECEC', mut: '#AFAFAF', bubble: '#303030', menu: '#353535'},
  },
  notion: {
    light: {bg: '#FFFFFF', rail: '#F7F7F5', card: '#FFFFFF', line: '#E9E9E7', ink: '#37352F', mut: '#91918E', bubble: '#EFEFED', menu: '#FFFFFF'},
    dark: {bg: '#191919', rail: '#202020', card: '#252525', line: '#2F2F2F', ink: '#E3E2E0', mut: '#9B9A97', bubble: '#2C2C2C', menu: '#252525'},
  },
  sheets: {
    light: {bg: '#F9FBFD', rail: '#EDF2FA', card: '#FFFFFF', line: '#E1E3E1', ink: '#1F1F1F', mut: '#5F6368', bubble: '#F8F9FA', menu: '#FFFFFF'},
    dark: {bg: '#F9FBFD', rail: '#EDF2FA', card: '#FFFFFF', line: '#E1E3E1', ink: '#1F1F1F', mut: '#5F6368', bubble: '#F8F9FA', menu: '#FFFFFF'},
  },
};
type Pal = typeof PAL.claude.light;

const MENU_DEFAULT: Record<string, string[]> = {
  claude: ['Add files or photos', 'Take a screenshot', 'Add to project', 'Use a skill'],
  chatgpt: ['Add photos & files', 'Create image', 'Deep research', 'Agent mode'],
  notion: ['Text', 'Heading 1', 'To-do list', 'Table', 'Ask AI'],
  sheets: ['Add-ons', 'Macros', 'Apps Script'],
};
const itemIcon = (s: string) => {
  const k = s.toLowerCase();
  if (/record/.test(k)) return Ph.Record;
  if (/screenshot|camera/.test(k)) return Ph.Camera;
  if (/file|photo|attach/.test(k)) return Ph.Paperclip;
  if (/project|folder/.test(k)) return Ph.FolderSimple;
  if (/skill|magic|ai/.test(k)) return Ph.Sparkle;
  if (/image/.test(k)) return Ph.ImageSquare;
  if (/research|search/.test(k)) return Ph.Binoculars;
  if (/agent|bot/.test(k)) return Ph.Robot;
  if (/github|code|script/.test(k)) return Ph.Code;
  if (/heading/.test(k)) return Ph.TextHOne;
  if (/to-do|todo|check/.test(k)) return Ph.CheckSquare;
  if (/table/.test(k)) return Ph.Table;
  if (/text/.test(k)) return Ph.TextT;
  if (/macro/.test(k)) return Ph.Lightning;
  if (/add-on|extension/.test(k)) return Ph.PuzzlePiece;
  if (/style|write/.test(k)) return Ph.PencilSimple;
  return Ph.DotOutline;
};

// ------------------------------------------------------------------ stanje u trenutku t
type St = {
  t: number; d: any; acc: string; dark: boolean; pal: Pal; app: string;
  typed: string; typing: boolean; caret: boolean; sendP: number; sent: string; tabs: any[]; activeTab: number;
};
const typedAt = (inp: any, t: number) => {
  if (!inp) return {s: '', on: false, full: false};
  const s = txt(inp);
  const T0 = T(inp, 0.4);
  const len = Math.min(1.5, Math.max(0.5, s.length * 0.05));
  const k = interpolate(t - T0, [0, len], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return {s: s.slice(0, Math.round(k * s.length)), on: t >= T0 - 0.25, full: k >= 1};
};

// ------------------------------------------------------------------ skinovi: osnova + sidra (dizajn koordinate)
type Skin = {anchors: (st: St) => Record<string, Rect>; menuFrom: string; Body: React.FC<{st: St; a: Record<string, Rect>}>};

const Caret: React.FC<{st: St; size: number; color: string}> = ({st, size, color}) =>
  st.caret ? <span style={{display: 'inline-block', width: 2.5, height: size * 1.05, background: color, marginLeft: 2, verticalAlign: 'text-bottom',
    opacity: Math.floor(st.t * 2.2) % 2 === 0 ? 1 : 0}} /> : null;

const TrafficLights: React.FC = () => (
  <div style={{position: 'absolute', left: 20, top: 16, display: 'flex', gap: 9}}>
    {['#FF5F57', '#FEBC2E', '#28C840'].map((c) => <div key={c} style={{width: 14, height: 14, borderRadius: 7, background: c}} />)}
  </div>
);

const Shimmer: React.FC<{st: St; x: number; y: number; w: number; T0: number; n?: number}> = ({st, x, y, w, T0, n = 3}) => (
  <>
    {Array.from({length: n}).map((_, i) => {
      const k = ease(st.t, T0 + i * 0.18, 0.4);
      const ww = [1, 0.86, 0.6][i % 3] * w;
      const sh = (st.t * 0.9 + i * 0.2) % 1;
      return (
        <div key={i} style={{position: 'absolute', left: x, top: y + i * 38, width: ww * k, height: 20, borderRadius: 10, opacity: k,
          background: `linear-gradient(90deg, ${st.pal.bubble} ${sh * 100 - 30}%, ${st.dark ? '#5A5955' : '#DCD9CF'} ${sh * 100}%, ${st.pal.bubble} ${sh * 100 + 30}%)`}} />
      );
    })}
  </>
);

const ReplyText: React.FC<{st: St; x: number; y: number; w: number; T0: number}> = ({st, x, y, w, T0}) => {
  const r = st.d.reply;
  if (!r) return <Shimmer st={st} x={x} y={y + 6} w={w} T0={T0} />;
  const s = txt(r);
  const k = interpolate(st.t - T0, [0, Math.min(1.8, s.length * 0.03)], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return <div style={{position: 'absolute', left: x, top: y, width: w, ...ui(500, 25, st.pal.ink, 1.4)}}>{s.slice(0, Math.round(k * s.length))}</div>;
};

const UserBubble: React.FC<{st: St; right: number; top: number; maxW: number}> = ({st, right, top, maxW}) => {
  const k = st.sendP;
  if (k <= 0) return null;
  return (
    <div style={{position: 'absolute', right: W - right, top: top + (1 - k) * 60, maxWidth: maxW, padding: '14px 22px', borderRadius: 22,
      background: st.pal.bubble, opacity: k, ...ui(500, 26, st.pal.ink, 1.35)}}>{st.sent}</div>
  );
};

const claude: Skin = {
  menuFrom: 'plus',
  anchors: (st) => {
    const dy = st.sendP * 170;  // posle slanja input ide dole, ali ostaje ceo u prozoru (dno 580 < 600)
    return {
      window: {x: 0, y: 0, w: W, h: H}, rail: {x: 0, y: 44, w: 72, h: H - 44}, main: {x: 72, y: 44, w: W - 72, h: H - 44},
      greeting: {x: 160, y: 130, w: 650, h: 80}, input: {x: 112, y: 240 + dy, w: 748, h: 170},
      plus: {x: 128, y: 350 + dy, w: 44, h: 44}, toggle: {x: 186, y: 350 + dy, w: 214, h: 44},
      model: {x: 590, y: 350 + dy, w: 150, h: 44}, mic: {x: 742, y: 352 + dy, w: 40, h: 40}, send: {x: 796, y: 348 + dy, w: 48, h: 48},
      chat: {x: 100, y: 70, w: 780, h: 300},
    };
  },
  Body: ({st, a}) => {
    const p = st.pal;
    const g = 1 - st.sendP;
    const has = st.typed.length > 0;
    return (
      <>
        <div style={abs(a.rail, {background: p.rail, borderRight: `1px solid ${p.line}`})}>
          {[Ph.SidebarSimple, Ph.PlusCircle, Ph.ChatsCircle, Ph.FolderSimple, Ph.Code].map((I, i) => (
            <div key={i} style={{position: 'absolute', left: 20, top: 24 + i * 58}}>
              <I size={32} weight={i === 1 ? 'fill' : 'regular'} color={i === 1 ? '#D97757' : p.mut} />
            </div>
          ))}
          <div style={{position: 'absolute', left: 16, bottom: 20, width: 40, height: 40, borderRadius: 20, background: st.dark ? '#5B5A55' : '#D9D6CC',
            display: 'grid', placeItems: 'center', ...ui(700, 18, p.ink)}}>{String(st.d.user ?? 'A').slice(0, 1).toUpperCase()}</div>
        </div>
        <div style={{...abs(a.greeting), display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 18, opacity: g,
          transform: `translateY(${-st.sendP * 40}px)`}}>
          <ClaudeMark size={50} />
          <span style={{fontFamily: `"${SERIF_FONT}", Georgia, serif`, fontSize: 56, color: p.ink, letterSpacing: '-0.01em'}}>
            {txt(st.d.greeting) || 'Good afternoon'}
          </span>
        </div>
        <UserBubble st={st} right={860} top={80} maxW={560} />
        {st.sendP > 0 ? (
          <>
            <div style={{position: 'absolute', left: 104, top: 168 + (1 - st.sendP) * 40, opacity: st.sendP}}>
              <ClaudeMark size={40} spin={st.t * 90} />
            </div>
            <ReplyText st={st} x={160} y={168} w={660} T0={T(st.d.send, 0) + 0.45} />
          </>
        ) : null}
        <div style={abs(a.input, {background: p.card, border: `1.5px solid ${p.line}`, borderRadius: 26,
          boxShadow: st.dark ? '0 10px 30px rgba(0,0,0,0.35)' : '0 10px 30px rgba(60,50,30,0.08)'})}>
          <div style={{position: 'absolute', left: 28, top: 28, right: 28, ...ui(has ? 500 : 400, 28, has ? p.ink : p.mut, 1.3)}}>
            {has ? st.typed : txt(st.d.placeholder) || 'How can I help you today?'}
            <Caret st={st} size={28} color={p.ink} />
          </div>
        </div>
        <div style={abs(a.plus, {borderRadius: 22, border: `1.5px solid ${p.line}`, display: 'grid', placeItems: 'center', background: p.card})}>
          <Ph.Plus size={24} weight="bold" color={p.ink} />
        </div>
        <div style={abs(a.toggle, {borderRadius: 12, background: p.rail, display: 'flex', alignItems: 'center', padding: 4, gap: 4})}>
          <div style={{flex: 1, textAlign: 'center', ...ui(500, 21, p.mut)}}>Chat</div>
          <div style={{flex: 1.25, height: '100%', borderRadius: 9, background: p.card, border: '2px solid #D97757', display: 'grid', placeItems: 'center',
            boxSizing: 'border-box', ...ui(600, 21, p.ink)}}>Cowork</div>
        </div>
        <div style={{...abs(a.model), display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 6, paddingRight: 10}}>
          <span style={ui(600, 21, p.ink)}>{txt(st.d.model) || 'Opus 4.8'}</span>
          <Ph.CaretDown size={18} weight="bold" color={p.mut} />
        </div>
        <div style={{...abs(a.mic), display: 'grid', placeItems: 'center'}}><Ph.Microphone size={28} color={p.mut} /></div>
        <div style={abs(a.send, {borderRadius: 13, background: '#D97757', opacity: has || st.sendP > 0 ? 1 : 0.55, display: 'grid', placeItems: 'center'})}>
          <Ph.ArrowUp size={26} weight="bold" color="#fff" />
        </div>
        <div style={{position: 'absolute', left: 130, top: a.input.y + 192, display: 'flex', gap: 26, opacity: g}}>
          {['Project or folder', 'Ask'].map((s, i) => (
            <div key={s} style={{display: 'flex', alignItems: 'center', gap: 8}}>
              {i === 0 ? <Ph.FolderSimple size={24} color={p.mut} /> : <Ph.HandPalm size={24} color={p.mut} />}
              <span style={ui(500, 21, p.mut)}>{s}</span><Ph.CaretDown size={16} color={p.mut} />
            </div>
          ))}
        </div>
      </>
    );
  },
};

const chatgpt: Skin = {
  menuFrom: 'plus',
  anchors: (st) => {
    const dy = st.sendP * 196;  // dno inputa 578 < 600
    return {
      window: {x: 0, y: 0, w: W, h: H}, rail: {x: 0, y: 44, w: 72, h: H - 44}, main: {x: 72, y: 44, w: W - 72, h: H - 44},
      greeting: {x: 140, y: 150, w: 690, h: 70}, input: {x: 112, y: 250 + dy, w: 748, h: 132},
      plus: {x: 132, y: 320 + dy, w: 46, h: 46}, mic: {x: 734, y: 322 + dy, w: 42, h: 42}, send: {x: 790, y: 318 + dy, w: 52, h: 52},
      model: {x: 96, y: 54, w: 190, h: 40}, chat: {x: 100, y: 70, w: 780, h: 300},
    };
  },
  Body: ({st, a}) => {
    const p = st.pal;
    const has = st.typed.length > 0;
    return (
      <>
        <div style={abs(a.rail, {background: p.rail})}>
          <div style={{position: 'absolute', left: 17, top: 18}}><OpenAIMark size={38} color={p.ink} /></div>
          {[Ph.SidebarSimple, Ph.NotePencil, Ph.MagnifyingGlass, Ph.ImagesSquare].map((I, i) => (
            <div key={i} style={{position: 'absolute', left: 20, top: 80 + i * 58}}><I size={30} color={p.ink} /></div>
          ))}
        </div>
        <div style={{...abs(a.model), display: 'flex', alignItems: 'center', gap: 8}}>
          <span style={ui(600, 26, p.ink)}>{txt(st.d.model) || 'ChatGPT'}</span><Ph.CaretDown size={20} weight="bold" color={p.mut} />
        </div>
        <div style={{position: 'absolute', right: 26, top: 56, width: 38, height: 38, borderRadius: 19, background: '#7C5CFF',
          display: 'grid', placeItems: 'center', ...ui(700, 17, '#fff')}}>{String(st.d.user ?? 'A').slice(0, 1).toUpperCase()}</div>
        <div style={{...abs(a.greeting), display: 'grid', placeItems: 'center', opacity: 1 - st.sendP, ...ui(600, 42, p.ink)}}>
          {txt(st.d.greeting) || 'What can I help with?'}
        </div>
        <UserBubble st={st} right={860} top={80} maxW={560} />
        {st.sendP > 0 ? (
          <>
            {!st.d.reply ? <div style={{position: 'absolute', left: 112, top: 182, width: 18, height: 18, borderRadius: 9, background: p.ink,
              transform: `scale(${0.8 + 0.25 * Math.sin(st.t * 7)})`, opacity: st.sendP}} /> : null}
            <ReplyText st={st} x={112} y={170} w={720} T0={T(st.d.send, 0) + 0.45} />
          </>
        ) : null}
        <div style={abs(a.input, {background: p.card, border: `1.5px solid ${p.line}`, borderRadius: 32,
          boxShadow: st.dark ? '0 8px 26px rgba(0,0,0,0.4)' : '0 8px 26px rgba(0,0,0,0.07)'})}>
          <div style={{position: 'absolute', left: 32, top: 22, right: 32, ...ui(has ? 500 : 400, 28, has ? p.ink : p.mut, 1.3)}}>
            {has ? st.typed : txt(st.d.placeholder) || 'Ask anything'}<Caret st={st} size={28} color={p.ink} />
          </div>
        </div>
        <div style={{...abs(a.plus), display: 'grid', placeItems: 'center'}}><Ph.Plus size={30} color={p.ink} /></div>
        <div style={{...abs(a.mic), display: 'grid', placeItems: 'center'}}><Ph.Microphone size={28} color={p.ink} /></div>
        <div style={abs(a.send, {borderRadius: 26, background: st.dark ? '#ECECEC' : '#0D0D0D', display: 'grid', placeItems: 'center'})}>
          {has ? <Ph.ArrowUp size={26} weight="bold" color={st.dark ? '#0D0D0D' : '#fff'} />
            : <Ph.Waveform size={28} weight="bold" color={st.dark ? '#0D0D0D' : '#fff'} />}
        </div>
      </>
    );
  },
};

const notion: Skin = {
  menuFrom: 'input',
  anchors: (st) => {
    const blocks: any[] = st.d.blocks ?? [];
    const yIn = 236 + blocks.length * 46;
    return {
      window: {x: 0, y: 0, w: W, h: H}, sidebar: {x: 0, y: 44, w: 230, h: H - 44}, page: {x: 230, y: 44, w: W - 230, h: H - 44},
      title: {x: 280, y: 140, w: 580, h: 64}, blocks: {x: 280, y: 226, w: 580, h: Math.max(46, blocks.length * 46)},
      input: {x: 280, y: yIn, w: 580, h: 44},
    };
  },
  Body: ({st, a}) => {
    const p = st.pal;
    const pages: string[] = (st.d.pages ?? [txt(st.d.title) || 'Weekly Report', 'Content ideas', 'Clients']).map(txt);
    const blocks: any[] = st.d.blocks ?? [];
    return (
      <>
        <div style={abs(a.sidebar, {background: p.rail, borderRight: `1px solid ${p.line}`})}>
          <div style={{position: 'absolute', left: 18, top: 16, display: 'flex', alignItems: 'center', gap: 10}}>
            {txt(st.d.workspace) ? (
              <div style={{width: 28, height: 28, borderRadius: 6, background: st.dark ? '#3A3A3A' : '#E3E2E0', display: 'grid', placeItems: 'center',
                ...ui(700, 16, p.ink)}}>{txt(st.d.workspace).slice(0, 1).toUpperCase()}</div>
            ) : <NotionMark size={30} />}
            <span style={ui(600, 20, p.ink)}>{txt(st.d.workspace) || 'Workspace'}</span>
          </div>
          {[[Ph.MagnifyingGlass, 'Search'], [Ph.House, 'Home'], [Ph.Tray, 'Inbox']].map(([I, s]: any, i) => (
            <div key={s} style={{position: 'absolute', left: 20, top: 66 + i * 40, display: 'flex', alignItems: 'center', gap: 10}}>
              <I size={21} color={p.mut} /><span style={ui(500, 19, p.mut)}>{s}</span>
            </div>
          ))}
          <div style={{position: 'absolute', left: 20, top: 200, ...ui(600, 15, p.mut)}}>Private</div>
          {pages.slice(0, 5).map((s, i) => (
            <div key={i} style={{position: 'absolute', left: 10, right: 10, top: 228 + i * 40, height: 36, borderRadius: 6, background: i === 0 ? p.bubble : undefined,
              display: 'flex', alignItems: 'center', gap: 10, paddingLeft: 10}}>
              <Ph.FileText size={21} color={p.mut} /><span style={{...ui(i === 0 ? 600 : 500, 19, p.ink), whiteSpace: 'nowrap', overflow: 'hidden'}}>{s}</span>
            </div>
          ))}
        </div>
        <div style={{position: 'absolute', left: 280, top: 70}}>
          {st.d.icon ? <span style={{fontSize: 58}}>{txt(st.d.icon)}</span> : <Ph.FileText size={62} weight="duotone" color={p.mut} />}
        </div>
        <div style={{...abs(a.title), ...ui(700, 44, p.ink, 1.2), whiteSpace: 'nowrap', overflow: 'hidden'}}>{txt(st.d.title) || 'Weekly Report'}</div>
        {blocks.map((b, i) => {
          const s = txt(b);
          const todo = /^\[( |x)\]\s*/i.exec(s);
          const bullet = /^[-•]\s*/.exec(s);
          const body = s.replace(/^\[( |x)\]\s*|^[-•]\s*/i, '');
          const k = ease(st.t, T(b, -1), 0.4);
          return (
            <div key={i} style={{position: 'absolute', left: 280, top: 230 + i * 46, display: 'flex', alignItems: 'center', gap: 12, opacity: k,
              transform: `translateY(${(1 - k) * 10}px)`}}>
              {todo ? (todo[1].toLowerCase() === 'x' ? <Ph.CheckSquare size={26} weight="fill" color="#2383E2" /> : <Ph.Square size={26} color={p.mut} />)
                : bullet ? <div style={{width: 8, height: 8, borderRadius: 4, background: p.ink, margin: '0 6px'}} /> : null}
              <span style={{...ui(400, 24, todo && todo[1].toLowerCase() === 'x' ? p.mut : p.ink), textDecoration: todo && todo[1].toLowerCase() === 'x' ? 'line-through' : undefined}}>{body}</span>
            </div>
          );
        })}
        <div style={{...abs(a.input), ...ui(400, 24, st.typed ? p.ink : p.mut), display: 'flex', alignItems: 'center',
          opacity: st.typing || st.typed ? 1 : 0}}>
          {st.typed || (st.typing ? '' : '')}<Caret st={st} size={24} color={p.ink} />
        </div>
      </>
    );
  },
};

const COLS = ['A', 'B', 'C', 'D', 'E'];
const CW = [212, 172, 160, 150, 126];
const cellRect = (ref: string): Rect | null => {
  const m = /^([A-E])(\d+)$/i.exec(ref || '');
  if (!m) return null;
  const c = COLS.indexOf(m[1].toUpperCase());
  const r = parseInt(m[2], 10) - 1;
  if (r < 0 || r > 7) return null;
  const x = 46 + CW.slice(0, c).reduce((s, v) => s + v, 0);
  return {x, y: 216 + r * 46, w: CW[c], h: 46};
};
const sheets: Skin = {
  menuFrom: 'menubar',
  anchors: (st) => {
    const base: Record<string, Rect> = {
      window: {x: 0, y: 0, w: W, h: H}, title: {x: 70, y: 52, w: 420, h: 34}, menubar: {x: 646, y: 88, w: 112, h: 28},
      toolbar: {x: 16, y: 122, w: W - 32, h: 40}, formula: {x: 16, y: 170, w: W - 32, h: 34},
      grid: {x: 0, y: 186, w: W, h: H - 186},
    };
    COLS.forEach((c) => { for (let r = 1; r <= 8; r++) { const cr = cellRect(`${c}${r}`); if (cr) base[`${c}${r}`] = cr; } });
    const ref = st.d.input?.cell;
    if (ref && base[ref.toUpperCase()]) base.input = base[ref.toUpperCase()];
    else base.input = base.B2;
    return base;
  },
  Body: ({st, a}) => {
    const p = st.pal;
    const cells: any[][] = st.d.cells ?? [];
    const act = (st.d.input?.cell ?? 'B2').toUpperCase();
    return (
      <>
        <div style={{position: 'absolute', left: 20, top: 52}}><SheetsMark size={40} /></div>
        <div style={{...abs(a.title), ...ui(500, 24, p.ink), whiteSpace: 'nowrap'}}>{txt(st.d.title) || 'Untitled spreadsheet'}</div>
        <div style={{position: 'absolute', left: 70, top: 90, display: 'flex', gap: 16}}>
          {['File', 'Edit', 'View', 'Insert', 'Format', 'Data', 'Tools', 'Extensions', 'Help'].map((s) => (
            <span key={s} style={ui(500, 17, p.ink)}>{s}</span>
          ))}
        </div>
        <div style={abs(a.toolbar, {background: p.rail, borderRadius: 20, display: 'flex', alignItems: 'center', gap: 22, paddingLeft: 22})}>
          {[Ph.MagnifyingGlass, Ph.ArrowCounterClockwise, Ph.ArrowClockwise, Ph.Printer, Ph.PaintRoller, Ph.TextB, Ph.TextItalic, Ph.PaintBucket, Ph.Table].map((I, i) => (
            <I key={i} size={22} color={p.mut} />
          ))}
        </div>
        <div style={abs(a.formula, {display: 'flex', alignItems: 'center', gap: 14, borderBottom: `1px solid ${p.line}`})}>
          <span style={{...ui(600, 18, p.mut), width: 50}}>{act}</span>
          <span style={{...ui(500, 20, p.mut), fontStyle: 'italic'}}>fx</span>
          <span style={ui(400, 20, p.ink)}>{st.typed || txt((cells[parseInt(act.slice(1), 10) - 1] ?? [])[COLS.indexOf(act[0])] ?? '')}</span>
        </div>
        <div style={{position: 'absolute', left: 0, top: 186, width: W, height: H - 186, background: '#fff'}}>
          <div style={{position: 'absolute', left: 0, top: 0, width: W, height: 30, background: p.bubble, borderBottom: `1px solid ${p.line}`}} />
          {COLS.map((c, i) => {
            const x = 46 + CW.slice(0, i).reduce((s, v) => s + v, 0);
            return <div key={c} style={{position: 'absolute', left: x, top: 0, width: CW[i], height: 30, borderLeft: `1px solid ${p.line}`,
              display: 'grid', placeItems: 'center', ...ui(500, 15, p.mut)}}>{c}</div>;
          })}
          {Array.from({length: 8}).map((_, r) => (
            <div key={r} style={{position: 'absolute', left: 0, top: 30 + r * 46, width: W, height: 46, borderBottom: `1px solid ${p.line}`}}>
              <div style={{position: 'absolute', left: 0, top: 0, width: 46, height: 46, background: p.bubble, display: 'grid', placeItems: 'center',
                ...ui(500, 15, p.mut)}}>{r + 1}</div>
              {COLS.map((c, i) => {
                const x = 46 + CW.slice(0, i).reduce((s, v) => s + v, 0);
                const ref = `${c}${r + 1}`;
                const raw = (cells[r] ?? [])[i];
                const v = ref === act && st.typed ? st.typed : txt(raw);
                const k = raw && typeof raw === 'object' ? ease(st.t, T(raw, -1), 0.35) : 1;
                return <div key={c} style={{position: 'absolute', left: x, top: 0, width: CW[i], height: 46, borderLeft: `1px solid ${p.line}`,
                  paddingLeft: 10, boxSizing: 'border-box', display: 'flex', alignItems: 'center', overflow: 'hidden', whiteSpace: 'nowrap', opacity: k,
                  background: raw && typeof raw === 'object' && raw.tone === 'bad' ? rgba(RED, 0.12) : undefined,
                  ...ui(r === 0 ? 700 : 400, 20, raw && typeof raw === 'object' && raw.tone === 'bad' ? RED : p.ink)}}>{v}{ref === act ? <Caret st={st} size={20} color={p.ink} /> : null}</div>;
              })}
            </div>
          ))}
        </div>
        {a.input ? <div style={abs({x: a.input.x - 1, y: a.input.y, w: a.input.w + 2, h: a.input.h + 1}, {border: '2.5px solid #1A73E8'})} /> : null}
      </>
    );
  },
};

const SKINS: Record<string, Skin> = {claude, chatgpt, notion, sheets};

// ------------------------------------------------------------------ zajednički slojevi
const Cursor: React.FC<{x: number; y: number; click: number; s: number}> = ({x, y, click, s}) => (
  <div style={{position: 'absolute', left: x, top: y, zIndex: 60, pointerEvents: 'none'}}>
    {click > 0 && click < 1 ? (
      <div style={{position: 'absolute', left: -30, top: -30, width: 60, height: 60, borderRadius: 30, border: '4px solid rgba(0,0,0,0.35)',
        transform: `scale(${0.3 + click * 1.1})`, opacity: 1 - click}} />
    ) : null}
    <svg width={38 / s} height={38 / s} viewBox="0 0 24 24" style={{filter: 'drop-shadow(0 3px 5px rgba(0,0,0,0.35))'}}>
      <path d="M4 2 L4 19 L8.6 14.8 L11.6 21.4 L14.4 20.2 L11.4 13.7 L17.6 13.7 Z" fill="#111" stroke="#fff" strokeWidth={1.6} strokeLinejoin="round" />
    </svg>
  </div>
);

type Key = {x: number; y: number; T: number; click: boolean};
const cursorAt = (keys: Key[], t: number) => {
  if (!keys.length) return null;
  let pos = {x: keys[0].x + 120, y: keys[0].y + 90};
  let prevT = 0;
  for (const k of keys) {
    const start = Math.max(prevT + 0.05, k.T - 0.5);
    const p = ease(t, start, Math.max(0.15, k.T - start), GLIDE);
    pos = {x: pos.x + (k.x - pos.x) * p, y: pos.y + (k.y - pos.y) * p};
    prevT = k.T;
  }
  const last = [...keys].reverse().find((k) => k.click && t >= k.T);
  return {...pos, click: last ? Math.min(1, (t - last.T) / 0.45) : 0};
};

const Menu: React.FC<{st: St; r: Rect; items: string[]; hl: number; hlT: number; badge: any; k: number}> = ({st, r, items, hl, hlT, badge, k}) => {
  const p = st.pal;
  const hk = hl >= 0 ? ease(st.t, hlT, 0.35) : 0;
  const bT = T(badge, hlT + 0.35);
  const bk = badge ? ease(st.t, bT, 0.45, Easing.bezier(0.34, 1.5, 0.64, 1)) : 0;
  return (
    <div style={abs(r, {background: p.menu, borderRadius: 18, border: `1.5px solid ${p.line}`, zIndex: 40, padding: 8,
      boxShadow: st.dark ? '0 24px 60px rgba(0,0,0,0.55)' : '0 24px 60px rgba(40,30,20,0.18)', opacity: k,
      transform: `translateY(${(1 - k) * -12}px) scale(${0.96 + 0.04 * k})`, transformOrigin: '20% 0%'})}>
      {items.map((s, i) => {
        const I = itemIcon(s);
        const on = i === hl ? hk : 0;
        return (
          <div key={i} style={{position: 'relative', height: 56, borderRadius: 12, display: 'flex', alignItems: 'center', gap: 16, paddingLeft: 16,
            background: on ? rgba(st.acc, 0.18 * on) : undefined, boxShadow: on ? `inset 0 0 0 ${2.5 * on}px ${st.acc}` : undefined}}>
            <I size={26} weight={on > 0.5 ? 'bold' : 'regular'} color={on > 0.5 ? p.ink : p.mut} />
            <span style={{...ui(on > 0.5 ? 700 : 500, 24, p.ink), whiteSpace: 'nowrap'}}>{s}</span>
            {i === hl && badge && bk > 0 ? (
              <span style={{marginLeft: 6, padding: '4px 12px', borderRadius: 999, background: st.acc, ...ui(800, 16, '#0A0A0B'), letterSpacing: '0.04em',
                transform: `scale(${bk})`, display: 'inline-block'}}>{txt(badge) || 'NEW'}</span>
            ) : null}
          </div>
        );
      })}
    </div>
  );
};

const SkillCard: React.FC<{st: St; r: Rect}> = ({st, r}) => {
  const c = st.d.card;
  const p = st.pal;
  const T0 = T(c, 0);
  const k = c.cont ? 1 : ease(st.t, T0, 0.55);
  const steps: any[] = c.steps ?? [];
  const run = c.run ? T(c.run, 1e9) : 1e9;
  const tickT = (i: number) => run + 0.3 + i * 0.42;
  // korak sa done: true je već urađen (callback iz ranijeg momenta) — štikliran od prvog frejma, bez ponovnog "pokretanja" (principles 44, 46)
  const preDone = (s: any) => s?.done === true && s?.tone !== 'bad';
  // crveni korak koji je stigao = posao je zaustavljen/pokvaren → status nikad "Done" (principle 49)
  const badIn = steps.some((s: any, i: number) => s?.tone === 'bad' && st.t >= T(s, T0 + 0.25 + i * 0.22));
  const lastGood = steps.reduce((m: number, s: any, i: number) => (s?.tone === 'bad' || preDone(s) ? m : i), -1);
  const allDone = !badIn && steps.length > 0 && (lastGood < 0 ? steps.every(preDone) : st.t >= tickT(lastGood) + 0.2);
  const status = badIn ? (txt(c.status) || 'Stopped') : st.t >= run ? (allDone ? 'Done' : 'Running…') : allDone ? 'Done' : txt(c.status);
  return (
    <div style={abs(r, {background: st.dark ? '#2B2B29' : '#FFFFFF', borderRadius: 24, zIndex: 45, padding: '22px 24px',
      border: `1.5px solid ${st.dark ? '#45443F' : '#E6E3DA'}`, boxShadow: st.dark ? '0 30px 70px rgba(0,0,0,0.6)' : '0 30px 70px rgba(30,25,15,0.2)',
      opacity: k, transform: `translateX(${(1 - k) * 80}px)`})}>
      <div style={{display: 'flex', alignItems: 'center', gap: 10}}>
        <Ph.Sparkle size={24} weight="fill" color={st.acc} />
        <span style={{...ui(800, 15, p.mut), letterSpacing: '0.14em'}}>{txt(c.kicker) || 'SKILL'}</span>
        {status ? (
          <span style={{marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 6, padding: '4px 12px', borderRadius: 999,
            background: badIn ? rgba(RED, 0.18) : allDone ? rgba(st.acc, 0.2) : p.bubble, ...ui(700, 15, badIn ? RED : p.ink)}}>
            {badIn ? <Ph.Prohibit size={18} weight="bold" color={RED} /> : allDone ? <Ph.CheckCircle size={18} weight="fill" color={st.acc} /> : st.t >= run ? <Ph.CircleNotch size={18} weight="bold" color={p.mut}
              style={{transform: `rotate(${st.t * 360}deg)`}} /> : null}
            {status}
          </span>
        ) : null}
      </div>
      <div style={{...ui(800, 30, p.ink, 1.15), marginTop: 10, marginBottom: 14}}>{txt(c.title)}</div>
      {steps.map((s, i) => {
        const sT = T(s, T0 + 0.25 + i * 0.22);
        const sk = c.cont && typeof s?.atT !== 'number' ? 1 : ease(st.t, sT, 0.45);
        const bad = s?.tone === 'bad';
        const done = !bad && (preDone(s) || st.t >= tickT(i));
        const dk = preDone(s) ? 1 : done ? ease(st.t, tickT(i), 0.3, Easing.bezier(0.34, 1.6, 0.64, 1)) : 0;
        const shake = bad ? Math.sin((st.t - sT) * 40) * 6 * Math.max(0, 1 - (st.t - sT) / 0.5) : 0;
        return (
          <div key={i} style={{display: 'flex', alignItems: 'center', gap: 14, height: 54, padding: '0 10px', borderRadius: 12, marginBottom: 4,
            background: bad ? rgba(RED, 0.1 * sk) : undefined, opacity: sk, transform: `translate(${shake}px, ${(1 - sk) * 14}px)`}}>
            <div style={{width: 32, height: 32, borderRadius: 16, flexShrink: 0, display: 'grid', placeItems: 'center',
              background: bad ? RED : done ? st.acc : p.bubble, transform: `scale(${done ? 0.8 + 0.2 * dk : 1})`, ...ui(800, 16, bad || done ? '#0A0A0B' : p.mut)}}>
              {bad ? <Ph.X size={18} weight="bold" color="#fff" /> : done ? <Ph.Check size={18} weight="bold" color="#0A0A0B" /> : i + 1}
            </div>
            <span style={{...ui(600, 24, bad ? RED : p.ink), whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'}}>{txt(s)}</span>
          </div>
        );
      })}
    </div>
  );
};

const Note: React.FC<{st: St; text: string; x: number; y: number; k: number; dim: number}> = ({st, text, x, y, k, dim}) => (
  <div style={{position: 'absolute', left: x, top: y, zIndex: 50, maxWidth: 380, padding: '14px 20px 14px 18px', borderRadius: 16,
    background: st.dark ? '#34332F' : '#FFFFFF', borderLeft: `6px solid ${st.acc}`, boxShadow: '0 16px 40px rgba(0,0,0,0.22)',
    opacity: k * (1 - 0.6 * dim), transform: `translateY(${(1 - k) * 16 - dim * 10}px) scale(${(0.9 + 0.1 * k) * (1 - 0.08 * dim)})`,
    ...ui(600, 24, st.pal.ink, 1.3)}}>{text}</div>
);

// ------------------------------------------------------------------ moment
export const AppMoment: React.FC<P> = ({d, t, dur, acc, dark, height}) => {
  const app = SKINS[d.app] ? d.app : 'claude';
  const skin = SKINS[app];
  // Podrazumevano svetla tema aplikacije (najprepoznatljivija); `theme: "dark"` za tamni Claude/ChatGPT/Notion.
  const useDark = d.theme === 'dark' && app !== 'sheets';
  const pal = (PAL as any)[app][useDark ? 'dark' : 'light'] as Pal;
  const typ = typedAt(d.input, t);
  const sendT = d.send ? T(d.send, 1e9) : 1e9;
  const sendP = ease(t, sendT, 0.6);
  const tabs: any[] = d.tabs ?? [];
  let activeTab = Math.max(0, tabs.findIndex((x) => x?.active));
  tabs.forEach((x, i) => { if (typeof x?.atT === 'number' && t >= x.atT) activeTab = i; });
  const st: St = {t, d, acc, dark: useDark, pal, app,
    typed: sendP > 0.05 ? '' : typ.s, typing: typ.on, caret: typ.on && sendP <= 0.05, sendP, sent: txt(d.input), tabs, activeTab};
  const a = skin.anchors(st);

  // meni
  const menu = d.menu;
  const items: string[] = menu ? (menu.items ?? MENU_DEFAULT[app]).map(txt) : [];
  const menuT = menu ? T(menu, 0.3) : 1e9;
  const hlText = menu?.highlight ? txt(menu.highlight).toLowerCase() : '';
  const hl = hlText ? items.findIndex((s) => s.toLowerCase() === hlText) : -1;
  const hlT = menu?.highlight ? T(menu.highlight, menuT + 0.5) : 1e9;
  const closeT = menu?.close ? T(menu.close, 1e9) : 1e9;
  const mk = menu ? ease(t, menuT, 0.32) * (1 - ease(t, closeT, 0.25)) : 0;
  const from = a[skin.menuFrom] ?? a.input;
  const mh = items.length * 56 + 16;
  const mw = 420;
  let my = from.y + from.h + 10;
  if (my + mh > H - 6) my = Math.max(50, from.y - mh - 10);
  const menuR: Rect = {x: Math.min(W - mw - 10, Math.max(10, from.x - 8)), y: my, w: mw, h: mh};
  const itemR = (i: number): Rect => ({x: menuR.x + 8, y: menuR.y + 8 + i * 56, w: mw - 16, h: 56});
  a.menu = menuR;
  if (hl >= 0) a.item = itemR(hl);

  // kartica
  const card = d.card;
  if (card) {
    const n = (card.steps ?? []).length;
    const ch = 116 + n * 58;
    const cw = 430;
    a.card = card.center ? {x: (W - cw) / 2, y: Math.max(56, (H - ch) / 2 + 20), w: cw, h: ch} : {x: W - cw - 26, y: Math.max(56, (H - ch) / 2 + 20), w: cw, h: ch};
  }
  // tabovi (traka pregledača u vrhu prozora)
  const tabR = (i: number): Rect => ({x: 96 + i * 196, y: 6, w: 190, h: 38});
  tabs.forEach((_, i) => { a[`tab${i}`] = tabR(i); });
  a.top = {x: 0, y: 0, w: W, h: H * 0.55};  // gornji deo prozora (tabovi + vrh stranice)

  // kursor: zadate tačke + automatske (meni, stavka, kucanje, slanje, nov tab)
  const keys: Key[] = [];
  const pt = (to: any): {x: number; y: number} | null => {
    if (to && typeof to === 'object' && typeof to.x === 'number') return {x: to.x, y: to.y};
    const r = a[String(to)];
    return r ? center(r) : null;
  };
  if (menu) { const p0 = center(from); keys.push({...p0, T: menuT, click: true}); }
  if (hl >= 0) { const r0 = itemR(hl); keys.push({x: r0.x + r0.w - 70, y: r0.y + r0.h / 2 + 4, T: hlT, click: true}); }
  if (d.input && app !== 'sheets') { const p0 = center(a.input); keys.push({x: a.input.x + 60, y: p0.y, T: T(d.input, 0.4) - 0.05, click: true}); }
  if (d.input && app === 'sheets') { const p0 = center(a.input); keys.push({...p0, T: T(d.input, 0.4) - 0.05, click: true}); }
  if (d.send) { const p0 = center(a.send ?? a.input); keys.push({...p0, T: sendT, click: true}); }
  tabs.forEach((x, i) => { if (typeof x?.atT === 'number') keys.push({...center(tabR(i)), T: x.atT, click: true}); });
  for (const c of (d.cursor ?? []) as any[]) {
    const p0 = pt(c.to);
    if (p0) keys.push({...p0, T: T(c, 0), click: c.click !== false});
  }
  keys.sort((x, y) => x.T - y.T);
  const cur = d.cursor === false ? null : cursorAt(keys, t);

  // kamera
  // Osnovni kadar: ceo prozor na 0.9, malo niže (iznad njega ima mesta za REC oznaku); zoom = kadar na deo interfejsa.
  // Kartica na sredini bez zadatog zoom-a → kamera sama priđe kartici (čitljivo na telefonu).
  // zoom bez `at` = početni kadar (odmah) — za nastavak (`cont`) da kamera ne skoči nazad na ceo prozor (principles.md 44)
  const zooms: any[] = ((d.zoom ?? []) as any[]).map((z) => ({...z, T: typeof z?.atT === 'number' ? z.atT : -10}));
  if (card && !zooms.some((z) => z.to === 'card') && (card.center || !d.zoom)) zooms.push({to: 'card', T: T(card, 0) + 0.15});
  let view = {x: W / 2, y: H / 2, s: 0.9, cy: Math.min(height / 2 + 50, 592)};
  for (const z of zooms.sort((x, y) => x.T - y.T)) {
    const r = a[String(z.to)] ?? null;
    if (!r) continue;
    const c0 = center(r);
    const zs = typeof z.scale === 'number' ? z.scale : Math.max(1, Math.min(2.3, 860 / r.w, 580 / r.h));
    const k = ease(t, z.T - 0.1, 0.95, GLIDE);
    view = {x: view.x + (c0.x - view.x) * k, y: view.y + (c0.y - view.y) * k, s: view.s + (zs - view.s) * k, cy: view.cy + (540 - view.cy) * k};
  }
  const drift = 1 + 0.018 * interpolate(t, [0, Math.max(0.6, dur)], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const pin = d.cont ? 1 : ease(t, 0, 0.5);
  const s = view.s * drift * (0.95 + 0.05 * pin);
  const CX = 540, CY = view.cy;
  const tx = CX - view.x * s, ty = CY - view.y * s;
  // REC okvir je u prostoru ekrana: oko vidljivog dela prozora (pri zoom-u = okvir kadra), nikad zalutala linija
  const fr = {l: Math.max(14, tx - 8), t: Math.max(14, ty - 8), r: Math.min(1066, tx + W * s + 8), b: Math.min(height - 14, ty + H * s + 8)};

  // REC, glas, beleške
  const recT = d.rec ? T(d.rec, 0) : 1e9;
  const rk = ease(t, recT, 0.4);
  const voiceT = d.voice ? T(d.voice, 0) : 1e9;
  const vk = ease(t, voiceT, 0.45);
  const notes: any[] = (d.notes ?? []).map((n: any, i: number) => ({...n, T: T(n, 0.6 + i * 0.8)}));
  const curAtT = (T0: number) => cursorAt(keys, T0) ?? {x: W / 2, y: H / 2};
  // "staro / ne radi" (principles.md 48): ceo prozor se ugasi u sivo na reč, preko njega može da uđe kartica (novo)
  const dimK = d.dim ? ease(t, T(d.dim, 1e9), 0.5) : 0;
  const tab = tabs[activeTab];
  const away = tabs.length > 0 && activeTab > 0 && typeof tab?.atT === 'number' ? ease(t, tab.atT, 0.35) : 0;

  return (
    <div style={{position: 'absolute', inset: 0, opacity: pin}}>
      <div style={{position: 'absolute', left: 0, top: 0, width: W, height: H, transformOrigin: '0 0',
        transform: `translate(${tx}px, ${ty}px) scale(${s})`}}>
        <div style={{position: 'absolute', inset: 0, borderRadius: 22, overflow: 'hidden', background: pal.bg,
          filter: dimK > 0.01 ? `grayscale(${0.85 * dimK}) brightness(${1 - 0.3 * dimK}) blur(${1.5 * dimK}px)` : undefined,
          boxShadow: dark ? '0 40px 90px rgba(0,0,0,0.6), 0 0 0 1.5px rgba(255,255,255,0.08)' : '0 40px 90px rgba(20,20,40,0.22), 0 0 0 1.5px rgba(0,0,0,0.06)'}}>
          <div style={{position: 'absolute', left: 0, top: 0, width: W, height: 44, background: tabs.length ? (st.dark ? '#1B1B1A' : '#E9E8E4') : pal.bg,
            borderBottom: `1px solid ${pal.line}`}} />
          <TrafficLights />
          {tabs.map((x, i) => {
            const r = tabR(i);
            const k = typeof x?.atT === 'number' ? ease(t, x.atT - 0.35, 0.35) : 1;
            const on = i === activeTab;
            const bad = x?.tone === 'bad';
            return (
              <div key={i} style={abs(r, {borderRadius: '10px 10px 0 0', background: on ? pal.bg : 'transparent', display: 'flex', alignItems: 'center', gap: 8,
                paddingLeft: 14, opacity: k, transform: `translateY(${(1 - k) * 20}px)`, boxShadow: bad && on ? `inset 0 3px 0 ${RED}` : undefined})}>
                <div style={{width: 18, height: 18, borderRadius: 4, background: bad ? RED : i === 0 ? '#D97757' : '#9AA0A6'}} />
                <span style={{...ui(on ? 600 : 500, 17, bad ? RED : pal.ink), whiteSpace: 'nowrap', overflow: 'hidden', maxWidth: 140}}>{txt(x)}</span>
              </div>
            );
          })}
          <skin.Body st={st} a={a} />
          {away > 0 ? (
            <div style={{position: 'absolute', left: 0, top: 44, width: W, height: H - 44, background: st.dark ? '#181818' : '#FFFFFF', opacity: away, zIndex: 20}}>
              <div style={{position: 'absolute', left: 60, top: 40, width: 500, height: 280, borderRadius: 16, background: st.dark ? '#2A2A2A' : '#ECECEC',
                display: 'grid', placeItems: 'center'}}><Ph.PlayCircle size={90} weight="fill" color={st.dark ? '#555' : '#C7C7C7'} /></div>
              <div style={{position: 'absolute', left: 60, top: 344, width: 520, ...ui(700, 30, st.dark ? '#EEE' : '#111', 1.2)}}>{txt(tab?.page) || txt(tab)}</div>
              {[0, 1, 2].map((i) => <div key={i} style={{position: 'absolute', left: 600, top: 40 + i * 104, width: 240, height: 88, borderRadius: 12,
                background: st.dark ? '#2A2A2A' : '#F0F0F0'}} />)}
            </div>
          ) : null}
        </div>
        {mk > 0 ? <Menu st={st} r={menuR} items={items} hl={hl} hlT={hlT} badge={menu.badge} k={mk} /> : null}
        {card && t >= T(card, 0) - 0.05 ? <SkillCard st={st} r={a.card} /> : null}
        {notes.map((n, i) => {
          if (t < n.T) return null;
          const k = ease(t, n.T, 0.4);
          const nxt = notes[i + 1];
          const dim = nxt && t >= nxt.T ? ease(t, nxt.T, 0.4) : 0;
          const old = notes[i + 2] && t >= notes[i + 2].T ? ease(t, notes[i + 2].T, 0.3) : 0;
          const c0 = curAtT(n.T);
          const x = Math.min(W - 400, Math.max(20, c0.x + 34)), y = Math.min(H - 90, Math.max(56, c0.y - 96));
          return <Note key={i} st={st} text={txt(n)} x={x} y={y} k={k * (1 - old)} dim={dim} />;
        })}
        {cur ? <Cursor x={cur.x} y={cur.y} click={cur.click} s={Math.sqrt(Math.max(1, s))} /> : null}
      </div>
      {rk > 0 ? (
        <div style={{position: 'absolute', left: fr.l, top: fr.t, width: fr.r - fr.l, height: fr.b - fr.t, boxSizing: 'border-box',
          borderRadius: 26, border: `6px solid ${RED}`, opacity: rk * (0.75 + 0.25 * Math.sin((t - recT) * 5)),
          boxShadow: `0 0 40px ${rgba(RED, 0.45)}, inset 0 0 30px ${rgba(RED, 0.25)}`, zIndex: 70, pointerEvents: 'none'}} />
      ) : null}
      {rk > 0 ? (
        <div style={{position: 'absolute', right: 1080 - Math.min(990, fr.r - 22), top: Math.max(252, fr.t + 18), transform: `scale(${0.85 + 0.15 * rk})`,
          transformOrigin: '100% 0%', opacity: rk, zIndex: 80,
          display: 'flex', alignItems: 'center', gap: 12, padding: '10px 22px', borderRadius: 999, background: RED, boxShadow: `0 10px 30px ${rgba(RED, 0.4)}`}}>
          <div style={{width: 16, height: 16, borderRadius: 8, background: '#fff', opacity: Math.floor((t - recT) * 2) % 2 === 0 ? 1 : 0.35}} />
          <span style={{...ui(800, 24, '#fff'), letterSpacing: '0.04em'}}>
            REC {`0:${String(Math.max(0, Math.floor(t - recT))).padStart(2, '0')}`}
          </span>
        </div>
      ) : null}
      {vk > 0 ? (
        <div style={{position: 'absolute', left: 540, top: Math.min(height - 150, 780), transform: `translate(-50%, ${(1 - vk) * 20}px)`, opacity: vk, zIndex: 80,
          display: 'flex', alignItems: 'center', gap: 14, padding: '12px 24px', borderRadius: 999, background: dark ? '#26262A' : '#FFFFFF',
          boxShadow: '0 14px 36px rgba(0,0,0,0.25)'}}>
          <Ph.Microphone size={30} weight="fill" color={acc} />
          <div style={{display: 'flex', alignItems: 'center', gap: 5, height: 40}}>
            {Array.from({length: 18}).map((_, i) => (
              <div key={i} style={{width: 6, borderRadius: 3, background: acc,
                height: 8 + 30 * Math.abs(Math.sin((t - voiceT) * 6 + i * 0.7) * Math.sin((t - voiceT) * 2.3 + i * 0.31))}} />
            ))}
          </div>
          {txt(d.voice?.label) ? <span style={ui(700, 22, dark ? '#fff' : '#111')}>{txt(d.voice.label)}</span> : null}
        </div>
      ) : null}
    </div>
  );
};
