import React from 'react';
import {Img, staticFile} from 'remotion';
import * as Ph from '@phosphor-icons/react';
import {
  PW, PH, Pal, Rect, St, Skin, ease, T, txt, RED, rgba, ui, abs, POP, countAt, fmtIG, fmtNum, arrivals, slotY, Caret,
} from './appCore';
import {AppIcon, IgGradient} from './appIcons';

/**
 * Telefon (faza 1 UI kita, 14. nov 2026): okvir iPhone-a + dodir prstom + aplikacije koje klijenti najčešće pominju
 * na telefonu. Dizajn 430 × 932 (iPhone Pro Max tačke); kamera uvek gleda DEO ekrana krupno (tekst ≥ 34 px na videu).
 *   instagram: screen "profile" (pratioci broje), "insights" (pregledi rastu, grafik se crta), "inbox" (DM-ovi stižu)
 *   iphone:    zaključan ekran — notifikacije (Stripe, Instagram, Gmail…) padaju jedna za drugom
 */

const IG_BLUE = '#0095F6';
const file = (x: any): string | null => (x && typeof x === 'object' && x.src ? x.src : null);

// ------------------------------------------------------------------ okvir + dodir
export const PhoneChrome: React.FC<{st: St; dark: boolean; filter?: string; children: React.ReactNode}> = ({st, dark, filter, children}) => {
  const light = st.app === 'iphone' || st.dark;  // beli status bar na tamnoj podlozi
  const ink = light ? '#FFFFFF' : '#000000';
  return (
    <>
      <div style={{position: 'absolute', left: -14, top: -14, width: PW + 28, height: PH + 28, borderRadius: 72, background: '#0B0B0C',
        boxShadow: dark ? '0 50px 110px rgba(0,0,0,0.7), 0 0 0 2px #2A2A2D' : '0 50px 110px rgba(20,20,40,0.35), 0 0 0 2px #3A3A3D'}} />
      <div style={{position: 'absolute', inset: 0, borderRadius: 58, overflow: 'hidden', background: st.pal.bg, filter}}>
        {children}
        <div style={{position: 'absolute', left: 0, top: 0, width: PW, height: 54, zIndex: 30, pointerEvents: 'none'}}>
          <span style={{position: 'absolute', left: 50, top: 17, ...ui(600, 18, ink, 1)}}>{txt(st.d.time) || '9:41'}</span>
          <div style={{position: 'absolute', left: (PW - 124) / 2, top: 11, width: 124, height: 36, borderRadius: 20, background: '#000'}} />
          <div style={{position: 'absolute', right: 30, top: 17, display: 'flex', gap: 6, alignItems: 'center'}}>
            <Ph.CellSignalFull size={19} weight="fill" color={ink} />
            <Ph.WifiHigh size={19} weight="bold" color={ink} />
            <Ph.BatteryFull size={26} weight="fill" color={ink} />
          </div>
        </div>
        <div style={{position: 'absolute', left: (PW - 140) / 2, bottom: 9, width: 140, height: 5, borderRadius: 3, background: ink, opacity: 0.85, zIndex: 30}} />
      </div>
    </>
  );
};

/** Dodir prstom: mek krug + talas na tap (na telefonu nema strelice). */
export const Touch: React.FC<{x: number; y: number; click: number; s: number}> = ({x, y, click}) => (
  <div style={{position: 'absolute', left: x, top: y, zIndex: 60, pointerEvents: 'none'}}>
    {click > 0 && click < 1 ? (
      <div style={{position: 'absolute', left: -34, top: -34, width: 68, height: 68, borderRadius: 34, border: '3px solid rgba(255,255,255,0.9)',
        boxShadow: '0 0 0 2px rgba(0,0,0,0.15)', transform: `scale(${0.4 + click * 1.0})`, opacity: 1 - click}} />
    ) : null}
    <div style={{position: 'absolute', left: -19, top: -19, width: 38, height: 38, borderRadius: 19,
      background: 'rgba(255,255,255,0.55)', border: '2px solid rgba(255,255,255,0.95)', boxShadow: '0 4px 14px rgba(0,0,0,0.35)',
      transform: `scale(${click > 0 && click < 0.35 ? 0.82 : 1})`}} />
  </div>
);

