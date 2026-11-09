/**
 * Deo originalnog snimka koji ostaje. srcStart/srcEnd = tačan isečak zvuka (s);
 * vFrom/vFrames = koji izvorni frejmovi idu u sliku (engine ih raspoređuje da prate zvuk ±½ frejma).
 */
export type Segment = {srcStart: number; srcEnd: number; vFrom?: number; vFrames?: number};

/** Jedan titl: 2–4 reči, vreme na IZLAZNOJ vremenskoj liniji (posle rezova), u sekundama. */
export type CaptionWord = {text: string; start: number};
export type CaptionChunk = {text: string; start: number; end: number; wt?: CaptionWord[]; key?: number; emphasis?: string[]};
/** clean = Stil 1 (blur-in) · karaoke = Stil 2 (pop + aktivna reč u boji) · box = Stil 3 (crn boks, reči se pune)
 *  · minimal = Stil 4 (glavna reč Inter Bold, ostalo Inter Light). */
export type CaptionStyle = 'clean' | 'karaoke' | 'box' | 'minimal';

/** box = Stil 1 (TikTok boks) · serif = Stil 2 (Editorial Serif) · color = Stil 3 (Color Block) · stack = Stil 4 (Stacked). */
export type HookStyle = 'box' | 'serif' | 'color' | 'stack';

export type HookSpec = {
  style?: HookStyle;
  /** Color Block: boja boksa (brend) i teksta (crna/bela po kontrastu). */
  bg?: string;
  fg?: string;
  /** Stacked: veličina fonta i visina oblika po delu, preklapanje oblika (px). */
  sizes?: number[];
  heights?: number[];
  overlap?: number;
  /** Tekst koji je uneo klijent, već prelomljen u redove (engine). */
  lines: string[];
  /** Razmak redova (px) — engine ga računa po stilu. */
  pitch?: number;
  /** y vrha prvog boksa (px na 1080×1920) — ispod brade. */
  y: number;
  start: number;
  end: number;
};

/** Kamera za jedan segment: skala na početku/kraju segmenta, centar zuma (px na 1080×1920). */
export type CameraCue = {seg: number; from: number; to: number; ox: number; oy: number};

export type EditProps = {
  /** Putanja snimka u odnosu na public/. */
  video: string;
  /** Isečen zvuk (voice.wav iz engine-a). Ako postoji, zvuk snimka se utišava. */
  audio?: string;
  /** fps kompozicije = fps snimka (bez pretvaranja 25→30). */
  fps: number;
  segments: Segment[];
  captions: CaptionChunk[];
  hook?: HookSpec | null;
  /** Punch-in / push-in po segmentu (engine/ccc/camera.py). */
  camera?: CameraCue[];
  /** Vertikalni centar titla (px na 1080×1920) — tačno ispod brade. */
  captionY: number;
  captionStyle?: CaptionStyle;
  /** Boja naglaska (Karaoke) — boja brenda klijenta, #RRGGBB. */
  captionAccent?: string;
};
