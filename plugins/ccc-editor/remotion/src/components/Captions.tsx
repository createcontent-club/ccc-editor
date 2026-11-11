import React from 'react';
import {AbsoluteFill, Easing, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import type {CaptionChunk, CaptionStyle} from '../types';
import {CAPTION_FONT, useFontSpec} from '../style';

const easeOutCubic = (p: number) => 1 - Math.pow(1 - p, 3);
const clamp01 = (v: number) => Math.min(1, Math.max(0, v));

const rowStyle = (y: number): React.CSSProperties => ({
  position: 'absolute',
  top: y,
  left: 0,
  right: 0,
  transform: 'translateY(-50%)',
  textAlign: 'center',
  whiteSpace: 'nowrap',
  lineHeight: 1,
});

/**
 * STIL 1 "Clean" — po referenci (references/captions/, prvih 5 s), izmereno frejm po frejm:
 *  Inter SemiBold 58 px, tracking -45, beli, bez interpunkcije i naglasaka, meka senka;
 *  ULAZ fade + blur ~4 frejma (25% → 80% → 95% → 100%), bez pomeranja; IZLAZ trenutan.
 */
/** Izgled svih titlova (Stil 1, odobren). Kontura (stroke) se na titlovima NIKAD ne koristi. */
const CAPTION_LOOK: React.CSSProperties = {
  fontFamily: CAPTION_FONT,
  fontWeight: 600,
  fontSize: 58,
  letterSpacing: '-0.045em', // tracking -45
  color: '#FFFFFF',
  textShadow: '0 4px 12px rgba(0,0,0,0.5), 0 1px 3px rgba(0,0,0,0.35)',
};
/** Isti izgled u svakom setu fontova; tracking prati izabrani font (Inter: -0.045em). */
const useLook = (): React.CSSProperties => ({...CAPTION_LOOK, letterSpacing: `${useFontSpec().tracking.caption}em`});

const ENTER = 0.16;
const Clean: React.FC<{chunk: CaptionChunk; t: number; y: number}> = ({chunk, t, y}) => {
  const look = useLook();
  const e = easeOutCubic(clamp01((t - chunk.start) / ENTER));
  const blur = 10 * (1 - e);
  return (
    <div
      style={{
        ...rowStyle(y),
        ...look,
        opacity: 0.3 + 0.7 * e,
        filter: blur > 0.05 ? `blur(${blur.toFixed(2)}px)` : undefined,
      }}
    >
      {chunk.text}
    </div>
  );
};

/**
 * STIL 2 "Karaoke": isti izgled kao Stil 1 (Inter SemiBold 58, tracking -45, beli, meka senka,
 *  originalna slova, bez konture), plus karaoke animacija: reč koja se upravo izgovara je u boji brenda
 *  i kratko "iskoči" (1.0 → 1.08 → 1.03); ulaz titla: pop 0.85 → 1 kroz ~3 frejma; izlaz trenutan.
 */
export const DEFAULT_ACCENT = '#FFE600'; // CCC žuta; klijent bira boju brenda

const Karaoke: React.FC<{chunk: CaptionChunk; t: number; y: number; fps: number; accent: string}> = ({
  chunk,
  t,
  y,
  fps,
  accent,
}) => {
  const look = useLook();
  const words = chunk.wt?.length ? chunk.wt : chunk.text.split(' ').map((text) => ({text, start: chunk.start}));
  let active = 0;
  words.forEach((w, i) => {
    if (t >= w.start - 0.5 / fps) active = i;
  });
  const enter = interpolate(t - chunk.start, [0, 3 / fps], [0.85, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.back(2)),
  });
  return (
    <div
      style={{
        ...rowStyle(y),
        ...look,
        transform: `translateY(-50%) scale(${enter})`,
      }}
    >
      {words.map((w, i) => {
        const on = i === active;
        const pop = on
          ? interpolate(t - w.start, [0, 2 / fps, 5 / fps], [1, 1.08, 1.03], {
              extrapolateLeft: 'clamp',
              extrapolateRight: 'clamp',
            })
          : 1;
        return (
          <span
            key={i}
            style={{
              display: 'inline-block',
              margin: '0 0.15em', // razmak = obična razmaknica + mesta za "pop" aktivne reči
              color: on ? accent : '#FFFFFF',
              transform: `scale(${pop})`,
            }}
          >
            {w.text}
          </span>
        );
      })}
    </div>
  );
};

