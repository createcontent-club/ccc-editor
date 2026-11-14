import React from 'react';
import * as Ph from '@phosphor-icons/react';
import {APP_COLORS, ui} from './appCore';

/** Crtani znakovi alata (bez preuzimanja) — isti u notifikacijama, inbox-u, čvorovima automatizacije. */

export const ClaudeMark: React.FC<{size: number; spin?: number; color?: string}> = ({size, spin = 0, color = '#D97757'}) => {
  const rays = [1, 0.78, 0.95, 0.72, 1, 0.82, 0.92, 0.7, 0.98, 0.8, 0.9, 0.74];
  return (
    <svg width={size} height={size} viewBox="-50 -50 100 100" style={{transform: `rotate(${spin}deg)`}}>
      {rays.map((r, i) => (
        <rect key={i} x={-4.2} y={-48 * r} width={8.4} height={44 * r} rx={4.2} fill={color}
          transform={`rotate(${(i * 360) / rays.length + (i % 2 ? 6 : 0)})`} />
      ))}
    </svg>
  );
};
export const OpenAIMark: React.FC<{size: number; color: string}> = ({size, color}) => (
  <svg width={size} height={size} viewBox="-50 -50 100 100">
    {[0, 60, 120, 180, 240, 300].map((a) => (
      <rect key={a} x={-11} y={-40} width={22} height={52} rx={11} fill="none" stroke={color} strokeWidth={7}
        transform={`rotate(${a}) translate(0 -2)`} />
    ))}
  </svg>
);
export const NotionMark: React.FC<{size: number}> = ({size}) => (
  <svg width={size} height={size} viewBox="0 0 100 100">
    <rect x={8} y={8} width={84} height={84} rx={14} fill="#fff" stroke="#111" strokeWidth={7} />
    <text x={50} y={72} textAnchor="middle" fontFamily="Georgia, serif" fontWeight={700} fontSize={58} fill="#111">N</text>
  </svg>
);
export const SheetsMark: React.FC<{size: number}> = ({size}) => (
  <svg width={size * 0.78} height={size} viewBox="0 0 78 100">
    <path d="M6 0 H52 L78 26 V94 a6 6 0 0 1 -6 6 H6 a6 6 0 0 1 -6 -6 V6 a6 6 0 0 1 6 -6 Z" fill="#0F9D58" />
    <path d="M52 0 V20 a6 6 0 0 0 6 6 H78 Z" fill="#87CEAC" />
    <rect x={16} y={44} width={46} height={36} rx={3} fill="#fff" />
    <rect x={20} y={48} width={17} height={12} fill="#0F9D58" /><rect x={41} y={48} width={17} height={12} fill="#0F9D58" />
    <rect x={20} y={64} width={17} height={12} fill="#0F9D58" /><rect x={41} y={64} width={17} height={12} fill="#0F9D58" />
  </svg>
);
export const GmailMark: React.FC<{size: number}> = ({size}) => (
  <svg width={size} height={size * 0.75} viewBox="0 0 100 75">
    <path d="M7 75 H23 V36 L0 19 V68 a7 7 0 0 0 7 7 Z" fill="#4285F4" />
    <path d="M77 75 H93 a7 7 0 0 0 7 -7 V19 L77 36 Z" fill="#34A853" />
    <path d="M77 6 V36 L100 19 V10 C100 1 90 -3 83 2 Z" fill="#FBBC04" />
    <path d="M23 36 V6 L50 26 L77 6 V36 L50 56 Z" fill="#EA4335" />
    <path d="M0 10 V19 L23 36 V6 L17 2 C10 -3 0 1 0 10 Z" fill="#C5221F" />
  </svg>
);
export const IgGradient = 'radial-gradient(circle at 30% 107%, #fdf497 0%, #fdf497 5%, #fd5949 45%, #d6249f 60%, #285AEB 90%)';

