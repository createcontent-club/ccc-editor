import React from 'react';
import {AbsoluteFill, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import type {HookSpec} from '../types';
import {CAPTION_FONT, HOOK_FONT, SERIF_FONT, useFontSpec} from '../style';

/**
 * Text hook po referenci (references/hook/, prve ~3 s), izmereno na 720 i preneto na 1080:
 *  - TikTok Sans (OFL, Google Fonts) Bold 700, širina 95, 81 px, crn tekst;
 *  - svaki red u svom belom boksu: visina 129 px, razmak redova 84 px (boksovi se preklapaju),
 *    30 px levo/desno od teksta, zaobljenje 15 px;
 *  - centrirano, vrh hooka 0.45 × visina lica ispod brade (engine računa `y`);
 *  - BEZ animacije: stoji od prvog frejma, nestaje naglo (na rezu ~3.4 s).
 * Prelom redova radi engine (kao TikTok: red se puni do ~834 px teksta).
 */
export const HOOK_STYLE = {
  fontSize: 81,
  boxHeight: 129,
  linePitch: 84,
  padX: 30,
  radius: 15,
};

/**
 * Hook Stil 2 "Editorial Serif": Instrument Serif 96 px, beli, blago zbijen (-0.02em), bez boksa,
 *  jača meka senka da se čita na svakoj pozadini; balansirani redovi (engine); bez animacije.
 */
const SerifHook: React.FC<{hook: HookSpec}> = ({hook}) => (
  <AbsoluteFill>
    {hook.lines.map((line, i) => (
      <div
        key={i}
        style={{
          position: 'absolute',
          top: hook.y + i * (hook.pitch ?? 100),
          left: 0,
          right: 0,
          textAlign: 'center',
          whiteSpace: 'nowrap',
          fontFamily: SERIF_FONT,
          fontSize: 96,
          lineHeight: '104px',
          letterSpacing: '-0.02em',
          color: '#FFFFFF',
          textShadow: '0 4px 18px rgba(0,0,0,0.55), 0 2px 6px rgba(0,0,0,0.45)',
        }}
      >
        {line}
      </div>
    ))}
  </AbsoluteFill>
);

/**
 * Hook Stil 4 "Stacked" (po slici klijenta): dva oblika jedan na drugom — gornji beli boks sa krupnim
 *  crnim tekstom, donji manji boks u boji brenda (tekst crn/beo po kontrastu) priljubljen odmah ispod
 *  gornjeg (bez razmaka, bez preklapanja); isti font i debljina u oba (Inter Bold, tracking -0.03em).
 *  ULAZ: oba oblika sa blagim bounce-om i malim pomakom odozdo — prvo gornji, pa donji 4 frejma kasnije.
 *  IZLAZ: trenutan.
 */
const STACK_DELAY = 4; // frejma između gornjeg i donjeg oblika
const StackHook: React.FC<{hook: HookSpec; frame: number; fps: number}> = ({hook, frame, fps}) => {
  const fs = useFontSpec();
  const sizes = hook.sizes ?? [96, 52];
  const heights = hook.heights ?? [131, 78];
  const overlap = hook.overlap ?? 0;
  const shapes = [
    {bg: '#FFFFFF', fg: '#000000', radius: 18, padX: 34},
    {bg: hook.bg ?? '#FF3B30', fg: hook.fg ?? '#FFFFFF', radius: 14, padX: 22},
  ];
  let top = hook.y;
  return (
    <AbsoluteFill>
      {hook.lines.map((line, i) => {
        const y = top;
        top += heights[i] - overlap;
        const s = spring({frame: frame - Math.round(hook.start * fps) - i * STACK_DELAY, fps,
          config: {damping: 11, stiffness: 170, mass: 0.6}});
        const sh = shapes[i] ?? shapes[1];
        return (
          <div
            key={i}
            style={{
              position: 'absolute',
              top: y,
              left: 0,
              right: 0,
              display: 'flex',
              justifyContent: 'center',
              zIndex: 10 + i, // donji oblik preko gornjeg (zalazi preko njegove ivice)
              opacity: Math.min(1, s * 3),
              transform: `translateY(${(1 - s) * 18}px) scale(${0.86 + 0.14 * s})`,
            }}
          >
            <div
              style={{
                height: heights[i],
                lineHeight: `${heights[i]}px`,
                padding: `0 ${sh.padX}px`,
                borderRadius: sh.radius,
                background: sh.bg,
                color: sh.fg,
                fontFamily: CAPTION_FONT,
                fontWeight: 700,
                fontSize: sizes[i],
                letterSpacing: `${fs.tracking.stack}em`,
                whiteSpace: 'nowrap',
              }}
            >
              {line}
            </div>
          </div>
        );
      })}
    </AbsoluteFill>
  );
};

export const Hook: React.FC<{hook: HookSpec; fontsReady: boolean}> = ({hook, fontsReady}) => {
  const fs = useFontSpec();
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const t = frame / fps;
  if (!fontsReady || t < hook.start || t >= hook.end) return null;
  if (hook.style === 'serif') return <SerifHook hook={hook} />;
  if (hook.style === 'stack') return <StackHook hook={hook} frame={frame} fps={fps} />;
  const s = HOOK_STYLE;

  const row = (i: number, extra: React.CSSProperties = {}): React.CSSProperties => ({
    position: 'absolute',
    top: hook.y + i * s.linePitch,
    left: 0,
    right: 0,
    display: 'flex',
    justifyContent: 'center',
    ...extra,
  });
  // Stil 3 "Color Block": iste mere, boks u boji brenda, tekst 800, oštrije ivice; boju teksta bira engine.
  const block = hook.style === 'color';
  const bg = block ? hook.bg ?? '#FFE600' : '#FFFFFF';
  const fg = block ? hook.fg ?? '#000000' : '#000000';
  const box: React.CSSProperties = {
    height: s.boxHeight,
    lineHeight: `${s.boxHeight}px`,
    padding: `0 ${s.padX}px`,
    borderRadius: block ? 10 : s.radius,
    fontFamily: HOOK_FONT,
    fontSize: s.fontSize,
    fontWeight: block ? 800 : 700,
    letterSpacing: `${fs.tracking.hook}em`,
    // CCC set: TikTok Sans sa osama iz reference; ostali setovi: obična težina (varijabilni ili statični fajl).
    ...(fs.hookAxes
      ? {fontVariationSettings: `'wght' ${block ? 800 : 700}, 'wdth' ${fs.hookAxes.wdth}, 'opsz' ${fs.hookAxes.opsz}`}
      : {}),
    whiteSpace: 'nowrap',
  };

  // Dva sloja, kao u TikTok-u: prvo SVI beli boksovi, pa SAV tekst preko njih — boksovi se
  // preklapaju, pa bi inače boks jednog reda prekrio vrhove/repove slova susednog reda.
  return (
    <AbsoluteFill>
      {hook.lines.map((line, i) => (
        <div key={`b${i}`} style={row(i)}>
          <div style={{...box, background: bg, color: 'transparent'}}>{line}</div>
        </div>
      ))}
      {hook.lines.map((line, i) => (
        <div key={`t${i}`} style={row(i)}>
          <div style={{...box, color: fg}}>{line}</div>
        </div>
      ))}
    </AbsoluteFill>
  );
};
