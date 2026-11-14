import React from 'react';
import {Easing, interpolate} from 'remotion';
import {UI_FONT} from '../style';

/**
 * Zajedničko jezgro App UI kita (AppUI.tsx = moment + slojevi; AppPhone.tsx / AppDesk.tsx = skinovi faze 1).
 * Skin = osnova aplikacije + "sidra" (imenovani delovi u dizajn koordinatama) na koja ciljaju kursor, kamera i meni.
 */

export type P = {d: any; t: number; dur: number; acc: string; dark: boolean; height: number};
export type Rect = {x: number; y: number; w: number; h: number};
export type Pal = {bg: string; rail: string; card: string; line: string; ink: string; mut: string; bubble: string; menu: string};

export const W = 900, H = 600;  // desktop prozor (dizajn pikseli)
export const PW = 430, PH = 932;  // telefon (iPhone Pro Max tačke)
export const EO = Easing.bezier(0.16, 1, 0.3, 1);
export const GLIDE = Easing.bezier(0.42, 0.08, 0.22, 1);
export const POP = Easing.bezier(0.34, 1.5, 0.64, 1);
export const ease = (t: number, from: number, len: number, curve: (n: number) => number = EO) =>
  interpolate(t - from, [0, len], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: curve});
export const T = (x: any, fb: number) => (typeof x?.atT === 'number' ? x.atT : fb);
export const txt = (x: any) => (typeof x === 'string' ? x : x == null ? '' : String(x?.text ?? x?.label ?? x?.name ?? (typeof x === 'number' ? x : '')));
export const RED = '#FF4D4D';
export const rgba = (hex: string, a: number) =>
  `rgba(${parseInt(hex.slice(1, 3), 16)},${parseInt(hex.slice(3, 5), 16)},${parseInt(hex.slice(5, 7), 16)},${a})`;
export const ui = (w: number, size: number, color: string, lh = 1.25): React.CSSProperties =>
  ({fontFamily: `"${UI_FONT}", "Inter", sans-serif`, fontWeight: w, fontSize: size, color, lineHeight: lh, letterSpacing: '-0.01em'});
export const center = (r: Rect) => ({x: r.x + r.w / 2, y: r.y + r.h / 2});
export const abs = (r: Rect, extra: React.CSSProperties = {}): React.CSSProperties =>
  ({position: 'absolute', left: r.x, top: r.y, width: r.w, height: r.h, boxSizing: 'border-box', ...extra});

/** Broj koji broji od `from` do `to` posle `at` (vrednost može biti broj, "12.4K", "$1,200" ili {from, to, at}). */
export const parseNum = (v: any): number => {
  if (typeof v === 'number') return v;
  const s = String(v ?? '').replace(/[,\s$€£]/g, '');
  const m = /^(-?\d+(?:\.\d+)?)([kKmMbB]?)/.exec(s);
  if (!m) return NaN;
  const mul = {k: 1e3, m: 1e6, b: 1e9}[m[2].toLowerCase() as 'k' | 'm' | 'b'] ?? 1;
  return parseFloat(m[1]) * mul;
};
export const countAt = (v: any, t: number, fallbackAt = 0): number => {
  if (v && typeof v === 'object' && !Array.isArray(v)) {
    const to = parseNum(v.to ?? v.value ?? v.text);
    const from = parseNum(v.start ?? 0);
    const k = ease(t, T(v, fallbackAt), 1.3, Easing.bezier(0.25, 0.1, 0.25, 1));
    return from + (to - from) * k;
  }
  return parseNum(v);
};
/** Instagram format: 9,876 · 12.4K · 1.2M */
export const fmtIG = (n: number): string => {
  if (!isFinite(n)) return '';
  const a = Math.abs(n);
  if (a >= 1e6) return `${(n / 1e6).toFixed(a >= 1e7 ? 0 : 1).replace(/\.0$/, '')}M`;
  if (a >= 1e4) return `${(n / 1e3).toFixed(a >= 1e5 ? 0 : 1).replace(/\.0$/, '')}K`;
  return Math.round(n).toLocaleString('en-US');
};
export const fmtNum = (n: number, like: any): string => {
  const s = String((like && typeof like === 'object' ? like.to ?? like.value : like) ?? '');
  const pre = /^\s*([$€£])/.exec(s)?.[1] ?? '';
  const dec = /\.(\d+)/.exec(s.replace(/[kKmM].*$/, ''))?.[1]?.length ?? 0;
  if (/[kKmM]\s*$/.test(s)) return pre + fmtIG(n);
  return pre + n.toLocaleString('en-US', {minimumFractionDigits: dec, maximumFractionDigits: dec});
};