/** Ikonica aplikacije u zaobljenom kvadratu (iOS stil). `app` = ime iz APP_COLORS ili bilo šta (prvo slovo + boja). */
export const AppIcon: React.FC<{app: string; size: number; radius?: number}> = ({app, size, radius}) => {
  const k = String(app || '').toLowerCase();
  const r = radius ?? size * 0.225;
  const box = (bg: string, child: React.ReactNode, extra: React.CSSProperties = {}) => (
    <div style={{width: size, height: size, borderRadius: r, background: bg, display: 'grid', placeItems: 'center', flex: 'none',
      overflow: 'hidden', ...extra}}>{child}</div>
  );
  const g = size * 0.58;
  switch (k) {
    case 'instagram': return box(IgGradient, <Ph.InstagramLogo size={g} weight="bold" color="#fff" />);
    case 'gmail': return box('#fff', <GmailMark size={size * 0.62} />, {boxShadow: 'inset 0 0 0 1px rgba(0,0,0,0.08)'});
    case 'stripe': return box('#635BFF', <span style={{...ui(800, size * 0.62, '#fff', 1), letterSpacing: '-0.04em'}}>S</span>);
    case 'shopify': return box('#5E8E3E', <Ph.ShoppingBag size={g} weight="fill" color="#fff" />);
    case 'calendar': {
      const day = new Date().getDate();
      return box('#fff', (
        <div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', lineHeight: 1}}>
          <span style={ui(700, size * 0.16, '#FF3B30', 1)}>FRI</span>
          <span style={ui(500, size * 0.5, '#111', 1)}>{day}</span>
        </div>
      ), {boxShadow: 'inset 0 0 0 1px rgba(0,0,0,0.08)'});
    }
    case 'messages': return box('linear-gradient(180deg,#5BF675,#0CBD2A)', <Ph.ChatCircle size={g} weight="fill" color="#fff" />);
    case 'whatsapp': return box('#25D366', <Ph.WhatsappLogo size={g} weight="fill" color="#fff" />);
    case 'slack': return box('#4A154B', <Ph.SlackLogo size={g} weight="bold" color="#fff" />);
    case 'paypal': return box('#003087', <Ph.PaypalLogo size={g} weight="fill" color="#fff" />);
    case 'sheets': return box('#fff', <SheetsMark size={size * 0.62} />, {boxShadow: 'inset 0 0 0 1px rgba(0,0,0,0.08)'});
    case 'notion': return box('#fff', <NotionMark size={size * 0.7} />, {boxShadow: 'inset 0 0 0 1px rgba(0,0,0,0.08)'});
    case 'openai': case 'chatgpt': return box('#0D0D0D', <OpenAIMark size={size * 0.6} color="#fff" />);
    case 'claude': return box('#F5F0E8', <ClaudeMark size={size * 0.64} />);
    case 'webhook': return box('#FF6D5A', <Ph.WebhooksLogo size={g} weight="bold" color="#fff" />);
    case 'typeform': return box('#262627', <span style={ui(700, size * 0.5, '#fff', 1)}>T</span>);
    case 'calendly': return box('#006BFF', <Ph.CalendarBlank size={g} weight="bold" color="#fff" />);
    case 'hubspot': return box('#FF7A59', <Ph.Users size={g} weight="fill" color="#fff" />);
    case 'zoom': return box('#2D8CFF', <Ph.VideoCamera size={g} weight="fill" color="#fff" />);
    case 'tiktok': return box('#111', <Ph.TiktokLogo size={g} weight="fill" color="#fff" />);
    case 'youtube': return box('#FF0000', <Ph.YoutubeLogo size={g} weight="fill" color="#fff" />);
    case 'linkedin': return box('#0A66C2', <Ph.LinkedinLogo size={g} weight="fill" color="#fff" />);
    case 'x': return box('#000', <Ph.XLogo size={g} weight="bold" color="#fff" />);
    case 'discord': return box('#5865F2', <Ph.DiscordLogo size={g} weight="fill" color="#fff" />);
    case 'airtable': return box('#18BFFF', <Ph.Table size={g} weight="fill" color="#fff" />);
    case 'schedule': case 'cron': return box('#7C5CFF', <Ph.Clock size={g} weight="bold" color="#fff" />);
    case 'code': return box('#FF9500', <Ph.Code size={g} weight="bold" color="#fff" />);
    case 'filter': case 'if': return box('#00A3A3', <Ph.FunnelSimple size={g} weight="bold" color="#fff" />);
    case 'ai': case 'agent': return box('#7C5CFF', <Ph.Robot size={g} weight="fill" color="#fff" />);
    case 'email': case 'mail': return box('#1A73E8', <Ph.EnvelopeSimple size={g} weight="fill" color="#fff" />);
    case 'database': case 'crm': return box('#5F6368', <Ph.Database size={g} weight="fill" color="#fff" />);
    default: {
      const bg = APP_COLORS[k] ?? '#5F6368';
      return box(bg, <span style={ui(800, size * 0.5, '#fff', 1)}>{String(app || '?').slice(0, 1).toUpperCase()}</span>);
    }
  }
};
export const APP_ICON_NAMES = ['instagram', 'gmail', 'stripe', 'shopify', 'calendar', 'messages', 'whatsapp', 'slack', 'paypal', 'sheets',
  'notion', 'openai', 'chatgpt', 'claude', 'webhook', 'typeform', 'calendly', 'hubspot', 'zoom', 'tiktok', 'youtube', 'linkedin', 'x',
  'discord', 'airtable', 'schedule', 'cron', 'code', 'filter', 'if', 'ai', 'agent', 'email', 'mail', 'database', 'crm'];