// ------------------------------------------------------------------ Instagram
const IG_PAL: {light: Pal; dark: Pal} = {
  light: {bg: '#FFFFFF', rail: '#FFFFFF', card: '#FFFFFF', line: '#DBDBDB', ink: '#000000', mut: '#737373', bubble: '#EFEFEF', menu: '#FFFFFF'},
  dark: {bg: '#000000', rail: '#000000', card: '#121212', line: '#262626', ink: '#F5F5F5', mut: '#A8A8A8', bubble: '#262626', menu: '#262626'},
};
const TILE_BG = ['linear-gradient(135deg,#F6D365,#FDA085)', 'linear-gradient(135deg,#84FAB0,#8FD3F4)', 'linear-gradient(135deg,#A18CD1,#FBC2EB)',
  'linear-gradient(135deg,#FCCB90,#D57EEB)', 'linear-gradient(135deg,#E0C3FC,#8EC5FC)', 'linear-gradient(135deg,#F093FB,#F5576C)',
  'linear-gradient(135deg,#4FACFE,#00F2FE)', 'linear-gradient(135deg,#43E97B,#38F9D7)', 'linear-gradient(135deg,#FA709A,#FEE140)'];

const Avatar: React.FC<{src: string | null; name: string; size: number; ring?: boolean; i?: number}> = ({src, name, size, ring, i = 0}) => {
  const inner = src ? <Img src={staticFile(src)} style={{width: '100%', height: '100%', objectFit: 'cover'}} />
    : <div style={{width: '100%', height: '100%', display: 'grid', placeItems: 'center', background: TILE_BG[i % TILE_BG.length], ...ui(700, size * 0.42, '#fff', 1)}}>
      {name.replace(/^@/, '').slice(0, 1).toUpperCase()}</div>;
  return ring ? (
    <div style={{width: size, height: size, borderRadius: size / 2, background: IgGradient, padding: size * 0.045, boxSizing: 'border-box', flex: 'none'}}>
      <div style={{width: '100%', height: '100%', borderRadius: '50%', overflow: 'hidden', border: `${size * 0.035}px solid #fff`, boxSizing: 'border-box'}}>{inner}</div>
    </div>
  ) : <div style={{width: size, height: size, borderRadius: size / 2, overflow: 'hidden', flex: 'none'}}>{inner}</div>;
};

const Verified: React.FC<{size: number}> = ({size}) => <Ph.SealCheck size={size} weight="fill" color={IG_BLUE} />;

const igProfileAnchors = (st: St): Record<string, Rect> => {
  const a: Record<string, Rect> = {
    header: {x: 0, y: 56, w: PW, h: 50}, avatar: {x: 16, y: 116, w: 96, h: 96}, stats: {x: 128, y: 120, w: 290, h: 72},
    posts: {x: 128, y: 120, w: 96, h: 72}, followers: {x: 224, y: 120, w: 100, h: 72}, following: {x: 324, y: 120, w: 96, h: 72},
    bio: {x: 16, y: 218, w: 400, h: 118}, button: {x: 16, y: 346, w: 196, h: 38}, grid: {x: 0, y: 452, w: PW, h: 480},
    profile: {x: 0, y: 56, w: PW, h: 330},
  };
  for (let i = 0; i < 9; i++) a[`tile${i}`] = {x: (i % 3) * 144, y: 452 + Math.floor(i / 3) * 192, w: 142, h: 190};
  return a;
};