/**
 * STIL 3 "Box Fill": isti tekst kao Stil 1 (Inter SemiBold 58, tracking -45, beli) na crnom boksu
 *  85% neprozirnosti; neizgovorene reči su na 20% neprozirnosti, a reči se "pune" do 100% jedna po
 *  jedna tačno kad su izgovorene (i ostaju pune); BEZ animacije pojavljivanja — tvrd prelaz između titlova.
 */
const BOX_BG = 'rgba(0, 0, 0, 0.85)';
const DIM = 0.2;
const BoxFill: React.FC<{chunk: CaptionChunk; t: number; y: number; fps: number}> = ({chunk, t, y, fps}) => {
  const look = useLook();
  const words = chunk.wt?.length ? chunk.wt : chunk.text.split(' ').map((text) => ({text, start: chunk.start}));
  return (
    <div style={{...rowStyle(y), display: 'flex', justifyContent: 'center'}}>
      <div
        style={{
          ...look,
          textShadow: 'none', // na crnom boksu senka nije potrebna
          background: BOX_BG,
          borderRadius: 18,
          padding: '16px 26px 18px',
        }}
      >
        {words.map((w, i) => {
          // reč se "napuni" do 100% za ~2 frejma kad počne da se izgovara
          const fill = interpolate(t - w.start, [-0.5 / fps, 2 / fps], [DIM, 1], {
            extrapolateLeft: 'clamp',
            extrapolateRight: 'clamp',
          });
          return (
            <span key={i} style={{opacity: fill}}>
              {i > 0 ? ' ' : ''}
              {w.text}
            </span>
          );
        })}
      </div>
    </div>
  );
};

/**
 * STIL 4 "Minimal Contrast": isti tekst kao Stil 1 (Inter 58, tracking -45, beli, meka senka),
 *  ali jedna glavna reč u svakom titlu je Inter Bold, a ostatak Inter Light — kontrast nosi stil.
 *  Animacija kao Stil 1 (fade + blur ulaz ~4 frejma, trenutan izlaz). Glavnu reč bira engine (`key`).
 */
const Minimal: React.FC<{chunk: CaptionChunk; t: number; y: number}> = ({chunk, t, y}) => {
  const look = useLook();
  const e = easeOutCubic(clamp01((t - chunk.start) / ENTER));
  const blur = 10 * (1 - e);
  const words = chunk.wt?.length ? chunk.wt.map((w) => w.text) : chunk.text.split(' ');
  return (
    <div
      style={{
        ...rowStyle(y),
        ...look,
        opacity: 0.3 + 0.7 * e,
        filter: blur > 0.05 ? `blur(${blur.toFixed(2)}px)` : undefined,
      }}
    >
      {words.map((w, i) => (
        <span key={i} style={{fontWeight: i === (chunk.key ?? 0) ? 700 : 300}}>
          {i > 0 ? ' ' : ''}
          {w}
        </span>
      ))}
    </div>
  );
};

export const Captions: React.FC<{captions: CaptionChunk[]; y: number; style?: CaptionStyle; accent?: string}> = ({
  captions,
  y,
  style = 'clean',
  accent = DEFAULT_ACCENT,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const t = frame / fps;
  const chunk = captions.find((c) => t >= c.start - 0.5 / fps && t < c.end);
  if (!chunk) return null;
  return (
    <AbsoluteFill>
      {style === 'karaoke' ? (
        <Karaoke chunk={chunk} t={t} y={y} fps={fps} accent={accent} />
      ) : style === 'box' ? (
        <BoxFill chunk={chunk} t={t} y={y} fps={fps} />
      ) : style === 'minimal' ? (
        <Minimal chunk={chunk} t={t} y={y} />
      ) : (
        <Clean chunk={chunk} t={t} y={y} />
      )}
    </AbsoluteFill>
  );
};
