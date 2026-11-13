import React, {createContext, useContext} from 'react';
import {Easing, Img, OffthreadVideo, Sequence, interpolate, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {Camera, Check, Heart, User, Video} from 'lucide-react';
import * as Ph from '@phosphor-icons/react';
import {CAPTION_FONT, useFontSpec} from '../style';

/**
 * Split Screen — gornja polovina (PLAN.md §11; pravila: skills/ccc-edit/formats/split-screen.md).
 *
 * Montažna psihologija (iz CCC revizija):
 *  - hero otvaranje (prvi moment, dok traje hook) — najveći i najbogatiji vizual;
 *  - nešto novo na 1.5–3 s; delovi ulaze TAČNO na reč (`atT` = s od početka momenta), i sporedni natpisi;
 *  - vizual objašnjava, ne ponavlja; svaki grafički element čitljiv bez zvuka (skala, ose, zaključak);
 *  - ništa ne stoji "mrtvo": tekst dobija highlight koji se iscrtava ispod ključne reči;
 *  - najava = ceo oblik sa skrivenim sadržajem (zamućen), nikad fragment; budući koraci se ne vide;
 *  - liste rastu nadole (redosled čitanja), meko klizanje nagore; grupa se glatko re-centrira kad stigne nov deo;
 *  - glatke krive (ease-out), 50 fps, meki izlaz; vizual popunjava sigurnu zonu x 90–990, y 240–840.
 */
export type TopItem = {kind: string; start: number; end: number; data: Record<string, any>; src?: string; last?: string};
export type TopSpec = {style: 'dark' | 'light'; accent: string; items: TopItem[]};

const ZONE = {x: 90, y: 240, w: 900, h: 600};
/** Ikonice: Phosphor (MIT), težina Bold — čvršće i kvalitetnije od tankih linija (odluka 12. nov 2026). */
const ICONS: Record<string, React.FC<any>> = {
  clock: Ph.Clock, calendar: Ph.CalendarBlank, chart: Ph.ChartBar, trending: Ph.TrendUp, money: Ph.CurrencyDollar,
  users: Ph.Users, user: Ph.User, message: Ph.ChatCircle, mail: Ph.Envelope, target: Ph.Target, zap: Ph.Lightning,
  rocket: Ph.RocketLaunch, check: Ph.Check, x: Ph.X, eye: Ph.Eye, search: Ph.MagnifyingGlass, star: Ph.Star,
  heart: Ph.Heart, bot: Ph.Robot, phone: Ph.DeviceMobile, camera: Ph.Camera, video: Ph.VideoCamera, lock: Ph.Lock,
  gift: Ph.Gift, lightbulb: Ph.Lightbulb, megaphone: Ph.Megaphone, filter: Ph.Funnel, link: Ph.Link,
  sparkles: Ph.Sparkle, trophy: Ph.Trophy, instagram: Ph.InstagramLogo, send: Ph.PaperPlaneTilt, file: Ph.FileText,
  bell: Ph.Bell, handshake: Ph.Handshake, inbox: Ph.Tray, play: Ph.Play, comment: Ph.ChatTeardropText,
  crown: Ph.Crown, flame: Ph.Fire, ban: Ph.Prohibit, hourglass: Ph.Hourglass, shield: Ph.ShieldCheck,
  folder: Ph.Folder, question: Ph.Question,
};

const lum = (hex: string) => {
  const c = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255)
    .map((v) => (v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4));
  return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
};
const onAccent = (hex: string) => (1.05 / (lum(hex) + 0.05) >= 3 ? '#FFFFFF' : '#0A0A0B');
const rgba = (hex: string, a: number) =>
  `rgba(${parseInt(hex.slice(1, 3), 16)},${parseInt(hex.slice(3, 5), 16)},${parseInt(hex.slice(5, 7), 16)},${a})`;

type Theme = {
  dark: boolean; base: string; grid: string; ink: string; mut: string; glass: string; glassStrong: string;
  line: string; hi: string; shadow: string; orb: number; track: string;
};
const THEMES: Record<'dark' | 'light', Theme> = {
  dark: {
    dark: true, base: 'radial-gradient(900px 620px at 50% 52%, #222327 0%, #141518 55%, #0C0C0E 100%)',
    grid: 'rgba(255,255,255,0.05)', ink: '#FFFFFF', mut: 'rgba(255,255,255,0.62)',
    glass: 'rgba(255,255,255,0.065)', glassStrong: 'rgba(255,255,255,0.11)', line: 'rgba(255,255,255,0.18)',
    hi: 'rgba(255,255,255,0.28)', shadow: '0 30px 70px rgba(0,0,0,0.5)', orb: 0.075, track: 'rgba(255,255,255,0.12)',
  },
  light: {
    dark: false, base: 'radial-gradient(900px 620px at 50% 52%, #FAFAFB 0%, #EEEFF1 60%, #E4E5E8 100%)',
    grid: 'rgba(10,10,12,0.05)', ink: '#0A0A0B', mut: 'rgba(10,10,12,0.56)',
    glass: 'rgba(255,255,255,0.5)', glassStrong: 'rgba(255,255,255,0.72)', line: 'rgba(255,255,255,0.95)',
    hi: 'rgba(255,255,255,1)', shadow: '0 26px 60px rgba(20,20,30,0.14)', orb: 0.09, track: 'rgba(10,10,12,0.09)',
  },
};

/** Psihologija boja: loše = crveno, upozorenje = narandžasto, dobro = boja brenda. */
// Naglasak je UVEK boja brenda ili crvena za loše/rizik — nikad treća (žuta/narandžasta) boja
// (recenzija ai-actor-0 v2, s27): "warn" se crta bojom brenda.
const TONES: Record<string, string> = {bad: '#FF4D4D'};
const toneColor = (tone: string | undefined, acc: string) => (tone && TONES[tone]) || acc;

type Ctx = {t: number; dur: number; fps: number; th: Theme; acc: string; hero: boolean; sweep: boolean};
const C = createContext<Ctx>({t: 0, dur: 1, fps: 30, th: THEMES.dark, acc: '#FFE600', hero: false, sweep: false});
const useC = () => useContext(C);

// ------------------------------------------------------------------ kretanje
const EASE_OUT = Easing.bezier(0.16, 1, 0.3, 1);
const ease = (x: number, from: number, len: number, curve: (n: number) => number = EASE_OUT) =>
  interpolate(x - from, [0, len], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: curve});
const prog = (c: Ctx, at: number, len = 0.65) => ease(c.t, at, len);
/** Ulaz: fade + meko klizanje nagore + skidanje zamućenja (nikad pad spolja). */
/** Ulaz sa dubinom: blagi 3D nagib (rotateX) koji se ispravi dok element dolazi — ne ravan fade. */
const pop = (p: number, dy = 26): React.CSSProperties => ({
  opacity: interpolate(p, [0, 0.55], [0, 1], {extrapolateRight: 'clamp'}),
  transform: `perspective(1400px) translateY(${(1 - p) * dy}px) rotateX(${(1 - p) * 16}deg) scale(${0.94 + 0.06 * p})`,
  transformOrigin: '50% 100%',
  filter: p < 0.995 ? `blur(${(1 - p) * 8}px)` : undefined,
});
const at0 = (x: any, fallback = 0) => (typeof x?.atT === 'number' ? x.atT : fallback);
const txt = (x: any) => (typeof x === 'string' ? x : x?.text ?? x?.label ?? '');
/** Vreme pojave i-tog dela: `atT`, inače ravnomerno; prvi deo najkasnije 0.2 s (nikad prazno na početku). */
const beat = (c: Ctx, x: any, i: number, n: number) => {
  const t = typeof x?.atT === 'number' ? x.atT : n <= 1 ? 0 : (i * Math.min(c.dur * 0.55, 0.45 * (n - 1))) / (n - 1);
  return i === 0 ? Math.min(t, 0.2) : t;
};
const font = (w: number, size: number, lh = 1.15): React.CSSProperties =>
  ({fontFamily: CAPTION_FONT, fontWeight: w, fontSize: size, lineHeight: lh, letterSpacing: '-0.03em'});

/**
 * Auto-fit teksta (QA 0.8.0, P1-23): šabloni su birali veličinu po broju slova i `nowrap` — dugačko ime ili brojka
 * izlazila je iz kartice / preko susednog stubića. Širina se meri pravim fontom (canvas u Chrome-u koji renderuje),
 * pa se veličina smanji tačno toliko da stane (najmanje `min`). `ls` = letter-spacing u em (font(): -0.03).
 */
let MEASURE: CanvasRenderingContext2D | null = null;
const textW = (s: string, w: number, size: number, ls = -0.03) => {
  const str = String(s ?? '');
  if (!MEASURE && typeof document !== 'undefined') MEASURE = document.createElement('canvas').getContext('2d');
  if (!MEASURE) return str.length * size * 0.56;
  MEASURE.font = `${w} ${size}px "${CAPTION_FONT}", sans-serif`;
  return MEASURE.measureText(str).width + ls * size * str.length;
};
const fit = (s: string, w: number, size: number, maxW: number, min = Math.round(size * 0.5), ls = -0.03) => {
  const tw = textW(s, w, size, ls) * 1.04;  // 4% rezerve: subpikseli, kerning u stvarnom layout-u
  return tw <= maxW ? size : Math.max(min, Math.floor((size * maxW) / tw));
};
/** Koliko redova zauzima tekst koji se prelama u širini maxW (procena za visinu kartice). */
const lines = (s: string, w: number, size: number, maxW: number) => {
  let n = 1, cur = 0;
  const space = textW(' ', w, size);
  for (const word of String(s ?? '').split(/\s+/).filter(Boolean)) {
    const ww = textW(word, w, size);
    if (cur > 0 && cur + space + ww > maxW) { n += 1; cur = ww; } else cur += (cur > 0 ? space : 0) + ww;
  }
  return n;
};
/** Drži kutiju širine bw (centar x) u sigurnoj zoni po x. */
const clampY = (y: number, bh: number) =>
  bh >= ZONE.h ? ZONE.y + ZONE.h / 2 : Math.min(ZONE.y + ZONE.h - bh / 2, Math.max(ZONE.y + bh / 2, y));
const clampX = (x: number, bw: number) =>
  bw >= ZONE.w ? ZONE.x + ZONE.w / 2 : Math.min(ZONE.x + ZONE.w - bw / 2, Math.max(ZONE.x + bw / 2, x));

/**
 * Vertikalna grupa koja se glatko re-centrira: delovi (visina h, pojava at) zauzimaju mesto od početka,
 * a grupa je pomerena tako da je VIDLJIVI deo uvek na sredini zone — kad stigne nov deo, sve klizne gore.
 */
/**
 * `focus`: kontrola pažnje — kad stigne nov deo liste, prethodni se utišaju (manji opacity + tamnije),
 * pa oko gledaoca ide na najnoviji. Naslov/zaglavlje liste (`keep`) se ne utišava.
 */
const Stack: React.FC<{parts: {h: number; at: number; el: React.ReactNode; keep?: boolean}[]; gap?: number; focus?: boolean}> = ({
  parts, gap = 24, focus,
}) => {
  const c = useC();
  const total = parts.reduce((s, p) => s + p.h, 0) + gap * (parts.length - 1);
  const shown = parts.reduce((s, p, i) => s + (p.h + (i ? gap : 0)) * ease(c.t, p.at, 0.7), 0);
  return (
    <div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', gap,
      transform: `translateY(${(total - shown) / 2}px)`}}>
      {parts.map((p, i) => {
        const next = parts.slice(i + 1).find((q) => !q.keep);
        const dim = focus && !p.keep && next ? ease(c.t, next.at, 0.5) : 0;
        const base = pop(prog(c, p.at));
        return (
          <div key={i} style={{minHeight: p.h, display: 'flex', alignItems: 'center', justifyContent: 'center', ...base,
            opacity: (base.opacity as number) * (1 - 0.65 * dim),
            filter: [base.filter, dim > 0.01 ? `brightness(${1 - 0.45 * dim}) saturate(${1 - 0.5 * dim})` : ''].filter(Boolean).join(' ') || undefined}}>
            <AtCtx.Provider value={p.at}>{p.el}</AtCtx.Provider>
          </div>
        );
      })}
    </div>
  );
};

/** Kada je deo ušao (s od početka momenta) — Glass po tome pušta "light sweep". */
const AtCtx = createContext<number>(0);

const Glass: React.FC<{style?: React.CSSProperties; glow?: number; strong?: boolean; children?: React.ReactNode; r?: number; at?: number}> = ({
  style, glow = 0, strong, children, r = 36, at,
}) => {
  const c = useC();
  const {th, acc} = c;
  const t0 = at ?? useContext(AtCtx);
  // Light sweep: meki odsjaj jednom pređe preko stakla dok kartica ulazi — samo u momentima koje engine označi
  // (otvaranje + payoff momenti, razmak ≥ 12 s) i samo na glavnoj kartici (onoj koja ulazi prva), ne na svakom redu.
  const sw = c.sweep && t0 <= 0.3 ? ease(c.t, t0 + 0.12, 0.95, Easing.inOut(Easing.cubic)) : 0;
  return (
    <div style={{
      position: 'relative', borderRadius: r, overflow: 'hidden', boxSizing: 'border-box',
      background: strong ? th.glassStrong : th.glass, backdropFilter: 'blur(26px) saturate(150%)',
      WebkitBackdropFilter: 'blur(26px) saturate(150%)', border: `1.5px solid ${th.line}`,
      boxShadow: `${th.shadow}, inset 0 1.5px 0 ${th.hi}` + (glow ? `, 0 0 ${70 * glow}px ${rgba(acc, 0.42 * glow)}` : ''),
      ...style,
    }}>
      <div style={{position: 'absolute', inset: 0, pointerEvents: 'none',
        background: `linear-gradient(140deg, rgba(255,255,255,${th.dark ? 0.16 : 0.5}) 0%, rgba(255,255,255,0) 42%)`}} />
      {sw > 0 && sw < 1 ? (
        <div style={{position: 'absolute', top: 0, bottom: 0, left: 0, width: '60%', pointerEvents: 'none', zIndex: 3,
          transform: `translateX(${-120 + sw * 290}%) skewX(-18deg)`,
          background: `linear-gradient(90deg, rgba(255,255,255,0) 0%, rgba(255,255,255,${th.dark ? 0.13 : 0.55}) 50%, rgba(255,255,255,0) 100%)`}} />
      ) : null}
      <div style={{position: 'relative'}}>{children}</div>
    </div>
  );
};

/**
 * "Backlit" pločica (odluka 12. nov 2026: Bold · minimal): tamna grafitna pločica (i na Light podlozi), tanka svetla
 * ivica u boji na vrhu, jedva primetan sjaj; ikonica Phosphor Bold u boji (tona). Mikro-pokret: kad stigne (`at`),
 * ikonica blago "iskoči" (skala + mali zaokret) — živo, bez preterivanja.
 */
const NeonTile: React.FC<{name?: string; size?: number; tone?: string; at?: number; radius?: number; children?: React.ReactNode}> = ({
  name, size = 120, tone, at, radius,
  children,
}) => {
  const c = useC();
  const col = toneColor(tone, c.acc);
  const I = (name && ICONS[name]) || Ph.Sparkle;
  const t0 = at ?? useContext(AtCtx);
  const k = ease(c.t, t0 + 0.08, 0.7, Easing.bezier(0.34, 1.4, 0.64, 1));  // blagi "overshoot" za iskok
  return (
    <div style={{width: size, height: size, borderRadius: radius ?? size * 0.29, flex: 'none', display: 'grid', placeItems: 'center',
      background: 'linear-gradient(180deg, #26272C 0%, #141518 100%)', border: '1.5px solid rgba(255,255,255,0.07)',
      boxShadow: `inset 0 1px 0 ${rgba(col, 0.42)}, inset 0 0 ${size * 0.15}px ${rgba(col, 0.07)}, 0 ${size * 0.12}px ${size * 0.23}px rgba(0,0,0,${c.th.dark ? 0.35 : 0.22})`}}>
      <div style={{transform: `scale(${0.7 + 0.3 * k}) rotate(${(1 - Math.min(1, k)) * -10}deg)`, display: 'grid', placeItems: 'center',
        filter: `drop-shadow(0 0 ${size * 0.02}px ${rgba(col, 0.3)})`}}>
        {children ?? <I size={size * 0.54} color={col} weight="bold" />}
      </div>
    </div>
  );
};
const IconTile: React.FC<{name?: string; size?: number; on?: number; tone?: string; at?: number}> = ({name, size = 120, tone, at}) => (
  <NeonTile name={name} size={size} tone={tone} at={at} />
);

/** Čist highlight koji se iscrtava ispod ključne reči (sekundarni takt — tekst nikad ne stoji "mrtav"). */
const Highlight: React.FC<{children: React.ReactNode; at: number; size: number; tone?: string}> = ({children, at, size, tone}) => {
  const c = useC();
  const k = ease(c.t, at + 0.3, 0.6);
  const col = toneColor(tone, c.acc);
  return (
    <span style={{position: 'relative', display: 'inline-block', zIndex: 0}}>
      <span style={{position: 'absolute', left: -size * 0.06, right: -size * 0.06, bottom: size * 0.04, height: size * 0.3,
        borderRadius: size * 0.15, background: col, opacity: c.th.dark ? 0.9 : 0.85, zIndex: -1,
        transform: `scaleX(${k})`, transformOrigin: 'left center', boxShadow: `0 0 ${30 * k}px ${rgba(col, 0.55)}`}} />
      {children}
    </span>
  );
};

// ------------------------------------------------------------------ šabloni
const countUp = (v: string, k: number) => {
  // QA 0.8.0, P0: odbrojavanje je menjalo izgovorene brojeve ("Since 2019" → "Since 2,019", "4,2 Mio" → "42 Mio").
  // Pravila: na kraju animacije UVEK tačno tekst govornika; godine (1900–2099), decimalni zarez ("4,2") i tačke
  // kao hiljade ("1.000.000") ili verzije ("v1.2.3") se ne odbrojavaju uopšte.
  if (k >= 0.999) return v;
  if (/(^|[^0-9.,])(19|20)\d\d(?![0-9])/.test(v) || /\d,\d{1,2}(?!\d)/.test(v) || /\d\.\d+\.\d/.test(v)) return v;
  // Raspon ("3–4 hrs") ili više brojeva: bez odbrojavanja (međuvrednosti tipa "1–4" zbunjuju) — animaciju nosi vizual.
  const nums = v.match(/[0-9][0-9,.]*/g) || [];
  if (nums.length > 1) {
    if (!nums.every((x) => parseFloat(x.replace(/,/g, '')) >= 10)) return v;
    return v.replace(/[0-9][0-9,.]*/g, (x) => {
      const n = parseFloat(x.replace(/,/g, '')), dec = (x.split('.')[1] || '').length;
      return dec ? (n * k).toFixed(dec) : Math.round(n * k).toLocaleString('en-US');
    });
  }
  if (nums.length !== 1) return v;
  const m = v.match(/^([^0-9]*)([0-9][0-9,.]*)(.*)$/);
  if (!m) return v;
  const n = parseFloat(m[2].replace(/,/g, ''));
  const dec = (m[2].split('.')[1] || '').length;
  return m[1] + (dec ? (n * k).toFixed(dec) : Math.round(n * k).toLocaleString('en-US')) + m[3];
};

const Stat: React.FC<{d: any}> = ({d}) => {
  const c = useC();
  const at = d.atT ?? 0;
  const v = String(d.value);
  const size = Math.max(120, Math.min(190, Math.floor(1350 / Math.max(4, v.length))));
  const subAt = at0(d.sub, Math.min(0.8, c.dur * 0.45));
  // Nikad prazan kadar (recenzija ai-actor-0 v1, s15): kartica sa natpisom ulazi odmah, a broj se odbrojava na reč.
  const parts = [
    {h: size + (d.label ? 70 : 0) + (d.of ? 90 : 0) + 60, at: 0, el: (
      <Glass glow={0.5} style={{width: 880, padding: '42px 56px 46px', textAlign: 'center'}}>
        {d.label ? <div style={{...font(600, 44), color: c.th.mut}}>{d.label}</div> : null}
        <div style={{...font(800, size, 1), letterSpacing: '-0.05em', color: c.th.ink, marginTop: 12, fontVariantNumeric: 'tabular-nums',
          opacity: 0.25 + 0.75 * ease(c.t, at - 0.1, 0.35)}}>
          {countUp(v, ease(c.t, at, 1.1))}
        </div>
        {d.of ? (
          <div style={{marginTop: 30}}>
            <div style={{height: 18, borderRadius: 99, background: c.th.track, overflow: 'hidden'}}>
              <div style={{width: `${ease(c.t, at + 0.15, 1.2) * Math.max(2, d.ring ?? 50)}%`, height: '100%', borderRadius: 99,
                background: c.acc, boxShadow: `0 0 24px ${rgba(c.acc, 0.8)}`}} />
            </div>
            <div style={{display: 'flex', justifyContent: 'space-between', marginTop: 12, ...font(600, 32), color: c.th.mut}}>
              <span style={{color: c.th.ink}}>{v}</span><span>{d.of}</span>
            </div>
          </div>
        ) : null}
      </Glass>
    )},
  ];
  if (d.sub) parts.push({h: 76, at: subAt, el: (
    <div style={{...font(800, 46), background: toneColor(d.sub?.tone ?? d.tone, c.acc), color: onAccent(toneColor(d.sub?.tone ?? d.tone, c.acc)),
      padding: '12px 34px', borderRadius: 99, boxShadow: `0 0 34px ${rgba(toneColor(d.sub?.tone ?? d.tone, c.acc), 0.5)}`}}>{txt(d.sub)}</div>
  )});
  return <Stack parts={parts} gap={22} />;
};

