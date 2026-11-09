import {useEffect, useState} from 'react';
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

const loadFace = async (family: string, file: string, descriptors: FontFaceDescriptors) => {
  const face = new FontFace(family, `url('${staticFile(`fonts/${file}`)}')`, descriptors);
  await face.load();
  document.fonts.add(face);
};

/**
 * Učitava lokalne fontove (bez interneta) i blokira render dok nisu spremni.
 * Samo javno dostupni fontovi (OFL): Inter (titlovi), TikTok Sans (hook Stil 1), Instrument Serif (hook Stil 2).
 */
export const useCccFonts = () => {
  const [handle] = useState(() => delayRender('CCC fontovi'));
  const [ready, setReady] = useState(false);
  useEffect(() => {
    Promise.all([
      loadFace(CAPTION_FONT, 'Inter-SemiBold.ttf', {weight: '600'}),
      loadFace(CAPTION_FONT, 'Inter-Light.ttf', {weight: '300'}), // Stil 4: ostatak teksta
      loadFace(CAPTION_FONT, 'Inter-Bold.ttf', {weight: '700'}), // Stil 4: glavna reč
      loadFace(HOOK_FONT, 'TikTokSans-Variable.ttf', {weight: '300 900', stretch: '75% 150%'}),
      loadFace(SERIF_FONT, 'InstrumentSerif-Regular.ttf', {weight: '400'}), // hook Stil 2
    ]).then(() => {
      setReady(true);
      continueRender(handle);
    });
  }, [handle]);
  return ready;
};