// ------------------------------------------------------------------ stanje u trenutku t
export type St = {
  t: number; d: any; acc: string; dark: boolean; pal: Pal; app: string;
  typed: string; typing: boolean; caret: boolean; sendP: number; sent: string; tabs: any[]; activeTab: number;
};
export type Skin = {
  anchors: (st: St) => Record<string, Rect>;
  menuFrom: string;
  Body: React.FC<{st: St; a: Record<string, Rect>}>;
  pal?: {light: Pal; dark: Pal};
  frame?: 'window' | 'phone';           // prozor (desktop) ili telefon
  size?: {w: number; h: number};       // dizajn veličina (podrazumevano 900 × 600)
  base?: (st: St, a: Record<string, Rect>) => {x: number; y: number; s: number};  // početni kadar
  maxZoom?: number;
  chrome?: boolean;                     // false = skin sam crta gornju traku (bez semafora)
  autoZoom?: (st: St, a: Record<string, Rect>) => {to: string; T: number; scale?: number}[];  // kad plan ne zada zoom
};

export const Caret: React.FC<{st: St; size: number; color: string}> = ({st, size, color}) =>
  st.caret ? <span style={{display: 'inline-block', width: 2.5, height: size * 1.05, background: color, marginLeft: 2, verticalAlign: 'text-bottom',
    opacity: Math.floor(st.t * 2.2) % 2 === 0 ? 1 : 0}} /> : null;

export const typedAt = (inp: any, t: number) => {
  if (!inp) return {s: '', on: false, full: false};
  const s = txt(inp);
  const T0 = T(inp, 0.4);
  const len = Math.min(1.5, Math.max(0.5, s.length * 0.05));
  const k = interpolate(t - T0, [0, len], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return {s: s.slice(0, Math.round(k * s.length)), on: t >= T0 - 0.25, full: k >= 1};
};

/** Element liste koji "stiže" na reč: k 0→1 (ulaz), i redosled — novi ulaze na vrh i guraju ostale dole. */
export const arrivals = (rows: any[], t: number) => {
  const withT = rows.map((r, i) => ({r, i, T: typeof r?.atT === 'number' ? r.atT : -1}));
  const visible = withT.filter((x) => x.T < 0 || t >= x.T - 0.05);
  // stigli (sa at) na vrh, najnoviji prvi; stari (bez at) ispod, svojim redom
  const fresh = visible.filter((x) => x.T >= 0).sort((a, b) => b.T - a.T);
  const old = visible.filter((x) => x.T < 0);
  return [...fresh, ...old].map((x) => ({...x, k: x.T < 0 ? 1 : ease(t, x.T - 0.05, 0.45)}));
};
/** Glatka pozicija reda: koliko je redova (koji su već ušli) iznad njega — klizi, ne skače. */
export const slotY = (list: {T: number; k: number}[], idx: number, rowH: number) => {
  let y = 0;
  for (let j = 0; j < idx; j++) y += rowH * list[j].k;
  return y;
};

/** Ikonice aplikacija (crtane, bez preuzimanja) za notifikacije, čvorove automatizacije i inbox. */
export const APP_COLORS: Record<string, string> = {
  stripe: '#635BFF', instagram: '#E1306C', gmail: '#EA4335', shopify: '#5E8E3E', calendar: '#1A73E8', messages: '#34C759',
  whatsapp: '#25D366', slack: '#4A154B', paypal: '#003087', sheets: '#0F9D58', notion: '#111111', openai: '#0D0D0D',
  claude: '#D97757', webhook: '#FF6D5A', typeform: '#262627', calendly: '#006BFF', hubspot: '#FF7A59', zoom: '#2D8CFF',
  tiktok: '#111111', youtube: '#FF0000', linkedin: '#0A66C2', x: '#000000', discord: '#5865F2', airtable: '#18BFFF',
};