const IgProfile: React.FC<{st: St; a: Record<string, Rect>}> = ({st, a}) => {
  const d = st.d, p = st.pal, t = st.t;
  const handle = txt(d.handle) || 'yourbrand';
  const followT = d.follow ? T(d.follow, 1e9) : 1e9;
  const followed = t >= followT;
  const fk = ease(t, followT, 0.3);
  const stat = (v: any, fb: string) => {
    if (v == null) return fb;
    const n = countAt(v, t, 0);
    return isFinite(n) ? (typeof v === 'object' ? fmtIG(n) : (typeof v === 'number' ? fmtIG(v) : txt(v))) : txt(v);
  };
  const bio: string[] = String(txt(d.bio) || '').split('\n').filter(Boolean).slice(0, 3);
  const grid: any[] = d.grid ?? [];
  const glow = (key: string) => {
    const v = d[key];
    if (!v || typeof v !== 'object' || typeof v.atT !== 'number') return 0;
    const k = ease(t, v.atT, 0.3) * (1 - ease(t, v.atT + 1.6, 0.6));
    return k;
  };
  const own = Boolean(d.own);
  return (
    <>
      <div style={{position: 'absolute', left: 0, top: 54, width: PW, height: 52, display: 'flex', alignItems: 'center', padding: '0 16px', gap: 10}}>
        {own ? null : <Ph.CaretLeft size={28} weight="bold" color={p.ink} />}
        <span style={{...ui(700, own ? 24 : 21, p.ink), flex: own ? undefined : 1, textAlign: own ? 'left' : 'center', display: 'flex', alignItems: 'center',
          justifyContent: own ? 'flex-start' : 'center', gap: 6}}>
          {own ? <Ph.LockSimple size={18} weight="bold" color={p.ink} /> : null}{handle}{d.verified ? <Verified size={18} /> : null}
          {own ? <Ph.CaretDown size={16} weight="bold" color={p.ink} /> : null}
        </span>
        {own ? <div style={{marginLeft: 'auto', display: 'flex', gap: 22}}><Ph.At size={28} color={p.ink} /><Ph.PlusSquare size={28} color={p.ink} /><Ph.List size={28} color={p.ink} /></div>
          : <Ph.DotsThree size={28} weight="bold" color={p.ink} />}
      </div>
      <div style={abs(a.avatar)}><Avatar src={file(d.avatar)} name={handle} size={96} ring={d.story !== false} /></div>
      {([['posts', 'posts'], ['followers', 'followers'], ['following', 'following']] as const).map(([k, label]) => {
        const r = a[k];
        const g = glow(k);
        return (
          <div key={k} style={{...abs(r), display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', borderRadius: 14,
            background: g > 0 ? rgba(st.acc, 0.16 * g) : undefined, boxShadow: g > 0 ? `inset 0 0 0 ${2.5 * g}px ${st.acc}` : undefined}}>
            <span style={ui(700, 22, p.ink, 1.1)}>{stat(d[k], k === 'posts' ? '128' : k === 'followers' ? '12.4K' : '310')}</span>
            <span style={ui(400, 16, p.ink, 1.3)}>{label}</span>
          </div>
        );
      })}
      <div style={{...abs(a.bio), display: 'flex', flexDirection: 'column', gap: 3}}>
        <span style={ui(600, 17, p.ink)}>{txt(d.name) || handle}</span>
        {txt(d.category) ? <span style={ui(400, 15, p.mut)}>{txt(d.category)}</span> : null}
        {bio.map((l, i) => <span key={i} style={{...ui(400, 16, p.ink, 1.3), whiteSpace: 'nowrap', overflow: 'hidden'}}>{l}</span>)}
        {txt(d.link) ? <span style={{...ui(600, 16, st.dark ? '#E0F1FF' : '#00376B'), display: 'flex', alignItems: 'center', gap: 4}}>
          <Ph.Link size={15} weight="bold" />{txt(d.link)}</span> : null}
      </div>
      <div style={{position: 'absolute', left: 16, top: 346, width: PW - 32, height: 38, display: 'flex', gap: 8}}>
        {own ? (
          <>
            <div style={{flex: 1, borderRadius: 10, background: p.bubble, display: 'grid', placeItems: 'center', ...ui(600, 16, p.ink)}}>Edit profile</div>
            <div style={{flex: 1, borderRadius: 10, background: p.bubble, display: 'grid', placeItems: 'center', ...ui(600, 16, p.ink)}}>Share profile</div>
          </>
        ) : (
          <>
            <div style={{flex: 1, borderRadius: 10, background: followed ? p.bubble : IG_BLUE, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
              transform: `scale(${followed ? 0.96 + 0.04 * fk : 1})`, ...ui(600, 16, followed ? p.ink : '#fff')}}>
              {followed ? <>Following<Ph.CaretDown size={14} weight="bold" /></> : txt(d.button) || 'Follow'}
            </div>
            <div style={{flex: 1, borderRadius: 10, background: p.bubble, display: 'grid', placeItems: 'center', ...ui(600, 16, p.ink)}}>Message</div>
            <div style={{width: 38, borderRadius: 10, background: p.bubble, display: 'grid', placeItems: 'center'}}><Ph.UserPlus size={18} weight="bold" color={p.ink} /></div>
          </>
        )}
      </div>
      <div style={{position: 'absolute', left: 0, top: 404, width: PW, height: 46, display: 'flex', borderBottom: `1px solid ${p.line}`}}>
        {[Ph.SquaresFour, Ph.FilmSlate, Ph.UserSquare].map((I, i) => (
          <div key={i} style={{flex: 1, display: 'grid', placeItems: 'center', borderBottom: i === 0 ? `1.5px solid ${p.ink}` : undefined}}>
            <I size={26} weight={i === 0 ? 'fill' : 'regular'} color={i === 0 ? p.ink : p.mut} /></div>
        ))}
      </div>
      {Array.from({length: 9}).map((_, i) => {
        const g = grid[i];
        const r = a[`tile${i}`];
        const k = g && typeof g === 'object' && typeof g.atT === 'number' ? ease(t, g.atT, 0.4, POP) : 1;
        const src = file(g);
        return (
          <div key={i} style={{...abs(r), overflow: 'hidden', background: src ? '#ddd' : TILE_BG[(i * 4) % TILE_BG.length],
            opacity: Math.min(1, k * 1.2), transform: `scale(${0.85 + 0.15 * k})`}}>
            {src ? <Img src={staticFile(src)} style={{width: '100%', height: '100%', objectFit: 'cover'}} /> : null}
            {txt(g?.views) ? <span style={{position: 'absolute', left: 8, bottom: 6, display: 'flex', alignItems: 'center', gap: 4, ...ui(600, 15, '#fff'),
              textShadow: '0 1px 4px rgba(0,0,0,0.5)'}}><Ph.Play size={14} weight="fill" />{txt(g.views)}</span> : null}
          </div>
        );
      })}
    </>
  );
};