/** Vreme: 7 dana, svaki dan dobija svoj blok jedan za drugim, ukupno se odbrojava — skala je odmah jasna. */
const Week: React.FC<{d: any}> = ({d}) => {
  const c = useC();
  const at = d.atT ?? 0;
  const days = ['M', 'T', 'W', 'T', 'F', 'S', 'S'].slice(0, Math.min(7, Math.max(3, d.days ?? 7)));
  const v = String(d.value);
  const fillEnd = at + 0.15 + days.length * 0.12 + 0.5;
  // Oblik (7 praznih dana) stoji od početka momenta; dani se pune tek kad krene broj (`at`).
  const parts = [{h: 470, at: 0, el: (
    <Glass glow={0.4} style={{width: 880, padding: '36px 46px 40px'}}>
      <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'baseline'}}>
        <div style={{...font(700, 40), color: c.th.mut}}>{d.label ?? 'per week'}</div>
        <div style={{...font(800, 76, 1), color: c.th.ink, letterSpacing: '-0.045em', fontVariantNumeric: 'tabular-nums'}}>
          {countUp(v, ease(c.t, at + 0.15, fillEnd - at))}
        </div>
      </div>
      <div style={{display: 'flex', justifyContent: 'space-between', marginTop: 30}}>
        {days.map((dd, i) => {
          const k = ease(c.t, at + 0.15 + i * 0.12, 0.6);
          return (
            <div key={i} style={{display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 14}}>
              <div style={{width: 92, height: 230, borderRadius: 22, background: c.th.track, position: 'relative', overflow: 'hidden',
                border: `1.5px solid ${c.th.line}`}}>
                <div style={{position: 'absolute', left: 10, right: 10, bottom: 10, height: 46 * k, borderRadius: 14,
                  background: c.acc, boxShadow: `0 0 22px ${rgba(c.acc, 0.7)}`}} />
              </div>
              <div style={{...font(700, 32), color: c.th.mut}}>{dd}</div>
            </div>
          );
        })}
      </div>
    </Glass>
  )}];
  if (d.per || d.sub) parts.push({h: 70, at: at0(d.sub, fillEnd - 0.2), el: (
    <div style={{...font(800, 42), background: c.acc, color: onAccent(c.acc), padding: '10px 30px', borderRadius: 99}}>
      {txt(d.sub) || d.per}
    </div>
  )});
  return <Stack parts={parts} gap={20} />;
};

/**
 * Framework (recenzija test-video-3 v1, s02/s07/s12/s18): kad video najavi N stvari, okvir se pokaže odmah — N pločica
 * sa skrivenim sadržajem ("?") — i ISTI okvir se vraća za svaki korak i na kraju (svi otkriveni).
 *   active = -1 → uvod: pločice ulaze jedna za drugom, imena skrivena; `total` ({text, at}) → pločice se spuste i
 *                 spoje zagradom u jednu celinu, a iznad njih se ispiše zajednička vrednost (npr. "20 min").
 *   active = n  → kraj: sve pločice otkrivene (imena + ✓), pale se redom — npr. "šablon sa sva 4 fajla".
 */
const Framework: React.FC<{d: any; done: boolean}> = ({d, done}) => {
  const c = useC();
  const items: any[] = d.items;
  const n = items.length;
  const tile = n >= 5 ? 128 : n === 4 ? 150 : 176;
  const pitch = Math.min(220, (ZONE.w - 20) / n);
  const rowW = pitch * n;
  const tot = d.total;
  const tt = tot ? at0(tot, Math.min(1.2, c.dur * 0.5)) : null;
  const join = tt === null ? 0 : ease(c.t, tt - 0.15, 0.8, CAM_GLIDE);
  const titleK = d.title ? prog(c, 0) : 0;
  // Razmak između elemenata je obavezan (recenzija v2, s02: "20 min" nabijeno uz naslov): naslov (0–60) → ≥ 40 px →
  // zajednička vrednost (96) → 24 px → zagrada (34) → pločice. Sa vrednošću red kreće niže da sve stane bez gužve.
  const GAP = 40;
  const top = tot ? 60 + GAP + 96 + 24 + 34 - 46 : 150;  // red pločica (y vrha) pre spajanja; spajanje ga spusti za 46 px
  const rowY = top + 46 * join;
  return (
    <div style={{width: ZONE.w, height: 520, position: 'relative'}}>
      {d.title ? <div style={{...pop(titleK), position: 'absolute', top: 6, left: 0, right: 0, textAlign: 'center',
        ...font(800, 50), color: c.th.ink}}>{txt(d.title)}</div> : null}
      {tot ? (
        <>
          {/* zagrada: vodoravna linija iznad pločica + kratke vertikale do svake, iscrtava se od sredine */}
          <div style={{position: 'absolute', left: (ZONE.w - rowW) / 2 + pitch / 2, width: (rowW - pitch) * join, top: rowY - 34,
            height: 6, borderRadius: 6, marginLeft: (rowW - pitch) * (1 - join) / 2, background: c.acc, boxShadow: `0 0 18px ${rgba(c.acc, 0.7)}`}} />
          {items.map((_, i) => (
            <div key={i} style={{position: 'absolute', left: (ZONE.w - rowW) / 2 + pitch * (i + 0.5) - 3, top: rowY - 34, width: 6,
              height: 34 * join, borderRadius: 6, background: c.acc, opacity: join}} />
          ))}
          <div style={{position: 'absolute', left: 0, right: 0, top: rowY - 34 - 96 - 24, display: 'flex', justifyContent: 'center',
            ...pop(ease(c.t, tt ?? 0, 0.6))}}>
            <div style={{...font(800, 62, 1), background: c.acc, color: onAccent(c.acc), padding: '16px 40px', borderRadius: 99,
              boxShadow: `0 0 40px ${rgba(c.acc, 0.55)}`, fontVariantNumeric: 'tabular-nums'}}>{countUp(txt(tot), ease(c.t, tt ?? 0, 0.9))}</div>
          </div>
        </>
      ) : null}
      {items.map((x, i) => {
        const tIn = done ? beat(c, x, i, n) : Math.min(0.15 + i * 0.16, c.dur * 0.4);
        const p = prog(c, tIn);
        const on = done ? ease(c.t, tIn + 0.1, 0.5) : 0;
        const base = pop(p, 30);
        return (
          <div key={i} style={{position: 'absolute', left: (ZONE.w - rowW) / 2 + pitch * i, width: pitch, top: rowY,
            display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 18, ...base}}>
            <div style={{position: 'relative'}}>
              <NeonTile name={d.icon ?? 'folder'} size={tile} at={tIn} />
              <div style={{position: 'absolute', right: -10, top: -10, width: 52, height: 52, borderRadius: 99, display: 'grid', placeItems: 'center',
                background: done ? c.acc : '#2A2B31', border: `2px solid ${done ? 'transparent' : 'rgba(255,255,255,0.12)'}`,
                transform: `scale(${done ? 0.6 + 0.4 * on : 1})`, boxShadow: done ? `0 0 20px ${rgba(c.acc, 0.6 * on)}` : undefined}}>
                {done ? <Check size={30} color={onAccent(c.acc)} strokeWidth={3} />
                  : <div style={{...font(800, 32, 1), color: c.th.mut}}>{i + 1}</div>}
              </div>
            </div>
            <div style={{...font(800, done ? (n >= 4 ? 34 : 40) : 52, 1.1), color: done ? c.th.ink : c.th.mut, textAlign: 'center',
              width: pitch - 12, opacity: done ? 0.4 + 0.6 * on : 0.7}}>
              {done ? txt(x) : '?'}
            </div>
          </div>
        );
      })}
    </div>
  );
};

/** Koraci: ceo oblik od početka, tekst trenutnog koraka zamućen dok ga ne izgovori; budući koraci se ne vide. */
const Steps: React.FC<{d: any}> = ({d}) => {
  const c = useC();
  const items: any[] = d.items;
  const n = items.length;
  if ((d.active ?? 0) < 0 || (d.active ?? 0) >= n) return <Framework d={d} done={(d.active ?? 0) >= n} />;
  const a = Math.min(n - 1, Math.max(0, d.active ?? 0));
  const at = at0(items[a], 0);
  const reveal = ease(c.t, at, 0.6);
  const label = txt(items[a]);
  return (
    <div style={{width: 900, display: 'flex', flexDirection: 'column', alignItems: 'center', ...pop(prog(c, 0))}}>
      <div style={{display: 'flex', alignItems: 'center', gap: 20, marginBottom: 26}}>
        <div style={{...font(800, 36), letterSpacing: '0.14em', color: c.th.mut}}>STEP {a + 1} / {n}</div>
        <div style={{display: 'flex', gap: 10}}>
          {items.map((_, i) => (
            <div key={i} style={{width: 80, height: 12, borderRadius: 99, overflow: 'hidden', background: c.th.track}}>
              <div style={{width: `${(i < a ? 1 : i === a ? reveal : 0) * 100}%`, height: '100%', background: c.acc,
                boxShadow: `0 0 14px ${rgba(c.acc, 0.8)}`}} />
            </div>
          ))}
        </div>
      </div>
      {a > 0 ? (
        <div style={{display: 'flex', gap: 12, marginBottom: 24, flexWrap: 'wrap', justifyContent: 'center'}}>
          {items.slice(0, a).map((x, i) => (
            <Glass key={i} r={99} style={{padding: '10px 24px 10px 14px'}}>
              <div style={{display: 'flex', alignItems: 'center', gap: 12, ...font(600, 32), color: c.th.mut}}>
                <span style={{width: 38, height: 38, borderRadius: 99, background: c.acc, display: 'grid', placeItems: 'center'}}>
                  <Check size={24} color={onAccent(c.acc)} strokeWidth={3} />
                </span>
                {txt(x)}
              </div>
            </Glass>
          ))}
        </div>
      ) : null}
      <Glass glow={0.3 + 0.7 * reveal} strong style={{width: 900, padding: '44px 46px', display: 'flex', alignItems: 'center'}}>
        <div style={{display: 'flex', alignItems: 'center', gap: 36}}>
          <NeonTile size={136} at={at}><div style={{...font(800, 76, 1), color: c.acc}}>{a + 1}</div></NeonTile>
          <div style={{...font(800, label.length > 24 ? 58 : 70, 1.08), color: c.th.ink, textAlign: 'left',
            filter: reveal < 0.995 ? `blur(${(1 - reveal) * 18}px)` : undefined, opacity: 0.35 + 0.65 * reveal}}>{label}</div>
        </div>
      </Glass>
    </div>
  );
};

/** Tok: čvor ulazi na reč, linija se iscrtava do njega; u hero verziji (otvaranje) čestice teku, rezultat "pukne". */
/**
 * Proces / uzrok → posledica. Raspored (`layout`) menja oblik da se isti flow ne ponavlja kroz video:
 * row (u redu), column (odozgo nadole, natpis desno), quad (kvadrant: dole → desno → gore), zigzag (gore-dole).
 */
const Flow: React.FC<{d: any}> = ({d}) => {
  const c = useC();
  const nodes: any[] = d.nodes;
  const n = nodes.length;
  const hero = c.hero || d.hero;
  const layout: string = ['column', 'quad', 'hub'].includes(d.layout) ? d.layout : 'row';  // zigzag (ukoso) izbačen — recenzija v2
  const H = 520, W = ZONE.w;
  const times = nodes.map((x, i) => beat(c, x, i, n));
  const titleH = d.title ? 70 : 0;
  // hub: čvor 0 (npr. logo alata) gore, ostali u redu ispod — sve linije idu IZ njega (recenzija test-video-3 v1, s03)
  const hub = layout === 'hub';
  // loop (samo quad): poslednji čvor se spaja sa prvim, tačke kruže stalno, u sredini natpis petlje (s16)
  const loopT = layout === 'quad' && d.loop ? at0(d.loop, Math.max(times[n - 1] + 0.6, c.dur * 0.6)) : null;
  const looped = loopT === null ? 0 : ease(c.t, loopT, 0.6);
  const edges: [number, number, number][] = hub
    ? nodes.slice(1).map((_, i) => [0, i + 1, times[i + 1]])
    : nodes.slice(1).map((_, i) => [i, i + 1, times[i + 1]]);
  if (loopT !== null) edges.push([n - 1, 0, loopT]);
  // centri pločica (x, y) i veličina pločice po rasporedu
  let tile: number, pts: {x: number; y: number}[];
  if (hub) {
    tile = n >= 4 ? 136 : 156;
    const kids = n - 1, pitch = W / kids;
    pts = nodes.map((_, i) => (i === 0 ? {x: W / 2, y: titleH + 96} : {x: pitch * (i - 0.5), y: titleH + 365}));
  } else if (layout === 'column') {
    tile = n >= 4 ? 104 : 124;
    const gap = (H - titleH) / n;
    pts = nodes.map((_, i) => ({x: W / 2 - 200, y: titleH + gap * (i + 0.5)}));
  } else if (layout === 'quad') {
    tile = hero ? 176 : 156;
    const cols = [W * 0.27, W * 0.27, W * 0.73, W * 0.73], rows = [titleH + 140, titleH + 395, titleH + 395, titleH + 140];
    pts = nodes.map((_, i) => ({x: cols[i], y: rows[i]}));
  } else if (layout === 'zigzag') {
    tile = n >= 4 ? 150 : 176;
    const pitch = W / n;
    pts = nodes.map((_, i) => ({x: pitch * (i + 0.5), y: titleH + (i % 2 ? 330 : 110)}));
  } else {
    tile = hero ? (n >= 3 ? 200 : 240) : n >= 4 ? 160 : 196;
    const pitch = W / n;
    pts = nodes.map((_, i) => ({x: pitch * (i + 0.5), y: (hero ? 150 : 120) + tile / 2}));
  }
  const labelSize = layout === 'column' ? 46 : hero ? 46 : n >= 4 || layout !== 'row' ? 36 : 40;
  return (
    <div style={{width: W, position: 'relative', height: H}}>
      {d.title ? <div style={{...pop(prog(c, 0)), position: 'absolute', top: 10, left: 0, right: 0, textAlign: 'center',
        ...font(700, 46), color: c.th.mut}}>{d.title}</div> : null}
      {edges.map(([ia, ib, te], i) => {
        const a = pts[ia], b = pts[ib];
        const dx = b.x - a.x, dy = b.y - a.y, len = Math.hypot(dx, dy), ang = Math.atan2(dy, dx);
        const pad = tile / 2 + 12, span = Math.max(0, len - pad * 2);
        const k = ease(c.t, te - 0.3, 0.55);
        const flowing = k >= 1;
        // petlja: kad se zatvori, tačke teku jedna za drugom kroz SVE ivice (krug), ne svaka za sebe
        const phase = loopT !== null && looped > 0.5 ? i / edges.length : 0;
        return (
          <div key={i} style={{position: 'absolute', left: a.x + Math.cos(ang) * pad, top: a.y + Math.sin(ang) * pad - 4,
            width: span * k, height: 8, borderRadius: 9, transformOrigin: '0 50%', transform: `rotate(${ang}rad)`,
            background: `linear-gradient(90deg, ${rgba(c.acc, 0.25)}, ${c.acc})`, boxShadow: `0 0 18px ${rgba(c.acc, 0.7)}`}}>
            {flowing ? (hero || looped > 0.5 ? [0, 0.33, 0.66] : [0]).map((o, j) => {
              const ph = Easing.inOut(Easing.sin)(((c.t * 0.75) + o + phase) % 1);
              return <div key={j} style={{position: 'absolute', top: -7, left: `calc(${ph * 100}% - 11px)`, width: 22, height: 22,
                borderRadius: 99, background: '#fff', boxShadow: `0 0 20px ${c.acc}`, opacity: Math.sin(ph * Math.PI)}} />;
            }) : null}
          </div>
        );
      })}
      {loopT !== null && d.center ? (
        // Unutar dijagrama BEZ iscrtanog highlight-a (recenzija v2, s16: gužva) — samo čist tekst sa vazduhom oko sebe;
        // highlight je za tekst koji je sam na ekranu (headline, naslov vesti).
        <div style={{position: 'absolute', left: pts[0].x + tile / 2 + 40, right: W - pts[n - 1].x + tile / 2 + 40,
          top: (pts[0].y + pts[1].y) / 2 - 70, height: 140, display: 'grid', placeItems: 'center', textAlign: 'center',
          ...pop(ease(c.t, at0(d.center, loopT), 0.6)), ...font(800, 44, 1.1), color: c.th.ink}}>
          {txt(d.center)}
        </div>
      ) : null}
      {nodes.map((x, i) => {
        const p = prog(c, times[i]);
        const last = i === n - 1;
        const burst = hero && last ? ease(c.t, times[i], 0.9) : 0;
        // kontrola pažnje: oko ide na najnoviji čvor (hub ostaje pun); kad se petlja zatvori, ceo sistem je opet pun
        const dim = last || (hub && i === 0) ? 0
          : (hub ? (i + 1 < n ? ease(c.t, times[i + 1], 0.5) * 0.5 : 0) : ease(c.t, times[i + 1], 0.5) * 0.5) * (1 - looped);
        const base = pop(p);
        const side = layout === 'column';
        const above = (layout === 'quad' && (i === 0 || i === 3)) || (hub && i === 0);  // gornji red: natpis IZNAD
        const pt = pts[i];
        if (hub && i === 0 && !txt(x)) {  // hub bez natpisa (logo govori sam) — samo pločica, veća
          return (
            <div key={i} style={{position: 'absolute', left: pt.x - tile * 0.65, top: pt.y - tile * 0.65, ...base}}>
              {x.src ? <LogoPlate f={x} size={tile * 1.3} /> : <IconTile name={x.icon} size={tile * 1.3} on={1} />}
            </div>
          );
        }
        return (
          <div key={i} style={{position: 'absolute', top: above ? undefined : pt.y - tile / 2, bottom: above ? H - (pt.y + tile / 2) : undefined,
            left: side ? pt.x - tile / 2 : pt.x - 140,
            width: side ? W - (pt.x - tile / 2) : 280, display: 'flex', flexDirection: side ? 'row' : above ? 'column-reverse' : 'column',
            alignItems: 'center', gap: side ? 30 : 0, ...base, opacity: (base.opacity as number) * (1 - dim),
            filter: [base.filter, dim > 0.01 ? `brightness(${1 - 0.5 * dim})` : ''].filter(Boolean).join(' ') || undefined}}>
            <div style={{position: 'relative', flex: 'none'}}>
              {burst > 0 && burst < 1 ? (
                <div style={{position: 'absolute', left: tile / 2, top: tile / 2, width: tile * (1 + burst * 1.2), height: tile * (1 + burst * 1.2),
                  transform: 'translate(-50%,-50%)', borderRadius: tile * 0.4, border: `4px solid ${c.acc}`, opacity: 1 - burst}} />
              ) : null}
              {x.src ? <LogoPlate f={x} size={tile} /> : <IconTile name={x.icon} size={tile} on={1} />}
            </div>
            <div style={{...font(800, labelSize, 1.1), color: c.th.ink, marginTop: side || above ? 0 : 20, marginBottom: above ? 18 : 0,
              textAlign: side ? 'left' : 'center',
              width: side ? undefined : 270}}>{txt(x)}</div>
          </div>
        );
      })}
    </div>
  );
};

/** Poređenje: levo se precrta, desno ulazi sa sjajem i ✓. */
const Versus: React.FC<{d: any}> = ({d}) => {
  const c = useC();
  const tl = at0(d.left, 0);
  const tr = at0(d.right, Math.min(1.0, c.dur * 0.45));
  // Recenzija test-video-3 v1 (s14): elementi u sigurnoj zoni (ne uz ivice), kartice blizu jedna drugoj, strelica
  // NASTAJE preko razmaka i preklapa obe kartice; bez linije precrtavanja (preko teksta u dva reda izgleda kao greška) —
  // "staro" se utiša i izgubi boju kad stigne "novo".
  const fade = ease(c.t, tr - 0.1, 0.55);
  const CW = 390, GAP = 60, CH = 400;
  const arrowK = ease(c.t, tr - 0.25, 0.7, Easing.bezier(0.34, 1.4, 0.64, 1));
  const card = (x: any, good: boolean, p: number) => (
    <Glass glow={good ? 0.9 : 0} strong={good} style={{...pop(p), width: CW, height: CH, padding: '36px 30px', boxSizing: 'border-box',
      display: 'flex', alignItems: 'center', justifyContent: 'center', textAlign: 'center',
      opacity: (pop(p).opacity as number) * (good ? 1 : 1 - fade * 0.5),
      filter: !good && fade > 0.01 ? `saturate(${1 - 0.8 * fade}) brightness(${1 - 0.3 * fade})` : undefined,
      transform: `${pop(p).transform} scale(${good ? 1 : 1 - 0.04 * fade})`}}>
      <div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 26}}>
        <NeonTile name={good ? 'check' : 'x'} size={104} radius={99} tone={good ? undefined : 'bad'} at={good ? tr : tl} />
        <div style={{...font(800, txt(x).length > 12 ? 56 : 64, 1.05), color: c.th.ink, maxWidth: CW - 60}}>{txt(x)}</div>
        {x.sub ? <div style={{...font(600, 34, 1.15), color: good ? c.acc : c.th.mut, maxWidth: CW - 60}}>{txt(x.sub)}</div> : null}
      </div>
    </Glass>
  );
  return (
    <div style={{display: 'flex', flexDirection: 'column', alignItems: 'center'}}>
      {d.title ? <div style={{...pop(prog(c, 0)), ...font(700, 46), color: c.th.mut, marginBottom: 26}}>{d.title}</div> : null}
      <div style={{position: 'relative', width: CW * 2 + GAP, display: 'flex', gap: GAP, alignItems: 'center'}}>
        {card(d.left, false, prog(c, tl))}
        {card(d.right, true, prog(c, tr))}
        <div style={{position: 'absolute', left: CW + GAP / 2 - 56, top: CH / 2 - 56, width: 112, height: 112, borderRadius: 99, zIndex: 4,
          display: 'grid', placeItems: 'center', background: c.acc, opacity: Math.min(1, arrowK * 2),
          transform: `scale(${arrowK}) translateX(${(1 - Math.min(1, arrowK)) * -40}px)`,
          boxShadow: `0 0 0 10px ${c.th.dark ? '#0B0D12' : '#F4F5F8'}, 0 0 40px ${rgba(c.acc, 0.6)}`}}>
          <Ph.ArrowRight size={60} color={onAccent(c.acc)} weight="bold" />
        </div>
      </div>
    </div>
  );
};

