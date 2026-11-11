import {createContext, useContext, useEffect, useState} from 'react';
import {continueRender, delayRender, staticFile} from 'remotion';

export const C = {
  white: '#FFFFFF',
  amber: '#FFBF00',
  red: '#FF0000',
} as const;

export const CAPTION_FONT = 'CCC Inter';
export const HOOK_FONT = 'CCC Hook';
export const SERIF_FONT = 'CCC Serif';

/** Glow + senka iz CCC brifa. */
export const textGlow = (rgb = '255,255,255') =>
  `0 0 18px rgba(${rgb},0.28), 0 0 60px rgba(${rgb},0.12), 0 3px 10px rgba(0,0,0,0.55)`;

/** Sigurna zona za IG/TikTok UI (px na 1080×1920). */
export const SAFE = {x: 90, top: 220, bottom: 380};

/** Set fontova iz engine-a (engine/ccc/fonts.py → prop `font`): fajlovi pod imenima porodica + tracking. */
export type FontFace_ = {family: string; file: string; weight: string; stretch?: string};
export type FontSpec = {
  id: string;
  faces: FontFace_[];
  tracking: {caption: number; hook: number; stack: number};
  /** Samo CCC set: TikTok Sans ose za hook boks (opsz, wdth). */
  hookAxes?: {opsz: number; wdth: number} | null;
};

/** CCC podrazumevani (odobren izgled) — kad prop nije prosleđen (Studio, stari projekti). */
export const DEFAULT_FONT: FontSpec = {
  id: 'ccc',
  faces: [
    {family: CAPTION_FONT, file: 'Inter-Light.ttf', weight: '300'},
    {family: CAPTION_FONT, file: 'Inter-SemiBold.ttf', weight: '600'},
    {family: CAPTION_FONT, file: 'Inter-Bold.ttf', weight: '700'},
    {family: HOOK_FONT, file: 'TikTokSans-Variable.ttf', weight: '300 900', stretch: '75% 150%'},
  ],
  tracking: {caption: -0.045, hook: 0, stack: -0.03},
  hookAxes: {opsz: 36, wdth: 95},
};

export const FontCtx = createContext<FontSpec>(DEFAULT_FONT);
export const useFontSpec = () => useContext(FontCtx);

const loadFace = async (family: string, file: string, descriptors: FontFaceDescriptors) => {
  const face = new FontFace(family, `url('${staticFile(`fonts/${file}`)}')`, descriptors);
  await face.load();
  document.fonts.add(face);
};

/**
 * Učitava lokalne fontove (bez interneta) i blokira render dok nisu spremni.
 * Samo javno dostupni fontovi (OFL). Editorial Serif hook je uvek Instrument Serif.
 */
export const useCccFonts = (spec: FontSpec = DEFAULT_FONT) => {
  const [handle] = useState(() => delayRender('CCC fontovi'));
  const [ready, setReady] = useState(false);
  useEffect(() => {
    Promise.all([
      ...spec.faces.map((f) =>
        loadFace(f.family, f.file, {weight: f.weight, ...(f.stretch ? {stretch: f.stretch} : {})}),
      ),
      loadFace(SERIF_FONT, 'InstrumentSerif-Regular.ttf', {weight: '400'}), // hook Stil 2
    ]).then(() => {
      setReady(true);
      continueRender(handle);
    });
  }, [handle, spec.id]);
  return ready;
};