const igInsightsAnchors = (st: St): Record<string, Rect> => {
  const rows: any[] = st.d.rows ?? [];
  const a: Record<string, Rect> = {
    header: {x: 0, y: 56, w: PW, h: 50}, period: {x: 16, y: 112, w: PW - 32, h: 40}, metric: {x: 16, y: 166, w: PW - 32, h: 90},
    value: {x: 16, y: 190, w: 300, h: 60}, chart: {x: 16, y: 270, w: PW - 32, h: 210}, rows: {x: 16, y: 500, w: PW - 32, h: Math.max(64, rows.length * 64)},
  };
  rows.forEach((_, i) => { a[`row${i}`] = {x: 16, y: 500 + i * 64, w: PW - 32, h: 64}; });
  return a;
};

const IgInsights: React.FC<{st: St; a: Record<string, Rect>}> = ({st, a}) => {
  const d = st.d, p = st.pal, t = st.t;
  const m = d.metric ?? {label: 'Views', value: 0};
  const mT = T(m, 0.2);
  const val = countAt(m.start != null ? m : {start: 0, to: m.value ?? m.to, atT: mT}, t, mT);
  const delta = m.delta ? (typeof m.delta === 'object' ? m.delta : {text: m.delta}) : null;
  const dT = delta ? T(delta, mT + 1.1) : 1e9;
  const dk = ease(t, dT, 0.4, POP);
  const bad = delta?.tone === 'bad' || /^-/.test(txt(delta));
  const ch = d.chart ?? {};
  const vals: number[] = (ch.values ?? [3, 4, 3.5, 5, 6, 5.5, 8, 9, 12, 15, 21, 30]).map(Number);
  const cT = T(ch, mT);
  const ck = ease(t, cT, 1.6);
  const r = a.chart;
  const mx = Math.max(...vals), mn = Math.min(0, ...vals);
  const pts = vals.map((v, i) => ({x: r.x + 10 + (i / (vals.length - 1)) * (r.w - 20), y: r.y + r.h - 30 - ((v - mn) / (mx - mn || 1)) * (r.h - 50)}));
  const shown = Math.max(1, ck * (pts.length - 1));
  const cut = pts.slice(0, Math.floor(shown) + 1);
  const fr = shown - Math.floor(shown);
  if (Math.floor(shown) < pts.length - 1) {
    const p0 = pts[Math.floor(shown)], p1 = pts[Math.floor(shown) + 1];
    cut.push({x: p0.x + (p1.x - p0.x) * fr, y: p0.y + (p1.y - p0.y) * fr});
  }
  const line = cut.map((q, i) => `${i ? 'L' : 'M'}${q.x - r.x},${q.y - r.y}`).join(' ');
  const area = `${line} L${cut[cut.length - 1].x - r.x},${r.h - 30} L${cut[0].x - r.x},${r.h - 30} Z`;
  const tip = cut[cut.length - 1];
  const rows: any[] = d.rows ?? [];
  return (
    <>
      <div style={{position: 'absolute', left: 0, top: 54, width: PW, height: 52, display: 'flex', alignItems: 'center', padding: '0 16px'}}>
        <Ph.CaretLeft size={28} weight="bold" color={p.ink} />
        <span style={{...ui(700, 21, p.ink), flex: 1, textAlign: 'center', marginRight: 28}}>{txt(d.title) || 'Insights'}</span>
      </div>
      <div style={{...abs(a.period), display: 'flex', alignItems: 'center', justifyContent: 'space-between'}}>
        <span style={{padding: '8px 14px', borderRadius: 10, background: p.bubble, display: 'flex', alignItems: 'center', gap: 6, ...ui(600, 15, p.ink)}}>
          {txt(d.period) || 'Last 30 days'}<Ph.CaretDown size={13} weight="bold" /></span>
        <span style={ui(400, 15, p.mut)}>{txt(d.dates) || 'Oct 15 – Nov 13'}</span>
      </div>
      <div style={abs(a.metric)}>
        <div style={ui(500, 17, p.mut)}>{txt(m.label) || 'Views'}</div>
        <div style={{display: 'flex', alignItems: 'center', gap: 12, marginTop: 4}}>
          <span style={ui(700, 46, p.ink, 1.1)}>{isFinite(val) ? fmtNum(val, m.value ?? m.to) : txt(m.value)}</span>
          {delta && dk > 0 ? (
            <span style={{padding: '5px 12px', borderRadius: 999, background: bad ? rgba(RED, 0.14) : 'rgba(0,186,124,0.14)', display: 'flex', alignItems: 'center', gap: 4,
              transform: `scale(${dk})`, ...ui(700, 17, bad ? RED : '#00A86B')}}>
              {bad ? <Ph.ArrowDownRight size={16} weight="bold" /> : <Ph.ArrowUpRight size={16} weight="bold" />}{txt(delta).replace(/^[+-]/, (s) => (bad ? '' : s))}
            </span>
          ) : null}
        </div>
      </div>
      <div style={abs(r)}>
        {[0, 1, 2, 3].map((i) => <div key={i} style={{position: 'absolute', left: 0, right: 0, top: 20 + i * ((r.h - 50) / 3), borderTop: `1px dashed ${p.line}`}} />)}
        <svg width={r.w} height={r.h} style={{position: 'absolute', left: 0, top: 0, overflow: 'visible'}}>
          <defs>
            <linearGradient id="igl" x1="0" x2="1"><stop offset="0" stopColor="#833AB4" /><stop offset="0.6" stopColor="#E1306C" /><stop offset="1" stopColor="#F77737" /></linearGradient>
            <linearGradient id="iga" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stopColor="#E1306C" stopOpacity="0.28" /><stop offset="1" stopColor="#E1306C" stopOpacity="0" /></linearGradient>
          </defs>
          <path d={area} fill="url(#iga)" />
          <path d={line} fill="none" stroke="url(#igl)" strokeWidth={5} strokeLinecap="round" strokeLinejoin="round" />
          {ck > 0 ? <circle cx={tip.x - r.x} cy={tip.y - r.y} r={8} fill="#E1306C" stroke="#fff" strokeWidth={3} /> : null}
        </svg>
        {(ch.x ?? []).length ? (
          <div style={{position: 'absolute', left: 10, right: 10, bottom: 0, display: 'flex', justifyContent: 'space-between', ...ui(400, 14, p.mut)}}>
            {(ch.x as any[]).map((s, i) => <span key={i}>{txt(s)}</span>)}</div>
        ) : null}
      </div>
      {rows.map((row, i) => {
        const rr = a[`row${i}`];
        const k = typeof row?.atT === 'number' ? ease(t, row.atT, 0.4) : 1;
        const v = countAt(typeof row?.value === 'object' ? row.value : {start: 0, to: row?.value, atT: typeof row?.atT === 'number' ? row.atT : 0}, t);
        const rbad = row?.tone === 'bad' || /^-/.test(txt(row?.delta));
        return (
          <div key={i} style={{...abs(rr), display: 'flex', alignItems: 'center', borderBottom: `1px solid ${p.line}`, opacity: k, transform: `translateY(${(1 - k) * 14}px)`}}>
            <span style={{...ui(500, 18, p.ink), flex: 1}}>{txt(row?.label)}</span>
            <span style={ui(700, 18, p.ink)}>{isFinite(v) && row?.value != null && isFinite(Number(String(row.value).replace(/[,$]/g, ''))) ? fmtNum(v, row.value) : txt(row?.value)}</span>
            {txt(row?.delta) ? <span style={{marginLeft: 10, ...ui(700, 15, rbad ? RED : '#00A86B')}}>{txt(row.delta)}</span> : null}
          </div>
        );
      })}
    </>
  );
};