/** Grafikon sa kontekstom: šta se meri (ose), kroz šta (oznake), i zaključak na kraju. */
const Chart: React.FC<{d: any}> = ({d}) => {
  const c = useC();
  const bars: number[] = d.bars;
  const at = d.atT ?? 0;
  const mx = Math.max(...bars);
  const n = bars.length;
  const xs: string[] = d.x ?? [];
  const bw = Math.min(n <= 3 ? 130 : 104, Math.floor(560 / n));
  const cw = n <= 2 ? 600 : n === 3 ? 680 : n <= 5 ? 800 : 900;  // kompaktno kad je malo stubića — bez praznog prostora
  const grown = at + 0.1 + n * 0.1 + 0.4;
  const noteAt = at0(d.note, grown);
  const kn = ease(c.t, noteAt, 0.6);
  // Boja nosi emociju: pad = loše (crveno), osim ako plan kaže drugačije.
  const tone = d.tone ?? (bars[n - 1] < bars[0] ? 'bad' : undefined);
  const col = toneColor(tone, c.acc);
  const noteCol = toneColor(d.note?.tone ?? tone, c.acc);
  return (
    <Glass glow={0.35} style={{...pop(prog(c, at)), width: cw, padding: '34px 44px 30px'}}>
      <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', minHeight: 60, flexWrap: 'wrap', gap: '12px 20px'}}>
        <div style={{...font(700, 42), color: c.th.ink, textAlign: 'left'}}>{d.label ?? ''}</div>
        {d.note ? (
          <div style={{opacity: kn, transform: `translateY(${(1 - kn) * 14}px)`, ...font(800, 36), background: noteCol,
            color: onAccent(noteCol), padding: '8px 22px', borderRadius: 99, whiteSpace: 'nowrap',
            boxShadow: `0 0 26px ${rgba(noteCol, 0.5)}`}}>{txt(d.note)}</div>
        ) : null}
      </div>
      <div style={{display: 'flex', marginTop: 18}}>
        {d.y ? (
          <div style={{width: 46, display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
            <div style={{transform: 'rotate(-90deg)', whiteSpace: 'nowrap', ...font(600, 28), color: c.th.mut}}>{d.y} →</div>
          </div>
        ) : null}
        <div style={{flex: 1}}>
          <div style={{height: 300, display: 'flex', alignItems: 'flex-end', justifyContent: 'space-around',
            borderBottom: `2px solid ${c.th.line}`, borderLeft: d.y ? `2px solid ${c.th.line}` : undefined}}>
            {bars.map((b, i) => {
              const k = ease(c.t, at + 0.1 + i * 0.1, 0.8);
              const last = i === n - 1;
              return (
                <div key={i} style={{width: bw, height: Math.max(6, (b / mx) * 270 * k), borderRadius: '16px 16px 6px 6px',
                  background: last ? col : c.th.dark ? 'rgba(255,255,255,0.18)' : 'rgba(10,10,12,0.14)',
                  boxShadow: last ? `0 0 ${36 * k}px ${rgba(col, 0.7)}` : undefined}} />
              );
            })}
          </div>
          {xs.length ? (
            <div style={{display: 'flex', justifyContent: 'space-around', marginTop: 10}}>
              {bars.map((_, i) => <div key={i} style={{width: bw + 40, textAlign: 'center', ...font(600, 26), color: c.th.mut}}>{xs[i] ?? ''}</div>)}
            </div>
          ) : null}
        </div>
      </div>
    </Glass>
  );
};

/** Checklist: stavka se pojavljuje (i štiklira) tek kad se izgovori; lista raste nadole, grupa se re-centrira. */
const Checklist: React.FC<{d: any}> = ({d}) => {
  const c = useC();
  const items: any[] = d.items;
  const off = d.title ? 1 : 0;
  const times = items.map((x, i) => beat(c, x, i + off, items.length + off));
  const parts = [
    ...(d.title ? [{h: 60, at: 0, keep: true, el: <div style={{...font(700, 46), color: c.th.mut}}>{d.title}</div>}] : []),
    ...items.map((x, i) => {
      const k = ease(c.t, times[i] + 0.2, 0.45);
      return {h: 112, at: times[i], el: (
        <Glass glow={0.35 * k} strong style={{width: 860, padding: '22px 30px'}}>
          <div style={{display: 'flex', alignItems: 'center', gap: 28}}>
            <NeonTile name={x?.tone === 'bad' ? 'x' : 'check'} size={72} tone={x?.tone} at={times[i] + 0.15} />
            <div style={{...font(800, txt(x).length > 22 ? 48 : 56), color: c.th.ink}}>{txt(x)}</div>
          </div>
        </Glass>
      )};
    }),
  ];
  return <Stack parts={parts} gap={18} focus />;
};

/**
 * "Native to the platform": kad rekreiramo pravu aplikaciju, dizajn i boje odaju platformu bez loga.
 * Instagram DM — crna (svetla) podloga, sive primljene poruke, ljubičasto→plavi gradijent za poslate,
 * zaglavlje sa avatarom u story prstenu i "Active now", polje "Message…" sa plavom kamerom.
 */
const IG = {
  dark: {bg: '#000000', line: '#262626', recv: '#262626', ink: '#FFFFFF', mut: '#A8A8A8'},
  light: {bg: '#FFFFFF', line: '#DBDBDB', recv: '#EFEFEF', ink: '#000000', mut: '#737373'},
  sent: 'linear-gradient(135deg, #A033FF 0%, #5851DB 45%, #3797F0 100%)',
  ring: 'linear-gradient(45deg, #F58529, #DD2A7B 55%, #8134AF)',
  blue: '#3797F0',
};
const IgAvatar: React.FC<{size: number; ring?: boolean}> = ({size, ring}) => (
  <div style={{width: size, height: size, borderRadius: 99, padding: ring ? 4 : 0, background: ring ? IG.ring : undefined, flex: 'none', boxSizing: 'border-box'}}>
    <div style={{width: '100%', height: '100%', borderRadius: 99, border: ring ? '3px solid #000' : undefined, boxSizing: 'border-box',
      background: 'linear-gradient(135deg, #FFB86B, #FF5A8A 60%, #7A5CFF)'}} />
  </div>
);
const IgChat: React.FC<{d: any}> = ({d}) => {
  const c = useC();
  const P = c.th.dark ? IG.dark : IG.light;
  const msgs: any[] = d.messages;
  const times = msgs.map((x, i) => beat(c, x, i, msgs.length));
  return (
    <div style={{...pop(prog(c, 0)), width: 860, background: P.bg, borderRadius: 44, border: `1.5px solid ${P.line}`,
      overflow: 'hidden', boxShadow: c.th.shadow, fontFamily: CAPTION_FONT}}>
      <div style={{display: 'flex', alignItems: 'center', gap: 20, padding: '26px 30px', borderBottom: `1.5px solid ${P.line}`}}>
        <div style={{...font(500, 54, 1), color: P.ink}}>‹</div>
        <IgAvatar size={78} ring />
        <div style={{flex: 1}}>
          <div style={{...font(700, 38, 1.1), letterSpacing: '-0.01em', color: P.ink}}>{d.title ?? 'your.client'}</div>
          <div style={{...font(500, 28, 1.2), letterSpacing: 0, color: P.mut}}>Active now</div>
        </div>
        <Video size={46} color={P.ink} strokeWidth={2} />
      </div>
      <div style={{padding: '18px 30px 8px', minHeight: 150}}>
        {msgs.map((x, i) => {
          const you = x.from === 'you';
          const k = prog(c, times[i], 0.5);
          if (c.t < times[i]) return null;
          const dim = i < msgs.length - 1 && c.t >= times[i + 1] ? ease(c.t, times[i + 1], 0.5) * 0.45 : 0;
          return (
            <div key={i} style={{display: 'flex', justifyContent: you ? 'flex-end' : 'flex-start', alignItems: 'flex-end', gap: 14,
              marginTop: 16, ...pop(k, 16), opacity: Math.min(1, k * 1.8) * (1 - dim)}}>
              {!you ? <IgAvatar size={56} /> : null}
              <div style={{maxWidth: 620, padding: '22px 30px', borderRadius: 44, background: you ? IG.sent : P.recv,
                color: you ? '#FFFFFF' : P.ink, ...font(500, 42, 1.25), letterSpacing: '-0.01em'}}>{txt(x)}</div>
            </div>
          );
        })}
      </div>
      <div style={{margin: '14px 24px 24px', padding: '14px 18px', borderRadius: 99, border: `1.5px solid ${P.line}`,
        display: 'flex', alignItems: 'center', gap: 18}}>
        <div style={{width: 62, height: 62, borderRadius: 99, background: IG.blue, display: 'grid', placeItems: 'center'}}>
          <Camera size={34} color="#FFFFFF" strokeWidth={2.2} />
        </div>
        <div style={{...font(500, 34), letterSpacing: 0, color: P.mut}}>Message...</div>
      </div>
    </div>
  );
};

/** Instagram komentar (native): avatar, korisničko ime + vreme, tekst, "Reply", srce; odgovor kreatora ispod. */
const IgComment: React.FC<{d: any}> = ({d}) => {
  const c = useC();
  const P = c.th.dark ? IG.dark : IG.light;
  const ra = d.atT ?? Math.min(0.8, c.dur * 0.45);
  const kr = prog(c, ra, 0.55);
  const row = (name: string, text: string, size: number, author?: boolean) => (
    <div style={{display: 'flex', gap: 22, alignItems: 'flex-start'}}>
      <IgAvatar size={size} />
      <div style={{flex: 1}}>
        <div style={{...font(700, 32, 1.2), letterSpacing: 0, color: P.ink}}>
          {name} <span style={{fontWeight: 500, color: P.mut}}>{author ? '· Author' : '2m'}</span>
        </div>
        <div style={{...font(500, author ? 40 : 52, 1.25), letterSpacing: '-0.01em', color: P.ink, marginTop: 6}}>{text}</div>
        <div style={{...font(600, 28), letterSpacing: 0, color: P.mut, marginTop: 10}}>Reply</div>
      </div>
      <Heart size={36} color={P.mut} strokeWidth={2} />
    </div>
  );
  if (d.typing) {
    // CTA "komentariši KLJUČNU REČ" (recenzija test-video-3 v1, s18): nativno Instagram polje za komentar — reč se
    // ukuca krupno, "Post" postane plav, komentar se objavi (krupan, bold), srce pukne crveno, pa stiže odgovor.
    const kw = String(d.text);
    const tEnd = Math.min(0.25 + kw.length * 0.07, Math.max(0.6, ra - 0.6));
    const typed = kw.slice(0, Math.round(kw.length * Math.min(1, Math.max(0, (c.t - 0.2) / Math.max(0.3, tEnd - 0.2)))));
    const posted = ease(c.t, tEnd + 0.15, 0.5);
    const heart = ease(c.t, tEnd + 0.55, 0.45, Easing.bezier(0.34, 1.6, 0.64, 1));
    return (
      <div style={{...pop(prog(c, 0)), width: 880, background: P.bg, borderRadius: 44, border: `1.5px solid ${P.line}`,
        padding: '30px 34px', boxShadow: c.th.shadow, boxSizing: 'border-box', fontFamily: CAPTION_FONT}}>
        <div style={{...font(700, 34, 1), letterSpacing: 0, color: P.ink, textAlign: 'center', paddingBottom: 22,
          borderBottom: `1.5px solid ${P.line}`, marginBottom: 26}}>Comments</div>
        {posted > 0.01 ? (
          <div style={{...pop(posted, 20), display: 'flex', gap: 22, alignItems: 'flex-start'}}>
            <IgAvatar size={84} />
            <div style={{flex: 1}}>
              <div style={{...font(700, 32, 1.2), letterSpacing: 0, color: P.ink}}>{d.user ?? 'your.viewer'} <span style={{fontWeight: 500, color: P.mut}}>now</span></div>
              {/* nativno: komentar je običan tekst iste veličine kao u aplikaciji (srazmerno kartici), ne ogroman bold (v2, s30) */}
              <div style={{...font(400, 44, 1.25), letterSpacing: 0, color: P.ink, marginTop: 6}}>{kw}</div>
              <div style={{...font(600, 28), letterSpacing: 0, color: P.mut, marginTop: 10}}>Reply</div>
            </div>
            <div style={{transform: `scale(${0.8 + 0.4 * heart})`, marginTop: 30}}>
              <Heart size={46} color={heart > 0.5 ? '#FF3040' : P.mut} fill={heart > 0.5 ? '#FF3040' : 'none'} strokeWidth={2} />
            </div>
          </div>
        ) : null}
        {d.reply && c.t >= ra ? (
          <div style={{marginTop: 22, marginLeft: 106, ...pop(kr, 16), opacity: (pop(kr, 16).opacity as number)}}>{row(d.author ?? 'you', d.reply, 60, true)}</div>
        ) : null}
        <div style={{marginTop: posted > 0.01 ? 30 : 0, display: 'flex', alignItems: 'center', gap: 20, padding: '16px 18px 16px 16px',
          borderRadius: 99, border: `1.5px solid ${P.line}`, opacity: 1 - 0.55 * posted}}>
          <IgAvatar size={64} />
          <div style={{flex: 1, ...font(400, posted > 0.5 ? 34 : 40, 1), letterSpacing: 0,
            color: typed && posted < 0.5 ? P.ink : P.mut, textAlign: 'left'}}>
            {posted > 0.5 ? 'Add a comment…' : typed || 'Add a comment…'}
            {posted < 0.5 && Math.floor(c.t * 2.2) % 2 === 0 ? <span style={{color: IG.blue}}>|</span> : null}
          </div>
          <div style={{...font(700, 34, 1), letterSpacing: 0, color: typed.length === kw.length && posted < 0.5 ? IG.blue : rgba(IG.blue, 0.4)}}>Post</div>
        </div>
      </div>
    );
  }
  return (
    <div style={{...pop(prog(c, 0)), width: 860, background: P.bg, borderRadius: 44, border: `1.5px solid ${P.line}`,
      padding: '34px 34px 30px', boxShadow: c.th.shadow, boxSizing: 'border-box', fontFamily: CAPTION_FONT}}>
      <div style={{opacity: d.reply ? 1 - 0.45 * ease(c.t, ra, 0.5) : 1}}>{row(d.user ?? 'your.viewer', d.text, 80)}</div>
      {d.reply && c.t >= ra ? (
        <div style={{marginTop: 26, marginLeft: 100, ...pop(kr, 16)}}>{row(d.author ?? 'you', d.reply, 60, true)}</div>
      ) : null}
    </div>
  );
};

/**
 * Resurs iz CTA-a (izveštaj, vodič, šablon) kao pravi predmet (recenzija ai-actor-0 v2, s29): stranice ulaze odmah,
 * naslov na reč, redovi se popunjavaju jedan po jedan, pozadinske stranice se rašire, oznaka ("FREE REPORT") iskoči —
 * vizual prati ono što govornik nudi, ne nasumičan šablon. Podaci: title, sub, badge, icon, rows (3–6), at, badgeAt.
 */
const Resource: React.FC<{d: any}> = ({d}) => {
  const c = useC();
  const tAt = at0(d, 0.4);
  const sAt = at0(d.sub, tAt + 0.5);
  const bAt = typeof d.badgeAt === 'number' ? d.badgeAt : at0(d.badge, sAt + 0.6);
  // Pravi sadržaj resursa (principles.md 43): `rows: ["…"]` = stvarne sekcije, vidljive ODMAH od početka CTA-a.
  const textRows: any[] | null = Array.isArray(d.rows) ? d.rows.slice(0, 5) : null;
  const rows = textRows ? textRows.length : Math.min(5, Math.max(3, d.rows ?? 4));
  const enter = prog(c, 0, 0.7);
  const fan = ease(c.t, sAt, 0.8, Easing.bezier(0.34, 1.3, 0.64, 1));
  const bk = ease(c.t, bAt, 0.5, Easing.bezier(0.34, 1.6, 0.64, 1));
  const PW = 470, PH = 540;  // sav sadržaj staje u stranicu (ništa se ne seče — recenzija v3)
  const Ic: React.FC<any> = (d.icon && ICONS[d.icon]) || Ph.FileText;
  const paper = c.th.dark ? '#151821' : '#FFFFFF';
  const page = (rot: number, dx: number, z: number, children?: React.ReactNode) => (
    <div style={{position: 'absolute', left: '50%', top: 0, width: PW, height: PH, marginLeft: -PW / 2, borderRadius: 26, background: paper,
      border: `1.5px solid ${c.th.line}`, boxShadow: c.th.shadow, transform: `translateX(${dx}px) rotate(${rot}deg)`, zIndex: z,
      overflow: 'hidden'}}>{children}</div>
  );
  const title = txt(d.title);
  // Auto-fit (QA 0.8.0, P1-23): dug naslov ili 5 dugih redova su izlazili ispod stranice (overflow: hidden ih je sekao).
  // Procena visine sadržaja → svi tekstovi se smanje istim faktorom dok ne stane (najviše do 62%).
  const subT = d.sub ? txt(d.sub) : '';
  const tBase = title.length > 18 ? 38 : title.length > 12 ? 44 : 56;
  const TW = PW - 68, RW = TW - 40 - 30 - 28;
  const bodyH = (f: number) => {
    const ts = tBase * f, ss = 28 * f, rs = 29 * f;
    let h = 116 + 30 + lines(title, 800, ts, TW) * ts * 1.05 + 24;
    if (subT) h += 14 + lines(subT, 600, ss, TW) * ss * 1.2;
    if (textRows) h += textRows.reduce((a, r) => a + Math.max(30, lines(txt(r), 700, rs, RW) * rs * 1.15) + 14, 0);
    else h += rows * 38;
    return h;
  };
  let F = 1;
  while (F > 0.62 && bodyH(F) > PH - 24) F -= 0.04;
  const titleSize = Math.min(Math.round(tBase * F), ...title.split(/\s+/).map((w) => fit(w, 800, Math.round(tBase * F), TW)));
  return (
    <div style={{position: 'relative', width: 900, height: PH + 20, ...pop(enter, 40)}}>
      {page(-7 * fan, -170 * fan, 1)}
      {page(7 * fan, 170 * fan, 2)}
      {page(0, 0, 3, (
        <div style={{display: 'flex', flexDirection: 'column', height: '100%'}}>
          <div style={{background: c.acc, padding: '26px 30px', display: 'flex', alignItems: 'center', gap: 18}}>
            <div style={{width: 64, height: 64, borderRadius: 18, background: rgba('#000000', 0.12), display: 'grid', placeItems: 'center'}}>
              <Ic size={40} color={onAccent(c.acc)} weight="bold" />
            </div>
            <div style={{...font(800, 26, 1.1), letterSpacing: '0.12em', color: onAccent(c.acc)}}>{d.kicker ?? 'REPORT'}</div>
          </div>
          <div style={{padding: '30px 34px 0', display: 'flex', flexDirection: 'column', gap: 14}}>
            <div style={{...pop(prog(c, tAt, 0.5), 14), ...font(800, titleSize, 1.05), letterSpacing: '-0.03em', color: c.th.ink}}>{title}</div>
            {d.sub ? <div style={{...pop(prog(c, sAt, 0.5), 10), ...font(600, Math.round(28 * F), 1.2), color: c.th.mut}}>{subT}</div> : null}
            <div style={{display: 'flex', flexDirection: 'column', gap: 14, marginTop: 10}}>
              {Array.from({length: rows}, (_, i) => {
                const k = ease(c.t, textRows ? at0(textRows[i], 0.25 + i * 0.22) : sAt + 0.15 + i * 0.16, 0.4);
                if (textRows) return (
                  <div key={i} style={{display: 'flex', alignItems: 'center', gap: 14, ...pop(k, 10)}}>
                    <div style={{...font(800, 24, 1), color: c.acc, width: 40, fontVariantNumeric: 'tabular-nums'}}>{String(i + 1).padStart(2, '0')}</div>
                    <div style={{...font(700, Math.round(29 * F), 1.15), color: c.th.ink, flex: 1}}>{txt(textRows[i])}</div>
                    <Ph.CheckCircle size={30} weight="fill" color={c.acc} style={{opacity: k}} />
                  </div>
                );
                return (
                  <div key={i} style={{display: 'flex', alignItems: 'center', gap: 14, opacity: 0.25 + 0.75 * k}}>
                    <div style={{...font(800, 24, 1), color: k > 0.5 ? c.acc : c.th.mut, width: 40, fontVariantNumeric: 'tabular-nums'}}>{String(i + 1).padStart(2, '0')}</div>
                    <div style={{height: 14, borderRadius: 99, background: c.th.track, flex: 1, overflow: 'hidden'}}>
                      <div style={{width: `${k * (92 - ((i * 23) % 35))}%`, height: '100%', borderRadius: 99, background: rgba(c.acc, 0.85)}} />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      ))}
      {d.badge ? (
        <div style={{position: 'absolute', zIndex: 5, right: 140, top: -18, transform: `scale(${bk}) rotate(${(1 - bk) * -12 + 6}deg)`,
          opacity: Math.min(1, bk * 1.5), ...font(800, fit(txt(d.badge), 800, 30, 380, 20, 0.08), 1), letterSpacing: '0.08em', color: '#FFFFFF', background: '#FF3040',
          whiteSpace: 'nowrap',
          padding: '14px 24px', borderRadius: 99, boxShadow: '0 14px 30px rgba(255,48,64,0.35)'}}>{txt(d.badge)}</div>
      ) : null}
    </div>
  );
};

/** DM: poruke ulaze redom nadole na reč; pre "you" poruke kucanje. */
const Chat: React.FC<{d: any}> = ({d}) => {
  const c = useC();
  if (d.platform === 'instagram') return <IgChat d={d} />;
  const msgs: any[] = d.messages;
  const times = msgs.map((x, i) => beat(c, x, i, msgs.length));
  return (
    <Glass glow={0.3} style={{...pop(prog(c, 0)), width: 860, padding: '30px 36px 36px'}}>
      <div style={{display: 'flex', alignItems: 'center', gap: 18, paddingBottom: 22, marginBottom: 6,
        borderBottom: `1.5px solid ${c.th.line}`}}>
        <div style={{width: 68, height: 68, borderRadius: 99, background: `linear-gradient(135deg, ${c.acc}, #7A5CFF)`}} />
        <div style={{...font(700, 40), color: c.th.ink}}>{d.title ?? 'Direct message'}</div>
      </div>
      {msgs.map((x, i) => {
        const tt = times[i];
        const you = x.from === 'you';
        const start = you ? tt - 0.4 : tt;
        if (c.t < start) return null;
        const typing = you && c.t < tt;
        const space = ease(c.t, start, 0.45);
        return (
          <div key={i} style={{display: 'flex', justifyContent: you ? 'flex-end' : 'flex-start', marginTop: 18 * space}}>
            {typing ? (
              <div style={{padding: '24px 32px', borderRadius: 30, background: rgba(c.acc, 0.3), display: 'flex', gap: 10, ...pop(space, 14)}}>
                {[0, 1, 2].map((k) => <div key={k} style={{width: 14, height: 14, borderRadius: 9, background: c.th.ink,
                  opacity: 0.3 + 0.7 * Math.abs(Math.sin((c.t * 5) + k * 0.9))}} />)}
              </div>
            ) : (
              <div style={{...pop(prog(c, tt, 0.5), 18), maxWidth: 640, padding: '22px 30px', borderRadius: you ? '34px 34px 8px 34px' : '34px 34px 34px 8px',
                background: you ? c.acc : c.th.glassStrong, color: you ? onAccent(c.acc) : c.th.ink, ...font(700, 46, 1.22),
                border: you ? 'none' : `1.5px solid ${c.th.line}`, boxShadow: you ? `0 0 30px ${rgba(c.acc, 0.5)}` : undefined}}>{txt(x)}</div>
            )}
          </div>
        );
      })}
    </Glass>
  );
};

/** Filter publike: mreža ljudi → na reč ostaju samo "pravi" (sjaj + ✓), ostali blede. */
const FilterGrid: React.FC<{d: any}> = ({d}) => {
  const c = useC();
  const total = Math.min(28, Math.max(12, d.total ?? 24));
  const keep = Math.min(6, Math.max(1, d.keep ?? 3));
  const cols = total % 7 === 0 ? 7 : 6;
  const rows = Math.ceil(total / cols);
  const at = d.atT ?? Math.min(0.9, c.dur * 0.45);
  const k = ease(c.t, at, 0.6);
  const sz = 96, gap = 20;
  // ikonica onoga što se bira (podrazumevano ljudi; npr. "rocket" za firme) — da grid ne laže šta se bira
  const Ico: React.FC<any> = (d.icon && ICONS[d.icon]) || User;
  const picks = new Set(Array.from({length: keep}, (_, i) => Math.floor(((i + 0.5) * total) / keep + (i % 2 ? 2 : -1)) % total));
  const parts = [
    {h: 66, at: 0, el: <div style={{...font(800, 54), color: c.th.ink}}>{d.label}</div>},
    {h: rows * sz + (rows - 1) * gap, at: 0.05, el: (
      <div style={{display: 'grid', gridTemplateColumns: `repeat(${cols}, ${sz}px)`, gap}}>
        {Array.from({length: total}, (_, i) => {
          const on = picks.has(i);
          return (
            <div key={i} style={{...pop(prog(c, 0.08 + 0.015 * i, 0.5), 12), width: sz, height: sz, borderRadius: 99,
              background: on ? rgba(c.acc, k) : c.th.track, opacity: on ? 1 : 1 - 0.72 * k,
              boxShadow: on ? `0 0 ${38 * k}px ${rgba(c.acc, 0.8)}` : undefined, border: `1.5px solid ${c.th.line}`,
              display: 'grid', placeItems: 'center'}}>
              {on && k > 0.4 ? <Check size={50} color={onAccent(c.acc)} strokeWidth={3} /> : <Ico size={48} color={c.th.mut} strokeWidth={2} />}
            </div>
          );
        })}
      </div>
    )},
  ];
  if (d.sub) parts.push({h: 56, at: at0(d.sub, at + 0.3), el: <div style={{...font(700, 44), color: c.th.mut}}>{txt(d.sub)}</div>});
  return <Stack parts={parts} gap={22} />;
};

/** Kinetički naslov: smisleni delovi ulaze na reč; ključni deo dobija highlight koji se iscrtava ispod. */
const Headline: React.FC<{d: any}> = ({d}) => {
  const c = useC();
  const words: any[] = d.words;
  const all = words.map(txt).join(' ');
  // Svaki smisleni deo stoji u jednom redu (nikad se ne lomi unutar sebe); font prati najduži deo.
  const longest = Math.max(...words.map((x) => txt(x).length));
  const size = Math.min(c.hero ? 132 : all.length > 30 ? 96 : all.length > 18 ? 116 : 136, Math.floor(ZONE.w / (longest * 0.54)));
  const times = words.map((x, i) => {
    const raw = typeof x?.atT === 'number' ? x.atT : i * Math.min(0.22, (c.dur * 0.5) / words.length);
    return i === 0 ? Math.min(raw, 0.2) : raw;
  });
  let lines = 1, lineW = 0;  // procena broja redova (delovi se ne lome) — za re-centriranje grupe
  words.forEach((x) => { const w = txt(x).length * size * 0.54 + size * 0.26; if (lineW + w > ZONE.w && lineW > 0) { lines++; lineW = w; } else lineW += w; });
  const parts = [{h: lines * size * 1.08, at: 0, el: (
    <div style={{display: 'flex', flexWrap: 'wrap', justifyContent: 'center', width: ZONE.w, gap: `${size * 0.08}px ${size * 0.26}px`}}>
      {words.map((x, i) => {
        const acc = d.accent && txt(x).toLowerCase().includes(String(d.accent).toLowerCase());
        const el = <span style={{...font(800, size, 1.04), letterSpacing: '-0.045em', color: c.th.ink, whiteSpace: 'nowrap'}}>{txt(x)}</span>;
        return (
          <span key={i} style={{...pop(prog(c, times[i], 0.55), 34), display: 'inline-block'}}>
            {acc ? <Highlight at={times[i]} size={size} tone={d.tone}>{el}</Highlight> : el}
          </span>
        );
      })}
    </div>
  )}];
  if (d.sub) parts.push({h: 64, at: at0(d.sub, Math.min(0.9, c.dur * 0.5)), el: <div style={{...font(600, 50), color: c.th.mut}}>{txt(d.sub)}</div>});
  return <Stack parts={parts} gap={26} />;
};

/** Notifikacije: stižu redom ODOZGO NADOLE (redosled čitanja), meko klizaju nagore; grupa se re-centrira. */
const Notify: React.FC<{d: any}> = ({d}) => {
  const c = useC();
  const items: any[] = d.items.slice(0, 4);
  const times = items.map((x, i) => beat(c, x, i, items.length));
  const parts = items.map((x, i) => ({h: 140, at: times[i], el: (
    <Glass glow={0.25} strong r={34} style={{width: 880, padding: '24px 30px'}}>
      <div style={{display: 'flex', alignItems: 'center', gap: 26}}>
        <NeonTile name={x.icon ?? 'bell'} size={92} tone={x.tone} />
        <div style={{flex: 1, textAlign: 'left'}}>
          <div style={{...font(800, 46), color: c.th.ink}}>{x.title}</div>
          {x.body ? <div style={{...font(600, 34), color: c.th.mut, marginTop: 4}}>{x.body}</div> : null}
        </div>
        <div style={{...font(600, 30), color: c.th.mut}}>now</div>
      </div>
    </Glass>
  )}));
  return <Stack parts={parts} gap={18} focus />;
};

const Key: React.FC<{d: any}> = ({d}) => {
  const c = useC();
  // Jedna reč nikad ne stoji sama u svom redu (recenzija test-video-3 v1, s16 "loop") — spoji je sa naslovom.
  if (d.line2 && !/\s/.test(txt(d.line2).trim())) d = {...d, line1: `${d.line1} ${txt(d.line2).trim()}`, line2: undefined};
  const parts = [
    ...(d.icon ? [{h: 190, at: 0, el: <IconTile name={d.icon} size={190} />}] : []),
    {h: d.line1.length > 22 ? 190 : 120, at: 0.1, el: (
      <div style={{...font(800, d.line1.length > 22 ? 88 : 110, 1.05), letterSpacing: '-0.045em', color: c.th.ink, textAlign: 'center', maxWidth: ZONE.w}}>{d.line1}</div>
    )},
    ...(d.line2 ? [{h: 64, at: at0(d.line2, 0.4), el: <div style={{...font(600, 54), color: c.th.mut, textAlign: 'center'}}>{txt(d.line2)}</div>}] : []),
  ];
  return <Stack parts={parts} gap={30} />;
};

/**
 * Pretraga + merač (recenzija test-video-3 v1, s01): kad govornik kaže da se alat koristi POGREŠNO ("kao search
 * engine"), metafora se rekreira doslovno — traka za pretragu sa CELIM logom alata i upitom koji se kuca — a tvrdnja
 * sa brojem ("trošiš 90% njegove snage") postaje merač: mali deo iskorišćen, ostatak u crvenom, broj se odbrojava na reč.
 */
const Search: React.FC<{d: any}> = ({d}) => {
  const c = useC();
  const q = txt(d.query);
  const qa = at0(d.query, 0.15);
  const typed = q.slice(0, Math.round(q.length * Math.min(1, Math.max(0, (c.t - qa) / Math.max(0.5, q.length * 0.045)))));
  const caret = Math.floor(c.t * 2.2) % 2 === 0 && typed.length < q.length + 1;
  const m = d.meter;
  const ma = m ? at0(m, Math.min(1.4, c.dur * 0.5)) : 0;
  const used = Math.max(2, Math.min(98, Number(m?.used ?? 10)));
  const fill = m ? ease(c.t, ma, 1.1, CAM_GLIDE) : 0;
  const bad = toneColor(m?.tone ?? 'bad', c.acc);
  const parts = [{h: 150, at: 0, el: (
    <Glass glow={0.35} strong r={99} style={{width: 880, height: 140, padding: '0 30px 0 20px', boxSizing: 'border-box'}}>
      {/* Glass umotava decu u svoj div — raspored ide u unutrašnji red */}
      <div style={{height: 140, display: 'flex', alignItems: 'center', gap: 24}}>
      <LogoPlate f={d.logo} size={100} at={0} />
      <div style={{flex: 1, minWidth: 0, ...font(600, 50, 1), letterSpacing: '-0.02em', color: typed ? c.th.ink : c.th.mut,
        whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'clip', textAlign: 'left'}}>
        {typed || (d.placeholder ?? 'Ask anything…')}{caret ? <span style={{color: c.acc}}>|</span> : null}
      </div>
      <div style={{width: 84, height: 84, borderRadius: 99, display: 'grid', placeItems: 'center', background: c.th.track}}>
        <Ph.MagnifyingGlass size={46} color={c.th.ink} weight="bold" />
      </div>
      </div>
    </Glass>
  )}];
  if (m) parts.push({h: 250, at: ma, el: (
    <Glass glow={0.2} style={{width: 880, padding: '32px 40px 36px', boxSizing: 'border-box'}}>
      <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'baseline'}}>
        <div style={{...font(700, 40), color: c.th.mut}}>{m.label ?? 'power used'}</div>
        <div style={{...font(800, 96, 1), color: bad, letterSpacing: '-0.05em', fontVariantNumeric: 'tabular-nums'}}>
          {countUp(String(m.value), fill)}
        </div>
      </div>
      <div style={{position: 'relative', height: 44, borderRadius: 99, marginTop: 22, overflow: 'hidden', background: c.th.track}}>
        <div style={{position: 'absolute', left: 0, top: 0, bottom: 0, width: `${used}%`, background: c.acc,
          boxShadow: `0 0 22px ${rgba(c.acc, 0.8)}`, borderRadius: 99}} />
        <div style={{position: 'absolute', left: `${used}%`, top: 0, bottom: 0, width: `${(100 - used) * fill}%`, borderRadius: '0 99px 99px 0',
          background: `repeating-linear-gradient(135deg, ${rgba(bad, 0.85)} 0 14px, ${rgba(bad, 0.55)} 14px 28px)`}} />
      </div>
      <div style={{display: 'flex', justifyContent: 'space-between', marginTop: 12, ...font(600, 30), color: c.th.mut}}>
        <span style={{color: c.acc}}>{m.usedLabel ?? `${used}% used`}</span><span style={{color: bad, opacity: fill}}>{m.wasteLabel ?? 'wasted'}</span>
      </div>
    </Glass>
  )});
  return <Stack parts={parts} gap={30} />;
};

const Comment: React.FC<{d: any}> = ({d}) => d.platform === 'instagram' ? <IgComment d={d} /> : (
  <Chat d={{title: d.user ?? 'your.viewer', messages: [{from: 'them', text: d.text, atT: 0},
    ...(d.reply ? [{from: 'you', text: d.reply, atT: d.atT ?? 0.6}] : [])]}} />
);

/**
 * Klijentova slika/video: isti glass okvir, ulaz, "dah" i kontrola pažnje kao šabloni — ne odskače od ostatka.
 * Okvir prati oblik fajla (vertikalan screenshot, horizontalan snimak ekrana…) i staje u zonu; slika dobija spor
 * zoom unutar okvira; video kreće od `start` (s u klipu) i, ako je kraći od momenta, zadržava poslednji kadar.
 */
const Media: React.FC<{it: TopItem; sf: number}> = ({it, sf}) => {
  const c = useC();
  const d = it.data;
  const capH = d.caption ? 76 : 0;
  const maxW = 860, maxH = 580 - capH;
  const ar = d.w && d.h ? d.w / d.h : 16 / 9;
  // Nikad više od 2× prirodne veličine — mala slika ostaje oštra (manja), umesto razvučena i mutna.
  const w = Math.min(maxW, maxH * ar, d.w ? d.w * 2 : maxW), h = w / ar;
  const zoom = 1 + 0.06 * interpolate(c.t, [0, Math.max(1, c.dur)], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
    easing: Easing.inOut(Easing.sin)});
  const start = Math.max(0, Number(d.start ?? 0));
  const clipLeft = d.clipDur ? Math.max(0.1, d.clipDur - start) : c.dur;
  const frozen = it.kind === 'video' && c.t >= clipLeft;
  const fill: React.CSSProperties = {width: '100%', height: '100%', objectFit: 'cover', display: 'block'};
  // Providan PNG (logo, izrezan predmet): bez kutije — samo predmet sa senkom i sjajem, na podlozi.
  if (it.kind === 'image' && d.alpha) {
    const parts = [{h: h, at: 0, el: (
      <Img src={staticFile(it.src ?? '')} style={{width: w, height: h, objectFit: 'contain', transform: `scale(${zoom})`,
        filter: `drop-shadow(0 24px 40px rgba(0,0,0,${c.th.dark ? 0.55 : 0.2})) drop-shadow(0 0 30px ${rgba(c.acc, 0.25)})`}} />
    )}];
    if (d.caption) parts.push({h: 56, at: at0(d.caption, 0.35), el: <div style={{...font(800, 46), color: c.th.ink}}>{txt(d.caption)}</div>});
    return <Stack parts={parts} gap={20} />;
  }
  const parts = [{h: h + 24, at: 0, el: (
    <Glass glow={0.5} strong r={36} style={{padding: 12, lineHeight: 0}}>
      <div style={{width: w, height: h, borderRadius: 24, overflow: 'hidden', position: 'relative', background: it.kind === 'video' ? '#000' : 'transparent'}}>
        {it.kind === 'video' ? (
          frozen && it.last ? <Img src={staticFile(it.last)} style={fill} /> : (
            <Sequence from={sf} durationInFrames={Math.max(1, Math.round(clipLeft * c.fps))} layout="none">
              <OffthreadVideo src={staticFile(it.src ?? '')} muted trimBefore={Math.round(start * c.fps)} style={fill} />
            </Sequence>
          )
        ) : (
          <Img src={staticFile(it.src ?? '')} style={{...fill, transform: `scale(${zoom})`}} />
        )}
      </div>
    </Glass>
  )}];
  if (d.caption) parts.push({h: 56, at: at0(d.caption, 0.35), el: <div style={{...font(800, 46), color: c.th.ink}}>{txt(d.caption)}</div>});
  return <Stack parts={parts} gap={20} />;
};


// ------------------------------------------------------------------ oblici iz klijentske recenzije (PLAN §13, faza B)
/** Slika ili snimak u okviru: lagani zoom sve vreme (slika) / snimak od `start` (zamrzne se na kraju klipa). */
/**
 * Lice u sredini okvira (recenzija ai-actor-0 v1, s05/s09): kod `cover` prikaza položaj slike se računa iz lica —
 * centar lica vodoravno u sredini okvira, uspravno na ~40% visine (prostor iznad glave). Bez lica: sredina.
 */
const facePos = (f: any, w: number, h: number) => {
  if (!f?.face || !f.w || !f.h) return '50% 40%';
  const s = Math.max(w / f.w, h / f.h), sw = f.w * s, sh = f.h * s;
  const cx = (f.face.x + f.face.w / 2) * s, cy = (f.face.y + f.face.h / 2) * s;
  // object-position p%: pomeraj = (okvir − slika) · p → tačka `at` slike dolazi na `want` u okviru
  const p = (box: number, size: number, at: number, want: number) =>
    size - box < 1 ? 50 : Math.round(Math.min(100, Math.max(0, ((at - want) / (size - box)) * 100)));
  return `${p(w, sw, cx, w / 2)}% ${p(h, sh, cy, h * 0.4)}%`;
};

const MediaBox: React.FC<{f: any; w: number; h: number; sf: number; r?: number}> = ({f, w, h, sf, r = 30}) => {
  const c = useC();
  const fill: React.CSSProperties = {width: '100%', height: '100%', objectFit: 'cover', display: 'block'};
  const face = facePos(f, w, h);
  const zoom = 1 + 0.07 * interpolate(c.t, [0, Math.max(1, c.dur)], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
    easing: Easing.inOut(Easing.sin)});
  const isVideo = f.mkind === 'video';
  const start = Math.max(0, Number(f.start ?? 0));
  const clipLeft = f.clipDur ? Math.max(0.1, f.clipDur - start) : c.dur;
  return (
    <div style={{width: w, height: h, borderRadius: r, overflow: 'hidden', position: 'relative', flex: 'none',
      background: '#000', boxShadow: `0 30px 60px rgba(0,0,0,${c.th.dark ? 0.5 : 0.22})`, border: `1.5px solid ${c.th.line}`}}>
      {isVideo ? (c.t >= clipLeft && f.last ? <Img src={staticFile(f.last)} style={{...fill, objectPosition: face}} /> : (
        <Sequence from={sf} durationInFrames={Math.max(1, Math.round(clipLeft * c.fps))} layout="none">
          <OffthreadVideo src={staticFile(f.src ?? '')} muted trimBefore={Math.round(start * c.fps)} style={{...fill, objectPosition: face}} />
        </Sequence>
      )) : <Img src={staticFile(f.src ?? '')} style={{...fill, objectPosition: face, transform: `scale(${zoom})`, transformOrigin: face}} />}
    </div>
  );
};

/**
 * Vertikalni snimak/slika: od ivice do ivice gornjeg dela (cela visina), a iza zamućena uvećana verzija istog
 * (klijentska recenzija v2, s14). Opcioni natpis dole, naslov i logo iznad (hero).
 */
const VerticalFull: React.FC<{d: any; sf: number; height: number; children?: React.ReactNode}> = ({d, sf, height, children}) => {
  const c = useC();
  const isVideo = d.mkind === 'video';
  const ar = d.w && d.h ? d.w / d.h : 9 / 16;
  const H = height, W = Math.round(H * ar);
  const start = Math.max(0, Number(d.start ?? 0));
  const clipLeft = d.clipDur ? Math.max(0.1, d.clipDur - start) : c.dur;
  const zoom = 1 + 0.05 * interpolate(c.t, [0, Math.max(1, c.dur)], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
    easing: Easing.inOut(Easing.sin)});
  const media = (style: React.CSSProperties) => isVideo ? (c.t >= clipLeft && d.last ? <Img src={staticFile(d.last)} style={style} /> : (
    <Sequence from={sf} durationInFrames={Math.max(1, Math.round(clipLeft * c.fps))} layout="none">
      <OffthreadVideo src={staticFile(d.src ?? '')} muted trimBefore={Math.round(start * c.fps)} style={style} />
    </Sequence>
  )) : <Img src={staticFile(d.src ?? '')} style={{...style, transform: `scale(${zoom})`}} />;
  const cover: React.CSSProperties = {position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'cover'};
  return (
    <div style={{position: 'absolute', inset: 0, overflow: 'hidden', background: '#000'}}>
      <div style={{position: 'absolute', inset: -60, filter: 'blur(38px) brightness(0.62) saturate(1.15)'}}>{media(cover)}</div>
      <div style={{position: 'absolute', top: 0, height: H, left: (1080 - W) / 2, width: W, overflow: 'hidden',
        boxShadow: '0 0 80px rgba(0,0,0,0.55)'}}>{media(cover)}</div>
      <div style={{position: 'absolute', left: 0, right: 0, bottom: 0, height: LIGHT_SHADE.h,
        background: `linear-gradient(180deg, rgba(12,12,16,0) 0%, rgba(12,12,16,${LIGHT_SHADE.a * 0.4}) 62%, rgba(12,12,16,${LIGHT_SHADE.a}) 100%)`}} />
      {d.caption ? (
        <div style={{position: 'absolute', left: 0, right: 0, top: H - 250, display: 'flex', justifyContent: 'center', ...pop(prog(c, at0(d.caption, 0.3)), 16)}}>
          <div style={{...font(800, 50), color: '#fff', background: 'rgba(12,13,16,0.62)', backdropFilter: 'blur(14px)', padding: '14px 30px',
            borderRadius: 22}}>{txt(d.caption)}</div>
        </div>
      ) : null}
      {children}
    </div>
  );
};

/**
 * Hook / spotlight: glavna tema velika na ekranu, iznad nje upadljiv naslov (sme da preklopi medij), a sa strane
 * logo kompanije kad je pomenu — bez drugog teksta. Hook mora biti jasan i upadljiv, ne scena iz sredine videa.
 */
const Spotlight: React.FC<{d: any; sf: number; height: number}> = ({d, sf, height}) => {
  const c = useC();
  const tAt = at0(d.title, 0.1);
  const k = prog(c, tAt, 0.6);
  const lk = d.logo?.src ? ease(c.t, at0(d.logo, Math.min(1.5, c.dur * 0.4)), 0.7, Easing.bezier(0.34, 1.4, 0.64, 1)) : 0;
  const portrait = d.w && d.h ? d.h / d.w > 1.15 : true;
  const title = d.title ? txt(d.title) : '';
  const tsize = title.length > 18 ? 76 : 92;
  const inner = (
    <>
      {/* naslov stoji NISKO, malo iznad titla na liniji podele — gornja sigurna zona ostaje slobodna (recenzija ai-actor-0 v2, s04) */}
      {title ? <div style={{position: 'absolute', left: 0, right: 0, bottom: 150, display: 'flex', justifyContent: 'center',
        opacity: interpolate(k, [0, 0.4], [0, 1], {extrapolateRight: 'clamp'}),
        transform: `translateY(${(1 - k) * 30}px) scale(${0.86 + 0.14 * k})`}}>
        <div style={{...font(800, tsize, 1.02), letterSpacing: '-0.04em', color: onAccent(c.acc), background: c.acc, padding: '18px 36px 22px',
          borderRadius: 26, boxShadow: `0 20px 60px rgba(0,0,0,0.45), 0 0 50px ${rgba(c.acc, 0.45)}`, textAlign: 'center', maxWidth: 940}}>{title}</div>
      </div> : null}
      {d.logo?.src ? (
        <div style={{position: 'absolute', right: portrait ? 70 : 60, top: height * 0.47, opacity: Math.min(1, lk * 1.4),
          transform: `translateY(-50%) scale(${0.6 + 0.4 * lk}) rotate(${(1 - lk) * -8}deg)`}}>
          <LogoPlate f={d.logo} size={200} at={at0(d.logo, 0)} />
        </div>
      ) : null}
    </>
  );
  const fx = d.fx && (d.fx.type ?? 'vanish') === 'vanish' ? d.fx : null;
  const layer = portrait
    ? <VerticalFull d={{...d, caption: undefined}} sf={sf} height={height} />
    : <div style={{position: 'absolute', inset: 0}}><MediaBox f={d} w={1080} h={height} sf={sf} r={0} /></div>;
  if (!fx) {
    if (portrait) return <VerticalFull d={{...d, caption: undefined}} sf={sf} height={height}>{inner}</VerticalFull>;
    return <div style={{position: 'absolute', inset: 0, overflow: 'hidden', background: '#000'}}>{layer}{inner}</div>;
  }
  // "Ne postoji" (recenzija ai-actor-0 v1, s04): preokret se pokazuje NA samoj slici — na reč slika zaigra digitalno
  // (pomereni pojasevi, RGB razdvajanje), pa izbledi u sivi "duh" sa linijama skeniranja. Tekst ostaje naslov.
  const g = at0(fx, Math.min(0.8, c.dur * 0.3));
  const gl = c.t >= g && c.t < g + 0.75 ? Math.sin(((c.t - g) / 0.75) * Math.PI) : 0;  // jačina glitch-a
  const v = ease(c.t, g + 0.3, 0.9);  // nestajanje
  const fr = Math.round(c.t * c.fps);
  const rnd = (i: number) => {const x = Math.sin(fr * 12.9898 + i * 78.233) * 43758.5453; return x - Math.floor(x);};
  const slices = gl > 0.05 ? [0, 1, 2, 3].map((i) => {
    const y0 = rnd(i) * 85, hh = 4 + rnd(i + 9) * 12, dx = (rnd(i + 20) - 0.5) * 120 * gl;
    return (
      <div key={i} style={{position: 'absolute', inset: 0, clipPath: `inset(${y0}% 0 ${Math.max(0, 100 - y0 - hh)}% 0)`,
        transform: `translateX(${dx}px)`, filter: `hue-rotate(${rnd(i + 30) * 90 * gl}deg)`}}>{layer}</div>
    );
  }) : null;
  return (
    <div style={{position: 'absolute', inset: 0, overflow: 'hidden', background: '#000'}}>
      <div style={{position: 'absolute', inset: 0, opacity: 1 - 0.72 * v, transform: `translateX(${(rnd(99) - 0.5) * 16 * gl}px)`,
        filter: `grayscale(${v}) contrast(${1 + 0.25 * v}) blur(${1.4 * v}px)`}}>
        {layer}
        {gl > 0.05 ? <div style={{position: 'absolute', inset: 0, transform: `translateX(${10 * gl}px)`, mixBlendMode: 'screen', opacity: 0.55 * gl,
          filter: 'sepia(1) saturate(6) hue-rotate(-50deg)'}}>{layer}</div> : null}
        {gl > 0.05 ? <div style={{position: 'absolute', inset: 0, transform: `translateX(${-10 * gl}px)`, mixBlendMode: 'screen', opacity: 0.55 * gl,
          filter: 'sepia(1) saturate(6) hue-rotate(150deg)'}}>{layer}</div> : null}
        {slices}
      </div>
      <div style={{position: 'absolute', inset: 0, opacity: Math.max(gl * 0.8, v * 0.55), pointerEvents: 'none',
        background: 'repeating-linear-gradient(0deg, rgba(255,255,255,0.10) 0px, rgba(255,255,255,0.10) 2px, rgba(0,0,0,0) 2px, rgba(0,0,0,0) 6px)'}} />
      {inner}
    </div>
  );
};

/** Logo fajl (ccc logo / providan PNG): prikazuje se ceo u pločici, nikad kao slika u okviru (cover bi ga isekao). */
const isLogo = (f: any) => Boolean(f?.src) && f?.mkind !== 'video' && (/web-logo-/.test(String(f.src)) || Boolean(f.alpha));

/** Medij + tekst: slika/snimak sa jedne strane, rečenice o njemu sa druge — pojavljuju se na reč, ranije se utišaju. */
const MediaText: React.FC<{d: any; sf: number}> = ({d, sf}) => {
  const c = useC();
  const lines: any[] = d.lines ?? [];
  const times = lines.map((x, i) => beat(c, x, i, lines.length));
  const mediaRight = d.side === 'right';
  const longest = Math.max(0, ...lines.map((x) => txt(x).length));
  const size = longest > 34 ? 44 : longest > 22 ? 52 : 60;
  const pm = prog(c, 0, 0.7);
  // Logo se NIKAD ne iseca (recenzija test-video-3 v1, s06): ceo, u neon pločici, sa blagim lebdenjem — ne u okviru slike.
  const bob = Math.sin(c.t * 1.8) * 8;
  // Duža scena = 2–3 slike u istom okviru (recenzija ai-actor-0 v1, s21): `more: [{file, at}]` se smenjuju na reč
  // (meki prelaz + blagi zoom-in nove), da jedna slika ne stoji 8 s.
  const more: any[] = (d.more ?? []).filter((m: any) => m?.src);
  const media = isLogo(d)
    ? <div style={{width: 430, height: 560, display: 'grid', placeItems: 'center', transform: `translateY(${bob}px)`}}><LogoPlate f={d} size={340} at={0} /></div>
    : more.length ? (
      <div style={{width: 430, height: 560, position: 'relative'}}>
        <MediaBox f={d} w={430} h={560} sf={sf} />
        {more.map((m, i) => {
          const k = ease(c.t, at0(m, (c.dur / (more.length + 1)) * (i + 1)), 0.5);
          return k > 0 ? (
            <div key={i} style={{position: 'absolute', inset: 0, opacity: k, transform: `scale(${1.04 - 0.04 * k})`}}>
              <MediaBox f={m} w={430} h={560} sf={sf} />
            </div>
          ) : null;
        })}
      </div>
    ) : <MediaBox f={d} w={430} h={560} sf={sf} />;
  return (
    <div style={{width: ZONE.w, height: 560, display: 'flex', flexDirection: mediaRight ? 'row-reverse' : 'row', alignItems: 'center', gap: 44}}>
      <div style={{...pop(pm, 30)}}>{media}</div>
      <div style={{flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', gap: 22, textAlign: 'left'}}>
        {d.title ? <div style={{...pop(prog(c, 0.1)), ...font(700, 32), color: c.th.mut, letterSpacing: '0.02em', textTransform: 'uppercase'}}>{d.title}</div> : null}
        {lines.map((x, i) => {
          const base = pop(prog(c, times[i]), 18);
          const dim = i < lines.length - 1 ? ease(c.t, times[i + 1], 0.5) * 0.55 : 0;
          return (
            <div key={i} style={{...base, opacity: (base.opacity as number) * (1 - dim), ...font(800, size, 1.08),
              color: x.tone ? toneColor(x.tone, c.acc) : c.th.ink, fontVariantNumeric: 'tabular-nums'}}>{countUp(txt(x), ease(c.t, times[i], 1.0))}</div>
          );
        })}
      </div>
    </div>
  );
};

/** Objave jedna preko druge: svaka nova ulazi pomereno, prethodne se povuku i utišaju. */
const PostStack: React.FC<{d: any}> = ({d}) => {
  const c = useC();
  const list: any[] = d.items ?? [];
  const n = list.length;
  const times = list.map((x, i) => beat(c, x, i, n));
  const rot = [-3, 2.5, -1.5, 2];
  return (
    <div style={{width: ZONE.w, height: 580, position: 'relative'}}>
      {list.map((x, i) => {
        const p = prog(c, times[i], 0.7);
        const after = list.slice(i + 1).filter((_, j) => c.t >= times[i + 1 + j]).length;
        const back = after > 0 ? ease(c.t, times[i + 1], 0.55) : 0;
        const base = pop(p, 40);
        const fit = x.src ? Math.min(760 / (x.w || 1000), 540 / (x.h || 1000)) : 0.78;  // slika: u okvir 760×540; nativna objava: 78%
        const iw2 = x.src ? (x.w || 1000) * fit : 880 * fit;
        const scale = 1 - 0.05 * Math.min(2, after - 1 + back);
        const off = i - (n - 1) / 2;
        const cx = ZONE.w / 2 + off * 70, cy = 290 + off * 46;
        return (
          <div key={i} style={{position: 'absolute', left: cx, top: cy, transformOrigin: '50% 50%', ...base,
            transform: `translate(-50%, -50%) ${base.transform} rotate(${rot[i % 4] * (1 - 0.4 * back)}deg) scale(${scale})`, width: iw2,
            opacity: (base.opacity as number) * (1 - 0.45 * Math.min(1, after - 1 + back)),
            filter: [base.filter, back > 0.01 ? `brightness(${1 - 0.25 * Math.min(1, after - 1 + back)})` : ''].filter(Boolean).join(' ') || undefined}}>
            {x.src ? (
              <Img src={staticFile(x.src)} style={{width: iw2, borderRadius: 24, display: 'block', boxShadow: c.th.shadow,
                border: '6px solid #fff'}} />
            ) : <div style={{transform: `scale(${fit})`, transformOrigin: '0 0', width: 880}}><Post d={{...x, atT: 0}} /></div>}
          </div>
        );
      })}
    </div>
  );
};

/** Osoba kojoj je glava na slici odsečena: kartica (beo okvir) sa licem u kadru + natpis sa trouglićem ispod. */
const PersonCard: React.FC<{d: any}> = ({d}) => {
  const c = useC();
  const pm = prog(c, 0, 0.7);
  const tagAt = at0(d, 0.45);
  const k = d.name ? ease(c.t, tagAt - 0.25, 0.75, CAM_GLIDE) : 1;  // pre natpisa: velika u sredini; natpis stiže → smanji se
  const sc = 1.24 - 0.24 * k;
  return (
    <div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 30, transform: `translateY(${(1 - k) * 70}px)`}}>
      <div style={{...pop(pm, 30), transform: `${pop(pm, 30).transform} scale(${sc})`, transformOrigin: '50% 60%', background: '#FFFFFF', padding: 14,
        borderRadius: 40, boxShadow: `0 30px 70px rgba(0,0,0,${c.th.dark ? 0.5 : 0.2})`}}>
        <MediaBox f={{...d, mkind: 'image'}} w={470} h={460} sf={0} r={28} />
      </div>
      <div style={{position: 'relative', height: 120, width: ZONE.w}}><NameTag d={d} top={22} /></div>
    </div>
  );
};

/**
 * Face-off (recenzija aazar-trial-1 v1, s01–s03): kad se dve strane porede, OBE su u kadru od prvog frejma —
 * gledalac odmah vidi KO se poredi, a onda se animira ono o čemu se priča. Svaka strana: kartica sa licem
 * (centrirano iz detekcije), logo brenda zakačen na dnu kartice, ime ispod, pa vrednosti koje ulaze na reč i
 * odbrojavaju (`values: [{text, at, tone, label}]` — nova zameni prethodnu, ista kartica ostaje). `tone: "bad"` =
 * crvena vrednost + strana se blago utiša; `tone: "good"` = sjaj u boji brenda. Mirno: spor zoom i lagano lebdenje,
 * bez jurnjave — pažnju nosi to ko je u kadru, ne brzina.
 */
const Faceoff: React.FC<{d: any; sf: number}> = ({d, sf}) => {
  const c = useC();
  const sides: any[] = (d.sides ?? []).slice(0, 2);
  const W = 390, Hc = 430, LOGO = 112;
  const vs = ease(c.t, 0.3, 0.7, Easing.bezier(0.34, 1.4, 0.64, 1));
  return (
    <div style={{width: ZONE.w, height: 640, position: 'relative', display: 'flex', justifyContent: 'center', gap: 110, marginTop: 30}}>
      {sides.map((s, i) => {
        const inn = ease(c.t, i * 0.14, 0.85);
        const vals: any[] = s.values ?? [];
        const times = vals.map((v, j) => at0(v, 0.8 + j * 1.2));
        let cur = -1;
        times.forEach((tt, j) => { if (c.t >= tt) cur = j; });
        const v = cur >= 0 ? vals[cur] : null;
        const kv = cur >= 0 ? ease(c.t, times[cur], 0.6) : 0;
        const bad = v?.tone === 'bad' ? kv : 0;
        const good = v?.tone === 'good' ? kv : 0;
        const bob = Math.sin((c.t + i * 1.3) * 1.6) * 5;
        return (
          <div key={i} style={{width: W, display: 'flex', flexDirection: 'column', alignItems: 'center',
            opacity: Math.min(1, inn * 1.5), transform: `translateY(${(1 - inn) * 60 + bob}px)`}}>
            <div style={{position: 'relative', borderRadius: 32,
              boxShadow: good > 0.01 ? `0 0 ${70 * good}px ${rgba(c.acc, 0.55 * good)}` : undefined,
              filter: bad > 0.01 ? `brightness(${1 - 0.28 * bad}) saturate(${1 - 0.45 * bad})` : undefined}}>
              <MediaBox f={{...s, mkind: s.mkind === 'video' ? 'video' : 'image'}} w={W} h={Hc} sf={sf} r={32} />
              {s.logo?.src ? (
                <div style={{position: 'absolute', left: '50%', bottom: -LOGO / 2, transform: 'translateX(-50%)'}}>
                  <LogoPlate f={s.logo} size={LOGO} at={0.2 + i * 0.14} />
                </div>
              ) : null}
            </div>
            <div style={{marginTop: s.logo?.src ? LOGO / 2 + 18 : 22, ...font(800, fit(s.name ?? '', 800, 44, W + 40), 1.05), color: c.th.ink,
              textAlign: 'center', whiteSpace: 'nowrap'}}>{s.name ?? ''}</div>
            <div style={{position: 'relative', height: 120, width: W + 120, marginTop: 6}}>
              {vals.map((x, j) => {
                if (j !== cur && j !== cur - 1) return null;
                const kin = ease(c.t, times[j], 0.6);
                const kout = j < cur ? ease(c.t, times[cur], 0.45) : 0;
                if (kin <= 0) return null;
                return (
                  <div key={j} style={{position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center',
                    opacity: kin * (1 - kout), transform: `translateY(${(1 - kin) * 18 - kout * 22}px)`}}>
                    <div style={{...font(900, fit(txt(x), 900, txt(x).length <= 8 ? 66 : txt(x).length <= 13 ? 52 : 40, W + 50, 26, -0.04), 1.0),
                      letterSpacing: '-0.04em', fontVariantNumeric: 'tabular-nums', whiteSpace: 'nowrap',
                      color: x.tone === 'bad' ? TONES.bad : x.tone === 'good' ? c.acc : c.th.ink}}>{countUp(txt(x), ease(c.t, times[j], 1.1))}</div>
                    {x.label ? <div style={{...font(600, fit(x.label, 600, 30, W + 50, 20)), color: c.th.mut, marginTop: 8, whiteSpace: 'nowrap'}}>{x.label}</div> : null}
                  </div>
                );
              })}
            </div>
          </div>
        );
      })}
      <div style={{position: 'absolute', left: '50%', top: Hc / 2, width: 118, height: 118, marginLeft: -59, marginTop: -59,
        borderRadius: 999, background: c.acc, display: 'grid', placeItems: 'center', opacity: Math.min(1, vs * 1.4),
        transform: `scale(${0.4 + 0.6 * vs})`, boxShadow: `0 0 ${50 * vs}px ${rgba(c.acc, 0.5)}`,
        ...font(900, 50, 1), letterSpacing: '-0.02em', color: onAccent(c.acc)}}>VS</div>
    </div>
  );
};

/**
 * Pillars (recenzija aazar-trial-1 v3, s02/s27): brojke dve-tri strane kao stubići, a na vrhu SVAKOG stubića lice/logo
 * te strane — zna se čiji je koji. `sets`: [{label, at, values: [n…], display: ["$4.2M"…], tones: ["good","bad"],
 * note: {text, at}}] — svaki skup ulazi na reč, stubići glatko narastu/smanje se na nove vrednosti (pratioci → prihod),
 * lica putuju sa vrhom stubića. Ime ispod osnove.
 */
const Pillars: React.FC<{d: any}> = ({d}) => {
  const c = useC();
  const bars: any[] = (d.bars ?? []).slice(0, 3);
  const sets: any[] = d.sets ?? [];
  const n = bars.length;
  // vrh najvišeg stubića: vrednost (70) + lice (AV) ispod natpisa skupa i "note" (0–120) — ništa se ne dodiruje (principle 13)
  const BW = n === 3 ? 170 : 200, GAP = n === 3 ? 90 : 170, AV = 132, BASE = 610, MAXH = 230, MINH = 34;
  const times = sets.map((s, i) => at0(s, i === 0 ? 0.25 : 0.8 + i));
  let cur = 0;
  times.forEach((tt, i) => { if (c.t >= tt) cur = i; });
  const hOf = (si: number, bi: number) => {
    const vals: number[] = (sets[si]?.values ?? []).map(Number);
    const mx = Math.max(1e-9, ...vals);
    return MINH + (MAXH - MINH) * Math.max(0, (vals[bi] ?? 0) / mx);
  };
  const totalW = n * BW + (n - 1) * GAP;
  const x0 = (ZONE.w - totalW) / 2;
  const SLOT = Math.min(BW + GAP - 24, BW + 2 * x0 + 60);  // širina za vrednost/ime: ne prelazi u susedni stubić
  const setLabel = sets[cur]?.label;
  // isti natpis kao u prethodnom skupu ostaje miran (ne trepne) — principle 44
  const kl = cur > 0 && sets[cur - 1]?.label === setLabel ? 1 : ease(c.t, times[cur] ?? 0, 0.55);
  const note = sets[cur]?.note;
  const noteT = note ? at0(note, (times[cur] ?? 0) + 0.9) : 0;
  const kn = note ? ease(c.t, noteT, 0.6, Easing.bezier(0.34, 1.4, 0.64, 1)) : 0;
  return (
    <div style={{width: ZONE.w, height: 680, position: 'relative'}}>
      {setLabel ? (
        <div style={{position: 'absolute', left: 0, right: 0, top: 0, textAlign: 'center', ...font(700, fit(setLabel, 700, 36, ZONE.w, 24)), color: c.th.mut,
          whiteSpace: 'nowrap',
          letterSpacing: '0.01em', opacity: kl, transform: `translateY(${(1 - kl) * 10}px)`}}>{setLabel}</div>
      ) : null}
      {note && kn > 0 ? (
        <div style={{position: 'absolute', left: '50%', top: 58, transform: `translateX(-50%) scale(${0.7 + 0.3 * kn})`, opacity: Math.min(1, kn * 1.4),
          ...font(900, fit(txt(note), 900, 46, ZONE.w - 60, 28)), color: onAccent(note.tone === 'bad' ? TONES.bad : c.acc), background: note.tone === 'bad' ? TONES.bad : c.acc,
          padding: '8px 24px', borderRadius: 16, whiteSpace: 'nowrap', boxShadow: `0 0 40px ${rgba(c.acc, 0.35)}`}}>{txt(note)}</div>
      ) : null}
      <div style={{position: 'absolute', left: x0 - 40, width: totalW + 80, top: BASE, height: 3, borderRadius: 3, background: c.th.line}} />
      {bars.map((b, i) => {
        const inn = ease(c.t, i * 0.12, 0.8);
        // visina: od prethodnog skupa ka trenutnom (glatko), prvi skup raste od nule
        const prev = cur > 0 ? hOf(cur - 1, i) : 0;
        const k = ease(c.t, (times[cur] ?? 0) + i * 0.12, 1.0, CAM_GLIDE);
        const h = (prev + (hOf(cur, i) - prev) * k) * (cur === 0 ? 1 : 1);
        const hh = cur === 0 ? hOf(0, i) * k : h;
        const tone = sets[cur]?.tones?.[i];
        const col = tone === 'bad' ? TONES.bad : tone === 'good' ? c.acc : c.th.hi;
        const shown = sets[cur]?.display?.[i] ?? String(sets[cur]?.values?.[i] ?? '');
        // Ono što je već na ekranu se NE resetuje kad stigne novi skup (recenzija aazar-trial-1 v4, s02, principle 44):
        // nepromenjena vrednost stoji puna; promenjena prelazi iz stare u novu (bez vraćanja na nulu).
        const before = cur > 0 ? (sets[cur - 1]?.display?.[i] ?? String(sets[cur - 1]?.values?.[i] ?? '')) : null;
        const same = before !== null && before === shown;
        const kv = same ? 1 : k;
        const valueText = same ? shown : countUp(shown, k);
        const left = x0 + i * (BW + GAP);
        const top = BASE - hh;
        return (
          <React.Fragment key={i}>
            <div style={{position: 'absolute', left, width: BW, top, height: hh, borderRadius: '22px 22px 6px 6px',
              background: `linear-gradient(180deg, ${rgba(col.startsWith('#') ? col : '#FFFFFF', 0.95)} 0%, ${rgba(col.startsWith('#') ? col : '#FFFFFF', 0.45)} 100%)`,
              boxShadow: tone === 'good' ? `0 0 50px ${rgba(c.acc, 0.45 * kv)}` : undefined, opacity: inn}} />
            <div style={{position: 'absolute', left: left + BW / 2 - AV / 2, top: top - AV - 14, width: AV, height: AV, opacity: inn,
              transform: `scale(${0.85 + 0.15 * inn})`}}>
              {b.logo?.src && !b.src ? <LogoPlate f={b.logo} size={AV} at={0} /> : (
                <div style={{width: AV, height: AV, borderRadius: 999, overflow: 'hidden', border: `5px solid ${tone === 'bad' ? TONES.bad : c.acc}`,
                  boxShadow: '0 16px 40px rgba(0,0,0,0.45)', background: '#000'}}>
                  <Img src={staticFile(b.src ?? '')} style={{width: '100%', height: '100%', objectFit: 'cover', objectPosition: facePos(b, AV, AV)}} />
                </div>
              )}
            </div>
            <div style={{position: 'absolute', left: left - 60, width: BW + 120, top: top - AV - 14 - 74, textAlign: 'center', opacity: kv,
              ...font(900, fit(shown, 900, 60, SLOT, 30, -0.04), 1), letterSpacing: '-0.04em', color: tone === 'bad' ? TONES.bad : tone === 'good' ? c.acc : c.th.ink,
              fontVariantNumeric: 'tabular-nums', whiteSpace: 'nowrap'}}>{valueText}</div>
            <div style={{position: 'absolute', left: left - 60, width: BW + 120, top: BASE + 16, textAlign: 'center', ...font(800, fit(b.name ?? '', 800, 38, SLOT, 22)),
              color: c.th.ink, opacity: inn, whiteSpace: 'nowrap'}}>{b.name ?? ''}</div>
          </React.Fragment>
        );
      })}
    </div>
  );
};

/**
 * Scena — full-screen custom animacija (recenzija aazar-trial-1 v3 + vlasnik): kad govornik objašnjava nešto što
 * gledalac treba da ZAMISLI, ceo gornji deo postaje pozornica i stvari o kojima se priča odglume to na reč.
 * Glumci su PRAVI asseti (reklama, proizvod, logo, lice); grafika (ikonica/tekst) samo kad asseta nema.
 *   actors: [{id, file | icon | text, x, y, size, aspect?, at?, frame?, round?}] — x/y = centar u px gornjeg dela (1080 × visina), size = širina
 *   beats:  [{at, do, target?, …}] — do: "move" {x, y, scale} · "clone" {n, cols, x, y, scale, gap} · "cycle" {rx, ry,
 *           speed, icon} · "tag" {text, x, y, tone} · "stamp" {text, tone} · "dim" · "focus" (ostali se utišaju) ·
 *           "swap" {file} (nova slika u istom okviru) · "exit"
 * Sve se kreće stalno (lagano lebdenje), ništa ne skače: svaki pokret je meka kriva.
 */
/** Tekst-glumac: font staje u širinu glumca, najduža reč u jedan red, najviše 3 reda (ranije je `size` = i font). */
const textSize = (a: any, w: number) => {
  let fs = a.fontSize ?? 64;
  const words = String(a.text ?? '').split(/\s+/).filter(Boolean);
  while (fs > 26 && (lines(a.text, 900, fs, w) > 3 || words.some((x) => textW(x, 900, fs) * 1.04 > w))) fs -= 2;
  return fs;
};

const Scene: React.FC<{d: any; sf: number; height: number}> = ({d, height}) => {
  const c = useC();
  const actors: any[] = d.actors ?? [];
  const beats: any[] = (d.beats ?? []).map((b: any, i: number) => ({...b, T: at0(b, 0.8 + i * 0.9)})).sort((a: any, b: any) => a.T - b.T);
  const forT = (id: string) => beats.filter((b) => b.target === id);
  const nodes: React.ReactNode[] = [];
  const glide = (T: number, len = 0.9) => ease(c.t, T, len, CAM_GLIDE);
  const actorBox = (a: any, w: number, h: number, key: string, extra: React.CSSProperties, img?: any) => {
    const f = img ?? a;
    const logo = isLogo(f);
    const inner = f.src
      ? (logo ? <LogoPlate f={f} size={Math.min(w, h)} at={0} /> : (
        <div style={{width: w, height: h, borderRadius: a.round ? 999 : 22, overflow: 'hidden', background: a.frame ? '#fff' : '#000',
          padding: a.frame ? 8 : 0, boxSizing: 'border-box', boxShadow: '0 24px 60px rgba(0,0,0,0.5)', border: `1.5px solid ${c.th.line}`}}>
          <Img src={staticFile(f.src)} style={{width: '100%', height: '100%', objectFit: a.fit ?? 'cover', objectPosition: facePos(f, w, h),
            borderRadius: a.frame ? 16 : 0, background: a.fit === 'contain' ? '#fff' : undefined}} />
        </div>))
      : a.icon ? <IconTile name={a.icon} size={Math.min(w, h)} at={0} />
        : <div style={{...font(900, textSize(a, w), 1.05), color: c.th.ink, textAlign: 'center', width: w}}>{a.text}</div>;
    return <div key={key} style={{position: 'absolute', left: 0, top: 0, ...extra}}>{inner}</div>;
  };
  const focusB = beats.filter((b) => b.do === 'focus');
  // Sigurna zona (QA 0.8.0, P1-23/24): glumac, mreža klonova, krug i natpisi uvek staju u x 90–990, y 240–840.
  const sizeOf = (a: any) => {
    const w = a.size ?? 300;
    if (a.text) { const fs = textSize(a, w); return [w, Math.round(lines(a.text, 900, fs, w) * fs * 1.05)]; }
    return [w, a.icon ? w : Math.round(w * (a.aspect ?? (a.w && a.h ? a.h / a.w : 1.25)))];
  };
  actors.forEach((a, ai) => {
    // `size` = širina glumca u px (w/h na čvoru su prave dimenzije slike koje engine upiše) → visina iz aspect ili slike
    const [w, h] = sizeOf(a);
    const tin = at0(a, 0);
    const kin = ease(c.t, tin, 0.7);
    if (kin <= 0) return;
    let x = clampX(a.x ?? 540, w), y = clampY(a.y ?? height / 2, h), s = 1, op = 1, dim = 0;
    let img: any = null;
    const mine = forT(a.id);
    for (const b of mine) {
      const k = glide(b.T);
      if (b.do === 'move') {
        const ts = b.scale ?? s;
        x += (clampX(b.x ?? x, w * ts) - x) * k; y += (clampY(b.y ?? y, h * ts) - y) * k; s += (ts - s) * k;
      }
      if (b.do === 'dim') dim = Math.max(dim, ease(c.t, b.T, 0.6));
      if (b.do === 'exit') op *= 1 - ease(c.t, b.T, 0.5);
      if (b.do === 'swap' && c.t >= b.T && b.src) img = b;
    }
    for (const f of focusB) {
      if (f.target !== a.id && c.t >= f.T) dim = Math.max(dim, 0.6 * ease(c.t, f.T, 0.5));
    }
    const clone = mine.find((b) => b.do === 'clone');
    const cyc = mine.find((b) => b.do === 'cycle');
    const bob = Math.sin((c.t + ai * 0.9) * 1.7) * 5;
    const style = (px: number, py: number, sc: number, o: number, rot = 0): React.CSSProperties => ({
      transform: `translate(${px - (w * sc) / 2}px, ${py - (h * sc) / 2 + bob}px) scale(${sc}) rotate(${rot}deg)`, transformOrigin: '0 0',
      opacity: o * Math.min(1, kin * 1.4),
      filter: dim > 0.01 ? `grayscale(${0.8 * dim}) brightness(${1 - 0.4 * dim})` : undefined,
    });
    if (!clone) {
      nodes.push(actorBox(a, w, h, `a${ai}`, style(x, y, s * (0.92 + 0.08 * kin), op), img));
    } else {
      const N = Math.max(1, Math.round(clone.n ?? 10));
      const cols = clone.cols ?? Math.ceil(Math.sqrt(N * 1.6));
      const rows = Math.ceil(N / cols);
      let sc = clone.scale ?? 0.38;
      let gap = clone.gap ?? 26;
      // mreža veća od zone → cela se smanji (i razmak), pa centar ostaje u zoni
      const gw = (cols - 1) * (w * sc + gap) + w * sc, gh = (rows - 1) * (h * sc + gap) + h * sc;
      const shrink = Math.min(1, ZONE.w / gw, ZONE.h / gh);
      sc *= shrink; gap *= shrink;
      const cw = w * sc + gap, ch = h * sc + gap;
      const gx = clampX(clone.x ?? 540, gw * shrink), gy = clampY(clone.y ?? height / 2 + 30, gh * shrink);
      for (let k = 0; k < N; k++) {
        const r = Math.floor(k / cols), cc = k % cols;
        const inRow = Math.min(cols, N - r * cols);
        const tx = gx + (cc - (inRow - 1) / 2) * cw, ty = gy + (r - (rows - 1) / 2) * ch;
        const p = k === 0 ? glide(clone.T, 0.8) : glide(clone.T + 0.12 + k * 0.07, 0.75);
        let px = x + (tx - x) * p, py = y + (ty - y) * p;
        let pS = s + (sc - s) * p;
        let rot = 0;
        if (cyc) {
          const q = glide(cyc.T, 1.0);
          const om = (cyc.speed ?? 0.9) * Math.max(0, c.t - cyc.T);
          const th0 = (k / N) * Math.PI * 2 - Math.PI / 2 + om;
          const cs = cyc.scale ?? sc * 0.85;
          const rx = Math.min(cyc.rx ?? 330, Math.max(0, ZONE.w / 2 - (w * cs) / 2));
          const ry = Math.min(cyc.ry ?? 220, Math.max(0, ZONE.h / 2 - (h * cs) / 2));
          const cx = clampX(cyc.x ?? 540, 2 * rx + w * cs), cy = clampY(cyc.y ?? height / 2 + 20, 2 * ry + h * cs);
          const ex = cx + rx * Math.cos(th0), ey = cy + ry * Math.sin(th0);
          px += (ex - px) * q; py += (ey - py) * q;
          pS += ((cyc.scale ?? sc * 0.85) - pS) * q;
          rot = q * Math.sin(th0) * 6;
        }
        const o = k === 0 ? op : op * Math.min(1, p * 1.6);
        if (o > 0.01) nodes.push(actorBox(a, w, h, `a${ai}c${k}`, {...style(px, py, pS, o, rot), zIndex: Math.round(py)}, img));
      }
      if (cyc) {
        const q = ease(c.t, cyc.T + 0.2, 0.7, Easing.bezier(0.34, 1.4, 0.64, 1));
        const I = (cyc.icon && ICONS[cyc.icon]) || Ph.ArrowsClockwise;
        const cs = cyc.scale ?? sc * 0.85;
        const rx = Math.min(cyc.rx ?? 330, Math.max(0, ZONE.w / 2 - (w * cs) / 2));
        const ry = Math.min(cyc.ry ?? 220, Math.max(0, ZONE.h / 2 - (h * cs) / 2));
        const cx = clampX(cyc.x ?? 540, 2 * rx + w * cs), cy = clampY(cyc.y ?? height / 2 + 20, 2 * ry + h * cs);
        nodes.push(
          <div key={`cyc${ai}`} style={{position: 'absolute', left: cx - 70, top: cy - 70, width: 140, height: 140, borderRadius: 999,
            background: c.acc, display: 'grid', placeItems: 'center', opacity: Math.min(1, q * 1.4), zIndex: 2000,
            transform: `scale(${0.4 + 0.6 * q}) rotate(${(c.t - cyc.T) * 160}deg)`, boxShadow: `0 0 60px ${rgba(c.acc, 0.55)}`}}>
            <I size={84} weight="bold" color={onAccent(c.acc)} />
          </div>,
        );
      }
    }
  });
  beats.filter((b) => b.do === 'tag' || b.do === 'stamp').forEach((b, i) => {
    const k = ease(c.t, b.T, 0.55, Easing.bezier(0.34, 1.4, 0.64, 1));
    if (k <= 0) return;
    const tgt = actors.find((a) => a.id === b.target);
    const col = b.tone === 'bad' ? TONES.bad : c.acc;
    const stamp = b.do === 'stamp';
    const ts = fit(stamp ? String(b.text ?? '').toUpperCase() : b.text, 900, b.size ?? (stamp ? 64 : 46), ZONE.w - 80 - (stamp ? 12 : 0), 26,
      stamp ? 0.02 : -0.02);
    const bw = textW(stamp ? String(b.text ?? '').toUpperCase() : b.text, 900, ts, stamp ? 0.02 : -0.02) + 52 + (stamp ? 12 : 0);
    const bh = ts + 20 + (stamp ? 12 : 0);
    const x = clampX(b.x ?? tgt?.x ?? 540, bw * (stamp ? 1 : 1)), y = clampY(b.y ?? (tgt ? (tgt.y ?? 480) : 780), bh);
    nodes.push(
      <div key={`t${i}`} style={{position: 'absolute', left: x, top: y, zIndex: 3000, whiteSpace: 'nowrap',
        transform: `translate(-50%, -50%) scale(${(stamp ? 1.5 - 0.5 * k : 0.7 + 0.3 * k)}) rotate(${stamp ? -8 : 0}deg)`, opacity: Math.min(1, k * 1.5),
        ...font(900, ts, 1), letterSpacing: stamp ? '0.02em' : '-0.02em',
        color: stamp ? col : onAccent(col), background: stamp ? 'rgba(0,0,0,0.35)' : col,
        border: stamp ? `6px solid ${col}` : undefined, padding: stamp ? '10px 26px' : '10px 26px', borderRadius: 18,
        textTransform: stamp ? 'uppercase' : undefined, boxShadow: `0 0 40px ${rgba(col, 0.35)}`}}>{b.text}</div>,
    );
  });
  return <div style={{position: 'absolute', inset: 0}}>{nodes}</div>;
};

// ------------------------------------------------------------------ pravi asseti sa interneta (PLAN §12)
/**
 * Pravi logo u ISTOJ backlit neon pločici kao ikonice (doslednost — odluka 12. nov 2026): tamna grafitna pločica,
 * tanka svetla ivica, logo u svojim bojama; taman logo (crn/tamnosiv) se prikazuje beo da se vidi na tamnoj pločici.
 */
const LogoPlate: React.FC<{f: any; size: number; at?: number}> = ({f, size, at}) => {
  const c = useC();
  const ar = f?.w && f?.h ? f.w / f.h : 1;
  const wide = ar > 2.2;
  const tw = wide ? size * 1.9 : size;
  const inner = size * 0.56;
  const iw = wide ? tw - size * 0.36 : ar >= 1 ? inner : inner * ar;
  const ih = wide ? (tw - size * 0.36) / ar : ar >= 1 ? inner / ar : inner;
  const t0 = at ?? useContext(AtCtx);
  const k = ease(c.t, t0 + 0.08, 0.7, Easing.bezier(0.34, 1.4, 0.64, 1));
  return (
    <div style={{width: tw, height: size, borderRadius: size * 0.29, flex: 'none', display: 'grid', placeItems: 'center',
      background: 'linear-gradient(180deg, #26272C 0%, #141518 100%)', border: '1.5px solid rgba(255,255,255,0.07)',
      boxShadow: `inset 0 1px 0 ${rgba(c.acc, 0.42)}, inset 0 0 ${size * 0.15}px ${rgba(c.acc, 0.07)}, 0 ${size * 0.12}px ${size * 0.23}px rgba(0,0,0,${c.th.dark ? 0.35 : 0.22})`}}>
      {f?.src ? <Img src={staticFile(f.src)} style={{width: iw, height: ih, objectFit: 'contain',
        transform: `scale(${0.7 + 0.3 * k})`, filter: f.dark ? 'brightness(0) invert(1)' : undefined}} /> : null}
    </div>
  );
};

/** Logo: jedan (pločica + ime + opis) ili više (red pločica koje ulaze na reč, fokus na najnovijoj). */
const Logo: React.FC<{d: any}> = ({d}) => {
  const c = useC();
  const list: any[] = d.logos ?? [{...d, atT: d.atT}];
  if (list.length === 1) {
    const x = list[0];
    const parts = [{h: 330, at: 0, el: <LogoPlate f={x} size={c.hero ? 330 : 300} />}];
    if (x.name || d.name) parts.push({h: 92, at: 0.15, el: <div style={{...font(800, 78, 1.05), letterSpacing: '-0.04em', color: c.th.ink}}>{x.name ?? d.name}</div>});
    if (d.sub) parts.push({h: 60, at: at0(d.sub, 0.45), el: <div style={{...font(600, 46), color: c.th.mut}}>{txt(d.sub)}</div>});
    return <Stack parts={parts} gap={24} />;
  }
  // Velike pločice: sve su tu od početka, prigušene; svaka se upali (i dobije ime) kad se brend pomene.
  const times = list.map((x, i) => (typeof x?.atT === 'number' ? x.atT : beat(c, x, i, list.length)));
  const size = list.length >= 4 ? 190 : list.length === 3 ? 240 : 300;
  return (
    <div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 34}}>
      {d.title ? <div style={{...font(700, 46), color: c.th.mut}}>{d.title}</div> : null}
      <div style={{display: 'flex', gap: list.length >= 4 ? 30 : 56, justifyContent: 'center', flexWrap: 'wrap', width: ZONE.w}}>
        {list.map((x, i) => {
          const on = ease(c.t, times[i], 0.55);
          const nm = ease(c.t, times[i] + 0.12, 0.5);
          const inn = ease(c.t, i * 0.14, 0.75, Easing.bezier(0.2, 0.9, 0.25, 1));  // ulazak: odozdo, sa rotacijom, jedna za drugom
          const bob = (1 - on) * Math.sin((c.t + i * 0.7) * 2.4) * 6;            // dok čeka: lagano lebdi
          return (
            <div key={i} style={{display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 22,
              opacity: Math.min(1, inn * 1.6), transform: `translateY(${(1 - inn) * 90 + bob}px) rotate(${(1 - inn) * (i % 2 ? 9 : -9)}deg)`}}>
              <div style={{opacity: 0.38 + 0.62 * on, filter: on < 0.99 ? `grayscale(${1 - on}) brightness(${0.72 + 0.28 * on})` : undefined,
                transform: `scale(${0.9 + 0.1 * on + 0.06 * Math.sin(Math.PI * on)})`, boxShadow: `0 0 ${46 * on}px ${rgba(c.acc, 0.35 * on)}`, borderRadius: size * 0.29}}>
                <LogoPlate f={x} size={size} at={times[i]} />
              </div>
              <div style={{height: 50, opacity: nm, transform: `translateY(${(1 - nm) * 12}px)`, ...font(800, 44), color: c.th.ink}}>{x.name ?? ''}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

/**
 * Slike i screenshotovi (pravila CCC revizije 12. nov 2026):
 *  - "bleed": ceo gornji deo (bez prozora) kad god označeni deo može da stoji u sredini sigurne zone, a da nigde
 *    nije uz ivicu ni isečen;
 *  - "blend": slika jednobojne ivice (telefon, beo sajt) → podloga gornjeg dela u boji ivice, slika se stopi u celinu
 *    i može da se naglasi bilo koji deo bez vidljivih ivica;
 *  - "frame": prozor pregledača / telefona kad ništa od toga ne ide.
 * Kamera: PRAVOLINIJSKI zoom (vidljivi pravougaonik se linearno sužava ka cilju, meko ubrzanje/usporavanje).
 * Isticanje: "flat cut-out" — označeni deo ostaje pun, ostatak izbledi ka boji podloge iza slike.
 */
/** Kretanje kamere (zoom/pan): S-kriva — sporo krene, ubrza na pola, sporo stane (ease-in-out quart), duže trajanje. */
const CAM_EASE = Easing.bezier(0.76, 0, 0.24, 1);

/**
 * Kamera + zatamnjenje kao JEDAN pokret (klijentska recenzija 12. nov 2026): kreće se od prvog kadra (nikad mirno pa
 * naglo), meko ubrzava i usporava dolazeći na označeni deo malo posle reči koja ga pominje, pa mirna pauza za čitanje.
 * Zatamnjenje ostatka ide istom krivom i traje jednako dugo kao zoom.
 */
const CAM_GLIDE = Easing.bezier(0.42, 0.08, 0.22, 1);
const camGlide = (t: number, dur: number, hlAt: number | null, arriveHint?: number) => {
  if (hlAt === null) return ease(t, 0, Math.max(1, dur), Easing.inOut(Easing.sin));  // bez isticanja: lagano celom scenom
  const hold = Math.min(1.4, Math.max(0.8, dur * 0.3));
  const arrive = Math.min(Math.max(1.0, dur - hold), Math.max(1.0, typeof arriveHint === 'number' ? arriveHint : hlAt + 0.5));
  return ease(t, 0, arrive, CAM_GLIDE);
};
type View = {x: number; y: number; w: number; h: number};
type PicPlan = {mode: 'bleed' | 'blend' | 'frame'; v0: View; v1: View; bg: string; W: number; H: number};
const FOCUS_C = {x: 540, y: 540};  // centar sigurne zone gornjeg dela (x 90–990, y 240–840)

const picPlan = (d: any, H: number, kind = 'screenshot'): PicPlan => {
  const W = 1080, iw = d.w || 1600, ih = d.h || 1000;
  // Fotografija se NIKAD ne seče da popuni ekran (recenzija ai-actor-0 v2, s19): preko celog gornjeg dela samo kad
  // `cover` odseca ≤ 12 % — inače ceo kadar, manji, na čistoj podlozi (prozor), kao ostali asseti.
  if (kind === 'image' && !d.focus && !d.highlight) {
    const cut = 1 - Math.min((iw / ih) / (W / H), (W / H) / (iw / ih));
    const sB0 = Math.max(W / iw, H / ih);
    const cov: View = {x: (iw - W / sB0) / 2, y: (ih - H / sB0) / 2, w: W / sB0, h: H / sB0};
    if (cut > 0.12) return {mode: 'frame', v0: cov, v1: cov, bg: '#FFFFFF', W, H};
  }
  const f = d.highlight ? {...(d.focus ?? {}), ...d.highlight} : d.focus;
  const hasF = f && f.w > 0 && f.h > 0;
  const sB = Math.max(W / iw, H / ih);
  const cover: View = {x: (iw - W / sB) / 2, y: (ih - H / sB) / 2, w: W / sB, h: H / sB};
  const toward = (s1: number, inBounds: boolean): View | null => {
    if (!hasF) return null;
    const v = {x: f.x + f.w / 2 - FOCUS_C.x / s1, y: f.y + f.h / 2 - FOCUS_C.y / s1, w: W / s1, h: H / s1};
    if (!inBounds) return v;
    const cx = Math.min(Math.max(v.x, 0), iw - v.w), cy = Math.min(Math.max(v.y, 0), ih - v.h);
    const off = Math.hypot(cx - v.x, cy - v.y) * s1;  // koliko bi fokus otišao sa sredine (px na ekranu)
    const fx = (f.x - cx) * s1, fy = (f.y - cy) * s1;
    const inZone = fx >= 90 && fx + f.w * s1 <= 990 && fy >= 240 && fy + f.h * s1 <= 840;
    return off <= 60 && inZone ? {x: cx, y: cy, w: v.w, h: v.h} : null;
  };
  // 1) bleed
  const arOk = Math.max(iw / ih, (W / H)) / Math.min(iw / ih, (W / H)) <= 1.6;
  if (hasF) {
    const sMax = Math.min(800 / f.w, 500 / f.h);
    const s1 = Math.min(sMax, sB * 2.4);
    const v1 = s1 >= sB ? toward(s1, true) : null;
    if (v1) return {mode: 'bleed', v0: cover, v1, bg: d.edge ?? '#FFFFFF', W, H};
  } else if (arOk) {
    const k = 1 / 1.06;
    return {mode: 'bleed', v0: cover, v1: {x: cover.x + cover.w * (1 - k) / 2, y: cover.y + cover.h * (1 - k) / 2, w: cover.w * k, h: cover.h * k},
      bg: d.edge ?? '#FFFFFF', W, H};
  }
  // 2) blend — i svetla stranica sa izgovorenim oznakama čija je ivica jednobojna bar sa 2 strane (članak: belo
  // oko teksta, tamno zaglavlje gore): kamera sme da priđe tekstu krupno, iza je boja stranice (recenzija
  // ai-actor-0 v1, s13/s17 — prozor je ostavljao citat i cene sitnim)
  const markedLight = (d.marks ?? []).some((m: any) => m.rect && m.rect.w && !m.blur) && (d.edgeSides?.length ?? 0) >= 2
    && typeof d.edge === 'string' && d.edge.length === 7 && lum(d.edge) > 0.6;
  if (d.edgeUniform || markedLight) {
    const s0 = Math.min((W * 0.92) / iw, (H - 60) / ih);
    const v0 = {x: (iw * s0 - W) / 2 / s0, y: (ih * s0 - H) / 2 / s0 + (H / 2 - 500) / s0, w: W / s0, h: H / s0};
    const v1 = hasF ? (toward(Math.max(s0 * 1.15, Math.min(800 / f.w, 500 / f.h, s0 * 3)), false) as View)
      : {x: v0.x + v0.w * 0.03, y: v0.y + v0.h * 0.03, w: v0.w * 0.94, h: v0.h * 0.94};
    return {mode: 'blend', v0, v1, bg: d.edge, W, H};
  }
  return {mode: 'frame', v0: cover, v1: cover, bg: '#FFFFFF', W, H};
};

/** Pogled koji stavlja označenu frazu (marker) u sredinu, malo bliže od trenutnog pogleda (s14/s15 recenzije). */
const markView = (v1: View, m: any, iw: number, ih: number, free = false, W = 1080, main?: any,
                  center: {x: number; y: number} = FOCUS_C, fitW = 860): View => {
  // Recenzija ai-actor-0 v1 (s13, s17): istaknut tekst na KRAJU pokreta je u sredini kadra i KRUPAN.
  // `center` = sredina vidljivog dela (gornji deo: FOCUS_C; prozor: sredina prozora — ranije je i prozor koristio
  // 540/540 sa celog ekrana, pa je fraza završavala dole desno). Zoom: red teksta ~70 px na ekranu, a sve označene
  // fraze zajedno staju u `fitW`; nikad dalje od dosadašnjeg pogleda osim kad mora da stane.
  const r = m.rect;
  const lh = Math.max(8, m.lh || r.h);
  const sv = W / v1.w;
  const sc = Math.min(fitW / r.w, Math.max(sv * 1.05, Math.min(70 / lh, sv * 3.2)));
  const w = W / sc, h = w * (v1.h / v1.w);
  let x = r.x + r.w / 2 - center.x / sc;
  const y = r.y + r.h / 2 - center.y / sc;
  // ceo istaknuti deo (npr. naslov) ostaje vidljiv kad god staje uz krupne oznake — ne seče se zbog markera
  if (main && main.w && main.w * sc <= fitW) {
    const lo = main.x + main.w - (center.x + fitW / 2) / sc, hi = main.x - (center.x - fitW / 2) / sc;
    if (lo <= hi) x = Math.min(Math.max(x, lo), hi);
  }
  if (free) return {x, y, w, h};
  return {x: Math.min(Math.max(x, 0), Math.max(0, iw - w)), y: Math.min(Math.max(y, 0), Math.max(0, ih - h)), w, h};
};

/** Sve izgovorene oznake zajedno (ne samo prva): pravougaonik koji ih obuhvata + visina reda + prvi takt. */
const markUnion = (d: any): any | null => {
  const ms: any[] = (d.marks ?? []).filter((m: any) => m.rect && m.rect.w && !m.blur);
  if (!ms.length) return null;
  const x0 = Math.min(...ms.map((m) => m.rect.x)), y0 = Math.min(...ms.map((m) => m.rect.y));
  const x1 = Math.max(...ms.map((m) => m.rect.x + m.rect.w)), y1 = Math.max(...ms.map((m) => m.rect.y + m.rect.h));
  const lh = Math.min(...ms.flatMap((m) => (m.lines?.length ? m.lines : [m.rect]).map((q: any) => q.h)));
  return {rect: {x: x0, y: y0, w: x1 - x0, h: y1 - y0}, lh, atT: Math.min(...ms.map((m) => at0(m, 0.6)))};
};

/** Kamera kroz sliku: pravougaonik pogleda ide PRAVO od v0 do v1 (bez krive), meko ubrzanje/usporavanje. */
const camera = (v0: View, v1: View, z: number, W: number) => {
  const v = {x: v0.x + (v1.x - v0.x) * z, y: v0.y + (v1.y - v0.y) * z, w: v0.w + (v1.w - v0.w) * z, h: v0.h + (v1.h - v0.h) * z};
  const s = W / v.w;
  return {s, tx: -v.x * s, ty: -v.y * s};
};

/** Slika + flat cut-out isticanje; `bg` = boja "oblika" iza slike u koju ostatak izbledi. */
const PicLayer: React.FC<{d: any; s: number; tx: number; ty: number; kh: number; bg: string}> = ({d, s, tx, ty, kh, bg}) => {
  const c = useC();
  const iw = d.w || 1600, ih = d.h || 1000;
  // oznake (ime, cifra): na reč se ta fraza izdvoji iz zatamnjenja i dobije marker u boji brenda, s leva na desno
  const lightPage = lum((d.edge && d.edge.length === 7 ? d.edge : '#FFFFFF')) > 0.5;
  const marks: any[] = (d.marks ?? []).filter((m: any) => m.rect && m.rect.w);
  const hl = d.highlight ? {...(d.focus ?? {}), ...d.highlight} : null;
  const pad = 10;
  return (
    <div style={{position: 'absolute', left: 0, top: 0, width: iw, height: ih, transformOrigin: '0 0',
      transform: `translate(${tx}px, ${ty}px) scale(${s})`}}>
      <div style={{position: 'absolute', inset: 0, background: bg}} />
      {d.src ? <Img src={staticFile(d.src)} style={{position: 'absolute', inset: 0, width: iw, height: ih, opacity: 1 - 0.78 * kh}} /> : null}
      {hl && hl.w ? (
        <div style={{position: 'absolute', left: hl.x - pad, top: hl.y - pad, width: hl.w + pad * 2, height: hl.h + pad * 2,
          overflow: 'hidden', borderRadius: 8, opacity: kh > 0 ? 1 : 0}}>
          {d.src ? <Img src={staticFile(d.src)} style={{position: 'absolute', left: -(hl.x - pad), top: -(hl.y - pad), width: iw, height: ih}} /> : null}
        </div>
      ) : null}
      {marks.flatMap((m, i) => {
        const at = at0(m, 0.4), lines: any[] = m.lines?.length ? m.lines : [m.rect], p2 = 6;
        const total = lines.reduce((a, q) => a + q.w, 0) || 1;
        let acc = 0;
        return lines.map((r, j) => {
          // marker prelazi liniju po liniju, kao rukom
          const k = m.blur ? 1 : ease(c.t, at + (acc / total) * 0.45, 0.45 * (r.w / total) + 0.05);
          acc += r.w;
          if (k <= 0) return null;
          return (
            <div key={`${i}-${j}`} style={{position: 'absolute', left: r.x - p2, top: r.y - p2, width: r.w + p2 * 2, height: r.h + p2 * 2}}>
              <div style={{position: 'absolute', inset: 0, overflow: 'hidden', borderRadius: 6}}>
                {d.src ? <Img src={staticFile(d.src)} style={{position: 'absolute', left: -(r.x - p2), top: -(r.y - p2), width: iw, height: ih}} /> : null}
              </div>
              {m.blur ? (
                <div style={{position: 'absolute', inset: -4, borderRadius: 10, backdropFilter: `blur(${14 * k}px)`,
                  background: `rgba(${lightPage ? '255,255,255' : '20,20,24'},${0.25 * k})`}} />
              ) : (
                <div style={{position: 'absolute', left: 0, top: 0, bottom: 0, width: `${k * 100}%`, borderRadius: 6,
                  background: rgba(c.acc, lightPage ? 0.55 : 0.4), mixBlendMode: lightPage ? 'multiply' : 'screen'}} />
              )}
            </div>
          );
        });
      })}
    </div>
  );
};

/** Ceo gornji deo (bleed / blend): slika je površina za edit; titl na liniji dobija blagu senku ako je slika svetla. */
const PictureFull: React.FC<{d: any; plan: PicPlan}> = ({d, plan}) => {
  const c = useC();
  const hl = d.highlight;
  const hlAt = hl ? at0(hl, Math.min(0.9, c.dur * 0.4)) : null;
  const light = lum(plan.bg.length === 7 ? plan.bg : '#FFFFFF') > 0.5;
  const mk = markUnion(d);  // sve izgovorene oznake zajedno; zamućena oznaka: bez približavanja
  // jedan pravolinijski pokret od početka do konačnog cilja — bez skretanja na pola puta (recenzija v3, s15)
  const main = d.highlight ? {...(d.focus ?? {}), ...d.highlight} : d.focus;
  const target = mk ? markView(plan.v1, mk, d.w || 1600, d.h || 1000, plan.mode === 'blend' || Boolean(d.edgeUniform) || light, plan.W, main) : plan.v1;
  const z = camGlide(c.t, c.dur, mk ? at0(mk, hlAt ?? 0.6) : hlAt, d.zoomAt);
  const {s, tx, ty} = camera(plan.v0, target, z, plan.W);
  const kh = hl ? z : 0;  // zatamnjenje = isti pokret kao zoom
  return (
    <div style={{position: 'absolute', inset: 0, overflow: 'hidden', background: plan.bg}}>
      <PicLayer d={d} s={s} tx={tx} ty={ty} kh={kh} bg={plan.bg} />
      {plan.mode === 'bleed' || light ? (
        <div style={{position: 'absolute', left: 0, right: 0, bottom: 0, height: LIGHT_SHADE.h,
          background: `linear-gradient(180deg, rgba(12,12,16,0) 0%, rgba(12,12,16,${LIGHT_SHADE.a * 0.12}) 35%, rgba(12,12,16,${LIGHT_SHADE.a * 0.4}) 62%, rgba(12,12,16,${LIGHT_SHADE.a * 0.75}) 84%, rgba(12,12,16,${LIGHT_SHADE.a}) 100%)`}} />
      ) : null}
    </div>
  );
};

/** Prozor (pregledač ili telefon) — kad ni pun prikaz ni stapanje ne mogu; ista kamera i cut-out. */
const Screenshot: React.FC<{d: any; photo?: boolean}> = ({d, photo}) => {
  const c = useC();
  const phone = d.device === 'phone' || (d.w && d.h && d.h / d.w > 1.4);
  const iw = d.w || 1600, ih = d.h || 1000, ar = iw / ih;
  // fotografija (image) nije stranica: bez trake pregledača, samo ceo kadar u okviru na čistoj podlozi
  const barH = phone || photo ? 0 : 46;
  const capH = photo && d.caption ? 80 : 0;  // natpis ispod fotografije (npr. naziv serije)
  const maxW = phone ? 360 : 880, maxH = 560 - barH - capH;
  const fw = Math.min(maxW, maxH * ar), fh = fw / ar;
  const hl = d.highlight ? {...(d.focus ?? {}), ...d.highlight} : null;
  const f = hl ?? d.focus;
  const hlAt = hl ? at0(d.highlight, Math.min(0.9, c.dur * 0.4)) : null;
  const v0: View = {x: 0, y: 0, w: iw, h: ih};
  // fotografija bez fokusa: blag zoom celom scenom (ništa ne stoji mrtvo), kadar ostaje ceo na početku
  let v1 = photo && !(f && f.w) ? {x: iw * 0.03, y: ih * 0.03, w: iw * 0.94, h: ih * 0.94} : v0;
  if (f && f.w) {
    const s1 = Math.max(1, Math.min(2.6, (iw * 0.62) / f.w, (ih * 0.7) / f.h));
    const w = iw / s1, h = ih / s1;
    v1 = {x: Math.min(Math.max(f.x + f.w / 2 - w / 2, 0), iw - w), y: Math.min(Math.max(f.y + f.h / 2 - h / 2, 0), ih - h), w, h};
  }
  const mk = markUnion(d);  // sve izgovorene oznake zajedno; zamućena oznaka: bez približavanja
  // prozor: slika ostaje u svojim ivicama; sredina = sredina PROZORA (ne ekrana)
  const target = mk ? markView(v1, mk, iw, ih, false, fw, f, {x: fw / 2, y: fh / 2}, fw * 0.86) : v1;
  const z = camGlide(c.t, c.dur, mk ? at0(mk, hlAt ?? 0.6) : f && f.w ? (hlAt ?? Math.min(0.9, c.dur * 0.4)) : null, d.zoomAt);
  const {s, tx, ty} = camera(v0, target, z, fw);
  const kh = hl ? z : 0;  // zatamnjenje = isti pokret kao zoom
  const host = (d.url || '').replace(/^https?:\/\//, '').replace(/^www\./, '').split('/')[0];
  return (
    <div style={{...pop(prog(c, 0))}}>
      <Glass glow={0.35} strong r={phone ? 54 : 30} style={{padding: phone ? 14 : 10}}>
        {!phone && !photo ? (
          <div style={{height: barH, display: 'flex', alignItems: 'center', gap: 10, padding: '0 12px'}}>
            {['#FF5F57', '#FEBC2E', '#28C840'].map((col) => <div key={col} style={{width: 14, height: 14, borderRadius: 9, background: col}} />)}
            <div style={{flex: 1, marginLeft: 14, height: 28, borderRadius: 9, background: c.th.dark ? 'rgba(255,255,255,0.08)' : 'rgba(10,10,12,0.06)',
              ...font(600, 18, 1.55), letterSpacing: 0, color: c.th.mut, textAlign: 'center'}}>{host}</div>
          </div>
        ) : null}
        <div style={{width: fw, height: fh, borderRadius: phone ? 42 : 14, overflow: 'hidden', position: 'relative', background: '#fff'}}>
          <PicLayer d={d} s={s * (iw / iw)} tx={tx} ty={ty} kh={kh} bg={d.edge ?? '#FFFFFF'} />
        </div>
      </Glass>
      {capH ? (
        <div style={{display: 'flex', justifyContent: 'center', marginTop: 22, ...pop(prog(c, at0(d.caption, 0.3)), 14)}}>
          <div style={{...font(800, 46), color: c.th.ink}}>{txt(d.caption)}</div>
        </div>
      ) : null}
    </div>
  );
};

/**
 * Prava fotografija (osoba, proizvod, mesto): isti način prikaza kao slike (ceo gornji deo / stapanje / prozor);
 * kod osobe kamera polako ide ka licu (glava i ramena), lice se nikad ne iseče. Natpis imena i opisa ulazi na reč.
 */
/**
 * Natpis sa imenom i malim trouglićem na vrhu (pokazuje na osobu iznad). Stil `d.tagStyle`:
 *  glass (staklo, kao do sada) · accent (boja brenda) · light (beo, ime + uloga u boji brenda).
 */
const NameTag: React.FC<{d: any; top?: number}> = ({d, top = 690}) => {
  const c = useC();
  if (!d.name) return null;
  const k = prog(c, at0(d, 0.45), 0.6);
  const st: string = d.tagStyle ?? 'glass';
  const bg = st === 'accent' ? c.acc : st === 'light' ? '#FFFFFF' : 'rgba(14,15,18,0.72)';
  const ink = st === 'accent' ? onAccent(c.acc) : st === 'light' ? '#0B0D12' : '#FFFFFF';
  const sub = st === 'accent' ? rgba(onAccent(c.acc), 0.72) : st === 'light' ? c.acc : 'rgba(255,255,255,0.72)';
  const tri = 24;
  return (
    <div style={{position: 'absolute', left: 0, right: 0, top, display: 'flex', justifyContent: 'center', ...pop(k, 18)}}>
      <div style={{position: 'relative', filter: 'drop-shadow(0 14px 30px rgba(0,0,0,0.35))'}}>
        <div style={{position: 'absolute', left: '50%', top: -tri + 2, width: tri * 2, height: tri, marginLeft: -tri,
          background: bg, clipPath: 'polygon(50% 0, 100% 100%, 0 100%)', backdropFilter: st === 'glass' ? 'blur(18px)' : undefined}} />
        <div style={{background: bg, borderRadius: 24, padding: st === 'glass' ? '16px 30px' : '16px 32px',
          backdropFilter: st === 'glass' ? 'blur(18px)' : undefined, display: 'flex', flexDirection: 'column', alignItems: 'center'}}>
          <div style={{...font(800, 46, 1.05), color: ink, fontVariantNumeric: 'tabular-nums'}}>{countUp(String(d.name), ease(c.t, at0(d, 0.45), 1.0))}</div>
          {d.sub ? <div style={{...font(700, 30, 1.2), color: sub, marginTop: 4}}>{txt(d.sub)}</div> : null}
        </div>
      </div>
    </div>
  );
};

const photoFocus = (d: any) => {
  if (d.focus) return d.focus;
  const f = d.face;
  if (!f) return null;
  // glava i ramena oko lica
  return {x: f.x - f.w * 0.9, y: f.y - f.h * 0.6, w: f.w * 2.8, h: f.h * 2.9};
};

const photoPlan = (d: any, H: number): PicPlan => {
  const W = 1080, iw = d.w || 1600, ih = d.h || 1000;
  const sB = Math.max(W / iw, H / ih);
  const f = photoFocus(d);
  const clampV = (v: View): View => ({...v, x: Math.min(Math.max(v.x, 0), iw - v.w), y: Math.min(Math.max(v.y, 0), ih - v.h)});
  const at = (s1: number, cx: number, cy: number) => clampV({x: cx - FOCUS_C.x / s1, y: cy - (FOCUS_C.y - 40) / s1, w: W / s1, h: H / s1});
  const cx = f ? f.x + f.w / 2 : iw / 2, cy = f ? f.y + f.h / 2 : ih / 2;
  const v0 = at(sB, cx, cy), v1 = at(sB * 1.08, cx, cy);
  // samo LICE mora stati u sigurnu zonu pri cover prikazu (glava/ramena služe za kadriranje), inače okvir
  const face = d.face;
  // i CELA glava (teme ≈ 0.6 visine lica iznad okvira lica) mora biti u kadru — inače kartica osobe, ne odsečena glava
  const fitsFace = !face || (face.w * sB <= 760 && face.h * sB <= 520 && ((face.y - face.h * 0.6 - v0.y) * sB) >= 20);
  if (fitsFace) return {mode: 'bleed', v0, v1, bg: d.edge ?? '#111', W, H};
  return {mode: 'frame', v0, v1, bg: '#111', W, H};
};

const PhotoFull: React.FC<{d: any; plan: PicPlan}> = ({d, plan}) => {
  const c = useC();
  const z = ease(c.t, 0, Math.max(1, c.dur), Easing.inOut(Easing.sin));  // stalni lagani zoom dok slika traje
  const {s, tx, ty} = camera(plan.v0, plan.v1, z, plan.W);
  return (
    <div style={{position: 'absolute', inset: 0, overflow: 'hidden', background: plan.bg}}>
      <PicLayer d={{...d, highlight: null}} s={s} tx={tx} ty={ty} kh={0} bg={plan.bg} />
      <div style={{position: 'absolute', left: 0, right: 0, bottom: 0, height: LIGHT_SHADE.h,
        background: `linear-gradient(180deg, rgba(12,12,16,0) 0%, rgba(12,12,16,${LIGHT_SHADE.a * 0.12}) 35%, rgba(12,12,16,${LIGHT_SHADE.a * 0.4}) 62%, rgba(12,12,16,${LIGHT_SHADE.a * 0.75}) 84%, rgba(12,12,16,${LIGHT_SHADE.a}) 100%)`}} />
      <NameTag d={d} />
    </div>
  );
};

/**
 * Objava sa društvene mreže — "native to the platform" (izgled i boje platforme, bez loga): X, Reddit, LinkedIn,
 * Threads. Kad govornik čita objavu naglas, delovi teksta se ističu na reč (`highlight: [{text, at}]`).
 * Ako postoji pravi screenshot objave (`file`), koristi se on (kao screenshot).
 */
const POST_THEME = {
  x: {bg: '#000000', ink: '#E7E9EA', mut: '#71767B', line: '#2F3336', accent: '#1D9BF0'},
  threads: {bg: '#101010', ink: '#F3F5F7', mut: '#777777', line: '#323232', accent: '#F3F5F7'},
  reddit: {bg: '#0E1113', ink: '#F2F4F5', mut: '#8BA2AD', line: '#2A3236', accent: '#FF4500'},
  linkedin: {bg: '#1B1F23', ink: '#FFFFFFE6', mut: '#FFFFFF99', line: '#38434F', accent: '#71B7FB'},
} as const;
const POST_LIGHT = {
  x: {bg: '#FFFFFF', ink: '#0F1419', mut: '#536471', line: '#EFF3F4', accent: '#1D9BF0'},
  threads: {bg: '#FFFFFF', ink: '#000000', mut: '#999999', line: '#E5E5E5', accent: '#000000'},
  reddit: {bg: '#FFFFFF', ink: '#1C1C1C', mut: '#576F76', line: '#E5EBEE', accent: '#FF4500'},
  linkedin: {bg: '#FFFFFF', ink: '#000000E6', mut: '#00000099', line: '#E8E8E8', accent: '#0A66C2'},
} as const;

const fmtCount = (n: any) => (typeof n === 'number' ? (n >= 1e6 ? `${(n / 1e6).toFixed(1)}M` : n >= 1e3 ? `${(n / 1e3).toFixed(1)}K` : `${n}`) : n);

const ReadAlong: React.FC<{text: string; hls: any[]; color: string; size: number}> = ({text, hls, color, size}) => {
  const c = useC();
  const segs: {t: string; at?: number}[] = [];
  let rest = text;
  (hls ?? []).map((h) => ({t: txt(h), at: at0(h, 0.5)})).forEach((h) => {
    const i = rest.toLowerCase().indexOf(h.t.toLowerCase());
    if (i < 0) return;
    if (i > 0) segs.push({t: rest.slice(0, i)});
    segs.push({t: rest.slice(i, i + h.t.length), at: h.at});
    rest = rest.slice(i + h.t.length);
  });
  if (rest) segs.push({t: rest});
  return (
    <>
      {segs.map((sg, i) => {
        if (typeof sg.at !== 'number') return <span key={i}>{sg.t}</span>;
        const k = ease(c.t, sg.at, 0.45, CAM_EASE);
        return (
          <span key={i} style={{background: `linear-gradient(90deg, ${rgba(color, 0.35)} ${k * 100}%, transparent ${k * 100}%)`,
            borderRadius: size * 0.12, padding: `0 ${size * 0.06}px`, margin: `0 -${size * 0.06}px`}}>{sg.t}</span>
        );
      })}
    </>
  );
};

const Avatar: React.FC<{d: any; size: number}> = ({d, size}) => {
  const a = d.avatar;
  return a?.src ? (
    <Img src={staticFile(a.src)} style={{width: size, height: size, borderRadius: d.platform === 'reddit' ? 99 : 99, objectFit: 'cover', flex: 'none'}} />
  ) : (
    <div style={{width: size, height: size, borderRadius: 99, flex: 'none', display: 'grid', placeItems: 'center',
      background: 'linear-gradient(135deg, #7A5CFF, #FF5A8A)', ...font(800, size * 0.42, 1), color: '#fff'}}>
      {(d.name || d.handle || '?').replace('@', '').slice(0, 1).toUpperCase()}
    </div>
  );
};

const Post: React.FC<{d: any}> = ({d}) => {
  const c = useC();
  const pf: keyof typeof POST_THEME = d.platform;
  const T = (c.th.dark ? POST_THEME : POST_LIGHT)[pf] ?? POST_THEME.x;
  const len = (d.text || '').length + (d.title || '').length;
  const size = len > 220 ? 36 : len > 140 ? 42 : 48;
  const Ico = ({I}: {I: any}) => <I size={30} color={T.mut} weight="regular" />;
  const stat = (I: any, v: any) => (v === undefined || v === null ? null : (
    <div style={{display: 'flex', alignItems: 'center', gap: 10, ...font(500, 28), letterSpacing: 0, color: T.mut}}><Ico I={I} />{fmtCount(v)}</div>
  ));
  return (
    <div style={{...pop(prog(c, d.atT ?? 0)), width: 880, background: T.bg, borderRadius: 34, border: `1.5px solid ${T.line}`,
      padding: '30px 36px 26px', boxShadow: c.th.shadow, boxSizing: 'border-box', textAlign: 'left', fontFamily: CAPTION_FONT}}>
      {pf === 'reddit' ? (
        <div style={{display: 'flex', alignItems: 'center', gap: 14, marginBottom: 16}}>
          <div style={{width: 52, height: 52, borderRadius: 99, background: T.accent, display: 'grid', placeItems: 'center'}}>
            <Ph.RedditLogo size={34} color="#fff" weight="fill" />
          </div>
          <div style={{...font(700, 28), letterSpacing: 0, color: T.ink}}>{d.community ?? 'r/community'}</div>
          <div style={{...font(500, 26), letterSpacing: 0, color: T.mut}}>· {d.time ?? '5h'} · {d.handle ?? 'u/user'}</div>
        </div>
      ) : (
        <div style={{display: 'flex', alignItems: 'center', gap: 18, marginBottom: 18}}>
          <Avatar d={d} size={76} />
          <div style={{flex: 1, minWidth: 0}}>
            <div style={{display: 'flex', alignItems: 'center', gap: 8}}>
              <div style={{...font(800, 32, 1.15), letterSpacing: '-0.01em', color: T.ink}}>{d.name ?? d.handle}</div>
              {d.verified ? <Ph.SealCheck size={30} color={pf === 'x' ? '#1D9BF0' : T.accent} weight="fill" /> : null}
            </div>
            <div style={{...font(500, 26, 1.2), letterSpacing: 0, color: T.mut}}>
              {pf === 'linkedin' ? (d.headline ?? '') : `${d.handle ?? ''}${d.time ? ' · ' + d.time : ''}`}
            </div>
            {pf === 'linkedin' && d.time ? <div style={{...font(500, 24), letterSpacing: 0, color: T.mut}}>{d.time} · 🌐</div> : null}
          </div>
          {pf === 'x' ? <Ph.DotsThree size={34} color={T.mut} /> : null}
        </div>
      )}
      {d.title ? <div style={{...font(700, size + 6, 1.2), letterSpacing: '-0.01em', color: T.ink, marginBottom: 10}}>{d.title}</div> : null}
      <div style={{...font(500, size, 1.32), letterSpacing: '-0.01em', color: T.ink, whiteSpace: 'pre-wrap'}}>
        <ReadAlong text={d.text} hls={d.highlight} color={pf === 'reddit' ? T.accent : pf === 'threads' ? '#8C8C8C' : T.accent} size={size} />
      </div>
      <div style={{display: 'flex', justifyContent: pf === 'linkedin' ? 'flex-start' : 'space-between', gap: 40, marginTop: 24,
        paddingTop: 16, borderTop: pf === 'x' ? 'none' : `1.5px solid ${T.line}`}}>
        {pf === 'reddit' ? (
          <>
            {stat(Ph.ArrowFatUp, d.likes)}{stat(Ph.ChatCircle, d.comments)}{stat(Ph.ShareFat, d.reposts)}
          </>
        ) : pf === 'linkedin' ? (
          <>
            {stat(Ph.ThumbsUp, d.likes)}{stat(Ph.ChatText, d.comments)}{stat(Ph.Repeat, d.reposts)}
          </>
        ) : (
          <>
            {stat(Ph.ChatCircle, d.comments)}{stat(Ph.Repeat, d.reposts)}{stat(Ph.Heart, d.likes)}{stat(Ph.ChartBar, d.views)}
          </>
        )}
      </div>
    </div>
  );
};

/** Vest: izdavač (logo + ime + datum), naslov krupno; ključne reči naslova dobijaju highlight kad se izgovore. */
const News: React.FC<{d: any}> = ({d}) => {
  const c = useC();
  const hls: any[] = d.highlight ?? [];
  const head: string = d.headline;
  const size = head.length > 70 ? 50 : head.length > 45 ? 58 : 66;
  // Delovi naslova: obeleženi izrazi (sa `at`) postaju Highlight, ostalo običan tekst.
  const segs: {t: string; at?: number}[] = [];
  let rest = head;
  hls.map((h) => ({t: txt(h), at: at0(h, 0.6)})).forEach((h) => {
    const i = rest.toLowerCase().indexOf(h.t.toLowerCase());
    if (i < 0) return;
    if (i > 0) segs.push({t: rest.slice(0, i)});
    segs.push({t: rest.slice(i, i + h.t.length), at: h.at});
    rest = rest.slice(i + h.t.length);
  });
  if (rest) segs.push({t: rest});
  return (
    <Glass glow={0.3} strong style={{...pop(prog(c, d.atT ?? 0)), width: 880, padding: '34px 40px 40px'}}>
      {d.image?.src ? (
        <div style={{height: 240, borderRadius: 18, overflow: 'hidden', marginBottom: 26}}>
          <Img src={staticFile(d.image.src)} style={{width: '100%', height: '100%', objectFit: 'cover',
            // lice u kadru: traka od 240 px se postavlja na lice (ne na sredinu slike, gde je često vrat)
            objectPosition: d.image.face && d.image.h ? `50% ${Math.round(Math.min(100, Math.max(0, (d.image.face.y + d.image.face.h * 0.3) / d.image.h * 100)))}%` : '50% 40%',
            transform: `scale(${1 + 0.05 * ease(c.t, 0, Math.max(1, c.dur))})`, transformOrigin: '50% 35%'}} />
        </div>
      ) : null}
      <div style={{display: 'flex', alignItems: 'center', gap: 18, marginBottom: 22}}>
        {d.logo?.src ? <LogoPlate f={d.logo} size={64} /> : null}
        <div style={{...font(800, 34), color: c.th.ink}}>{d.outlet}</div>
        {d.date ? <div style={{...font(600, 30), color: c.th.mut}}>· {d.date}</div> : null}
      </div>
      <div style={{...font(800, size, 1.14), letterSpacing: '-0.03em', color: c.th.ink, textAlign: 'left'}}>
        {segs.map((sg, i) => typeof sg.at === 'number'
          ? <Highlight key={i} at={sg.at} size={size}><span>{sg.t}</span></Highlight>
          : <span key={i}>{sg.t}</span>)}
      </div>
    </Glass>
  );
};

/** Pozadina je scena, ne zvezda: tih grid koji se gubi ka ivicama + dva blaga svetla u boji brenda. */
const Background: React.FC<{th: Theme; acc: string; t: number}> = ({th, acc, t}) => {
  const o1 = {x: 330 + Math.sin(t / 3.4) * 80, y: 420 + Math.cos(t / 4.0) * 50};
  const o2 = {x: 760 + Math.cos(t / 3.0) * 70, y: 600 + Math.sin(t / 3.6) * 60};
  return (
    <>
      <div style={{position: 'absolute', inset: 0, background: th.base}} />
      {[o1, o2].map((o, i) => (
        <div key={i} style={{position: 'absolute', left: o.x - 230, top: o.y - 230, width: 460, height: 460, borderRadius: 999,
          background: rgba(acc, i ? th.orb * 0.8 : th.orb), filter: 'blur(120px)'}} />
      ))}
      <div style={{position: 'absolute', inset: 0,
        backgroundImage: `linear-gradient(${th.grid} 2px, transparent 2px), linear-gradient(90deg, ${th.grid} 2px, transparent 2px)`,
        backgroundSize: '72px 72px',
        WebkitMaskImage: 'radial-gradient(ellipse 48% 52% at 50% 54%, #000 0%, rgba(0,0,0,0.6) 45%, transparent 100%)'}} />
      {th.dark ? (
        <div style={{position: 'absolute', left: 0, right: 0, bottom: 0, height: 140,
          background: 'linear-gradient(180deg, transparent, rgba(0,0,0,0.35))'}} />
      ) : (
        // Light: blaga senka od linije podele naviše — beli titl na liniji dobija dovoljno odvajanja od svetle podloge.
        // Više tačaka (ease) da nema vidljive "trake".
        <div style={{position: 'absolute', left: 0, right: 0, bottom: 0, height: LIGHT_SHADE.h,
          background: `linear-gradient(180deg, rgba(12,12,16,0) 0%, rgba(12,12,16,${LIGHT_SHADE.a * 0.12}) 35%, ` +
            `rgba(12,12,16,${LIGHT_SHADE.a * 0.4}) 62%, rgba(12,12,16,${LIGHT_SHADE.a * 0.75}) 84%, rgba(12,12,16,${LIGHT_SHADE.a}) 100%)`}} />
      )}
    </>
  );
};

const LIGHT_SHADE = {h: 300, a: 0.42}; // Light: senka iznad linije podele (visina px, najveća tamnoća)
const EXIT = 0.16; // s: moment izlazi (fade + blur + blago gore) tik pre sledećeg — novi ulazi na čistu podlogu

const Moment: React.FC<{it: TopItem; t: number; fps: number; th: Theme; acc: string; exit: number; height: number}> = ({it, t, fps, th, acc, exit, height}) => {
  const sf = Math.round(it.start * fps);
  const ctx: Ctx = {t: t - it.start, dur: it.end - it.start, fps, th, acc, hero: Boolean(it.data?.hero), sweep: Boolean(it.data?.sweep)};
  const drift = 1 + 0.02 * interpolate(t - it.start, [0, Math.max(0.6, it.end - it.start)], [0, 1],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.inOut(Easing.sin)});
  const out = exit > 0 ? Easing.in(Easing.cubic)(Math.min(1, exit)) : 0;
  const d = it.data;
  if (it.kind === 'photo' && d.src) {
    const pp = photoPlan(d, height);
    if (pp.mode !== 'frame') {
      return (
        <C.Provider value={ctx}>
          <div style={{position: 'absolute', left: 0, top: 0, width: 1080, height, opacity: (1 - out) * Math.min(1, ease(t - it.start, 0, 0.35) * 1.2),
            filter: out > 0.01 ? `blur(${out * 10}px)` : undefined}}>
            <PhotoFull d={d} plan={pp} />
          </div>
        </C.Provider>
      );
    }
  }
  if (it.kind === 'scene') {  // full-screen custom animacija: cela gornja polovina je pozornica
    return (
      <C.Provider value={ctx}>
        <div style={{position: 'absolute', left: 0, top: 0, width: 1080, height, opacity: (1 - out) * Math.min(1, ease(t - it.start, 0, 0.3) * 1.2),
          filter: out > 0.01 ? `blur(${out * 10}px)` : undefined}}>
          <Scene d={d} sf={sf} height={height} />
        </div>
      </C.Provider>
    );
  }
  const portrait = d.w && d.h && d.h / d.w > 1.15;
  if (it.kind === 'spotlight' || ((it.kind === 'video' || (it.kind === 'image' && !d.alpha)) && portrait && d.src)) {
    return (
      <C.Provider value={ctx}>
        <div style={{position: 'absolute', left: 0, top: 0, width: 1080, height, opacity: (1 - out) * Math.min(1, ease(t - it.start, 0, 0.35) * 1.2),
          filter: out > 0.01 ? `blur(${out * 10}px)` : undefined}}>
          {it.kind === 'spotlight' ? <Spotlight d={d} sf={sf} height={height} /> : <VerticalFull d={{...d, mkind: it.kind === 'video' ? 'video' : 'image'}} sf={sf} height={height} />}
        </div>
      </C.Provider>
    );
  }
  const pic = (it.kind === 'screenshot' || (it.kind === 'image' && !d.alpha) || (it.kind === 'post' && d.src)) && d.src && !d.cropped
    ? picPlan(d, height, it.kind) : null;
  if (pic && pic.mode !== 'frame') {
    return (
      <C.Provider value={ctx}>
        <div style={{position: 'absolute', left: 0, top: 0, width: 1080, height, opacity: (1 - out) * Math.min(1, ease(t - it.start, 0, 0.35) * 1.2),
          filter: out > 0.01 ? `blur(${out * 10}px)` : undefined}}>
          <PictureFull d={d} plan={pic} />
        </div>
      </C.Provider>
    );
  }
  const body = it.kind === 'stat' ? <Stat d={d} />
    : it.kind === 'week' ? <Week d={d} />
    : it.kind === 'steps' ? <Steps d={d} />
    : it.kind === 'flow' ? <Flow d={d} />
    : it.kind === 'versus' ? <Versus d={d} />
    : it.kind === 'chart' ? <Chart d={d} />
    : it.kind === 'checklist' ? <Checklist d={d} />
    : it.kind === 'chat' ? <Chat d={d} />
    : it.kind === 'filter' ? <FilterGrid d={d} />
    : it.kind === 'headline' ? <Headline d={d} />
    : it.kind === 'notify' ? <Notify d={d} />
    : it.kind === 'comment' ? <Comment d={d} />
    : it.kind === 'key' ? <Key d={d} />
    : it.kind === 'search' ? <Search d={d} />
    : it.kind === 'logo' ? <Logo d={d} />
    : it.kind === 'screenshot' && d.cropped ? <Media it={{...it, kind: 'image'}} sf={sf} />
    : it.kind === 'screenshot' || (it.kind === 'image' && !d.alpha && d.src) ? <Screenshot d={d} photo={it.kind === 'image'} />
    : it.kind === 'news' ? <News d={d} />
    : it.kind === 'photo' ? <PersonCard d={d} />
    : it.kind === 'mediatext' ? <MediaText d={d} sf={sf} />
    : it.kind === 'faceoff' ? <Faceoff d={d} sf={sf} />
    : it.kind === 'pillars' ? <Pillars d={d} />
    : it.kind === 'resource' ? <Resource d={d} />
    : it.kind === 'posts' ? <PostStack d={d} />
    : it.kind === 'post' && d.src ? <Screenshot d={d} />
    : it.kind === 'post' ? <Post d={d} />
    : <Media it={it} sf={sf} />;
  return (
    <C.Provider value={ctx}>
      <div style={{position: 'absolute', left: ZONE.x, top: ZONE.y, width: ZONE.w, height: ZONE.h,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        opacity: 1 - out, filter: out > 0.01 ? `blur(${out * 10}px)` : undefined,
        transform: `translateY(${-out * 24}px) scale(${drift * (1 - 0.05 * out)})`}}>
        {body}
      </div>
    </C.Provider>
  );
};

export const TopHalf: React.FC<{height: number; spec?: TopSpec | null}> = ({height, spec}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  useFontSpec();
  const th = THEMES[spec?.style ?? 'dark'];
  const acc = spec?.accent ?? '#FFE600';
  const t = frame / fps;
  const items = spec?.items ?? [];
  const idx = items.findIndex((x) => t >= x.start && t < x.end);
  const it = idx >= 0 ? items[idx] : null;
  const exit = it && idx < items.length - 1 ? Math.max(0, (t - (it.end - EXIT)) / EXIT) : 0;
  return (
    <div style={{position: 'absolute', left: 0, top: 0, width: 1080, height, overflow: 'hidden'}}>
      <Background th={th} acc={acc} t={t} />
      {it ? <Moment key={`m${it.start}`} it={it} t={t} fps={fps} th={th} acc={acc} exit={exit} height={height} /> : null}
    </div>
  );
};