const INBOX_TOP = 206, ROW = 80;
const igInboxAnchors = (st: St): Record<string, Rect> => {
  const n = Math.min(8, (st.d.threads ?? []).length);
  const a: Record<string, Rect> = {
    header: {x: 0, y: 56, w: PW, h: 50}, search: {x: 16, y: 110, w: PW - 32, h: 40}, requests: {x: 250, y: 160, w: 164, h: 36},
    list: {x: 0, y: INBOX_TOP, w: PW, h: Math.max(ROW, n * ROW)}, input: {x: 16, y: 860, w: PW - 32, h: 48},
  };
  for (let i = 0; i < 8; i++) a[`row${i}`] = {x: 0, y: INBOX_TOP + i * ROW, w: PW, h: ROW};
  return a;
};

const IgInbox: React.FC<{st: St; a: Record<string, Rect>}> = ({st, a}) => {
  const d = st.d, p = st.pal, t = st.t;
  const list = arrivals(d.threads ?? [], t).slice(0, 8);
  const req = d.requests != null ? countAt(d.requests, t) : NaN;
  return (
    <>
      <div style={{position: 'absolute', left: 0, top: 54, width: PW, height: 52, display: 'flex', alignItems: 'center', padding: '0 16px', gap: 10}}>
        <Ph.CaretLeft size={28} weight="bold" color={p.ink} />
        <span style={{...ui(700, 22, p.ink), display: 'flex', alignItems: 'center', gap: 6}}>{txt(d.handle) || 'yourbrand'}<Ph.CaretDown size={15} weight="bold" /></span>
        <Ph.PencilSimpleLine size={28} color={p.ink} style={{marginLeft: 'auto'}} />
      </div>
      <div style={{...abs(a.search), borderRadius: 12, background: p.bubble, display: 'flex', alignItems: 'center', gap: 10, paddingLeft: 14}}>
        <Ph.MagnifyingGlass size={20} color={p.mut} /><span style={ui(400, 17, p.mut)}>Search</span>
      </div>
      <span style={{position: 'absolute', left: 16, top: 166, ...ui(700, 18, p.ink)}}>Messages</span>
      <span style={{position: 'absolute', right: 16, top: 166, ...ui(600, 17, IG_BLUE)}}>
        {isFinite(req) ? `Requests (${fmtIG(req)})` : 'Requests'}</span>
      {list.map((x, idx) => {
        const r = x.r ?? {};
        const y = INBOX_TOP + slotY(list, idx, ROW);
        const unread = r.unread !== false && x.T >= 0;
        const fresh = x.T >= 0 ? ease(t, x.T, 0.25) * (1 - ease(t, x.T + 1.2, 0.8)) : 0;
        return (
          <div key={x.i} style={{position: 'absolute', left: 0, top: y, width: PW, height: ROW, display: 'flex', alignItems: 'center', gap: 14, padding: '0 16px',
            boxSizing: 'border-box', opacity: x.k, transform: `translateX(${(1 - x.k) * -30}px)`, background: fresh > 0 ? rgba(st.acc, 0.1 * fresh) : undefined}}>
            <Avatar src={file(r.avatar)} name={txt(r.name) || '?'} size={58} i={x.i + 2} />
            <div style={{flex: 1, minWidth: 0}}>
              <div style={{...ui(unread ? 700 : 500, 17, p.ink), whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'}}>{txt(r.name)}</div>
              <div style={{...ui(unread ? 600 : 400, 15, unread ? p.ink : p.mut), whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'}}>
                {txt(r.text)}<span style={{color: p.mut, fontWeight: 400}}>{` · ${txt(r.time) || (x.T >= 0 ? 'now' : '2h')}`}</span>
              </div>
            </div>
            {unread ? <div style={{width: 10, height: 10, borderRadius: 5, background: IG_BLUE, flex: 'none'}} /> : <Ph.Camera size={26} color={p.mut} />}
          </div>
        );
      })}
    </>
  );
};

const instagram: Skin = {
  menuFrom: 'header',
  frame: 'phone',
  size: {w: PW, h: PH},
  pal: IG_PAL,
  maxZoom: 2.6,
  anchors: (st) => {
    const sc = st.d.screen ?? 'profile';
    const a = sc === 'insights' ? igInsightsAnchors(st) : sc === 'inbox' ? igInboxAnchors(st) : igProfileAnchors(st);
    if (sc === 'profile' && st.d.follow) (a as any).__taps = [{x: a.button.x + a.button.w / 2, y: a.button.y + a.button.h / 2, T: T(st.d.follow, 1e9), click: true}];
    return a;
  },
  base: (st) => {
    const sc = st.d.screen ?? 'profile';
    return sc === 'inbox' ? {x: PW / 2, y: 370, s: 2.05} : sc === 'insights' ? {x: PW / 2, y: 392, s: 1.9} : {x: PW / 2, y: 262, s: 2.15};
  },
  Body: ({st, a}) => {
    const sc = st.d.screen ?? 'profile';
    return sc === 'insights' ? <IgInsights st={st} a={a} /> : sc === 'inbox' ? <IgInbox st={st} a={a} /> : <IgProfile st={st} a={a} />;
  },
};

// ------------------------------------------------------------------ iPhone zaključan ekran (notifikacije)
const LOCK_PAL: {light: Pal; dark: Pal} = {
  light: {bg: '#1B2140', rail: '#1B2140', card: 'rgba(245,245,247,0.86)', line: 'rgba(0,0,0,0.08)', ink: '#111', mut: '#5E5E66', bubble: '#E9E9EE', menu: '#FFF'},
  dark: {bg: '#0B0B10', rail: '#0B0B10', card: 'rgba(40,40,46,0.86)', line: 'rgba(255,255,255,0.08)', ink: '#F5F5F7', mut: '#A1A1AA', bubble: '#2C2C30', menu: '#2C2C30'},
};
const N_TOP = 318, N_GAP = 10;
const noteH = (n: any) => (txt(n?.body).length > 44 ? 112 : 92);

const iphone: Skin = {
  menuFrom: 'clock',
  frame: 'phone',
  size: {w: PW, h: PH},
  pal: LOCK_PAL,
  maxZoom: 2.6,
  anchors: (st) => {
    const a: Record<string, Rect> = {clock: {x: 0, y: 80, w: PW, h: 190}, list: {x: 10, y: N_TOP, w: PW - 20, h: 470}};
    for (let i = 0; i < 5; i++) a[`n${i}`] = {x: 10, y: N_TOP + i * (100 + N_GAP), w: PW - 20, h: 100};
    a.top = {x: 0, y: 60, w: PW, h: 520};
    return a;
  },
  base: () => ({x: PW / 2, y: 366, s: 1.82}),
  Body: ({st}) => {
    const d = st.d, t = st.t;
    const glass = st.dark ? LOCK_PAL.dark : LOCK_PAL.light;
    const list = arrivals(d.notifications ?? [], t).slice(0, 6);
    const wall = txt(d.wallpaper) || `radial-gradient(120% 70% at 20% 10%, ${rgba(st.acc, 0.55)} 0%, transparent 55%), radial-gradient(90% 60% at 90% 80%, #5B3CC4 0%, transparent 60%), linear-gradient(180deg, #141833 0%, #0C0E1F 100%)`;
    let y = N_TOP;
    return (
      <>
        <div style={{position: 'absolute', inset: 0, background: wall}} />
        <div style={{position: 'absolute', left: 0, top: 62, width: PW, display: 'flex', justifyContent: 'center'}}><Ph.LockSimple size={22} weight="fill" color="rgba(255,255,255,0.9)" /></div>
        <div style={{position: 'absolute', left: 0, top: 96, width: PW, textAlign: 'center', ...ui(600, 22, 'rgba(255,255,255,0.92)')}}>{txt(d.date) || 'Friday, November 14'}</div>
        <div style={{position: 'absolute', left: 0, top: 118, width: PW, textAlign: 'center', ...ui(600, 108, 'rgba(255,255,255,0.95)', 1), letterSpacing: '-0.02em'}}>
          {txt(d.time) || '9:41'}</div>
        {list.map((x, idx) => {
          const n = x.r ?? {};
          const h = noteH(n);
          const top = y;
          y += (h + N_GAP) * x.k;
          const drop = (1 - x.k) * -40;
          return (
            <div key={x.i} style={{position: 'absolute', left: 10, top: top + drop, width: PW - 20, height: h, borderRadius: 24, background: glass.card,
              boxShadow: '0 10px 30px rgba(0,0,0,0.25)', opacity: x.k * (idx > 3 ? Math.max(0, 1 - (idx - 3) * 0.5) : 1),
              transform: `scale(${0.94 + 0.06 * x.k})`, display: 'flex', gap: 12, padding: '14px 14px', boxSizing: 'border-box'}}>
              <AppIcon app={txt(n.app) || 'messages'} size={42} />
              <div style={{flex: 1, minWidth: 0}}>
                <div style={{display: 'flex', alignItems: 'baseline', gap: 8}}>
                  <span style={{...ui(700, 17, glass.ink), flex: 1, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'}}>{txt(n.title)}</span>
                  <span style={ui(400, 14, glass.mut)}>{txt(n.time) || (x.T >= 0 ? 'now' : '2m ago')}</span>
                </div>
                <div style={{...ui(400, 16, glass.ink, 1.3), display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden'}}>{txt(n.body)}</div>
              </div>
            </div>
          );
        })}
        <div style={{position: 'absolute', left: 44, top: 836, width: 54, height: 54, borderRadius: 27, background: 'rgba(255,255,255,0.18)', display: 'grid', placeItems: 'center'}}>
          <Ph.Flashlight size={26} weight="fill" color="#fff" /></div>
        <div style={{position: 'absolute', right: 44, top: 836, width: 54, height: 54, borderRadius: 27, background: 'rgba(255,255,255,0.18)', display: 'grid', placeItems: 'center'}}>
          <Ph.Camera size={26} weight="fill" color="#fff" /></div>
      </>
    );
  },
};

export const PHONE_SKINS: Record<string, Skin> = {instagram, iphone};
export {Caret};
