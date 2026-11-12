import React from 'react';
import {AbsoluteFill, Audio, OffthreadVideo, Sequence, interpolate, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import type {CameraCue, EditProps, Segment} from './types';
import {Captions} from './components/Captions';
import {Hook} from './components/Hook';
import {TopHalf} from './components/TopHalf';
import {DEFAULT_FONT, FontCtx, useCccFonts} from './style';

export const segmentFrames = (s: Segment, fps: number) => s.vFrames ?? Math.round((s.srcEnd - s.srcStart) * fps);
const segmentFrom = (s: Segment, fps: number) => s.vFrom ?? Math.round(s.srcStart * fps);

/** Zum jednog segmenta oko lica: skala ide od cue.from do cue.to (spor push-in), ≥ 1 → bez crnih ivica. */
const Shot: React.FC<{cue?: CameraCue; dur: number; children: React.ReactNode}> = ({cue, dur, children}) => {
  const f = useCurrentFrame();
  if (!cue) return <AbsoluteFill>{children}</AbsoluteFill>;
  const scale = interpolate(f, [0, Math.max(1, dur)], [cue.from, cue.to], {extrapolateRight: 'clamp'});
  return (
    <AbsoluteFill style={{transform: `scale(${scale})`, transformOrigin: `${cue.ox}px ${cue.oy}px`}}>
      {children}
    </AbsoluteFill>
  );
};

/** Nedestruktivni rez: zadržani segmenti originala poređani jedan za drugim. */
const Footage: React.FC<{video: string; segments: Segment[]; muted: boolean; camera?: CameraCue[]; srcFps: number}> = ({
  video,
  segments,
  muted,
  camera,
  srcFps,
}) => {
  const {fps} = useVideoConfig();
  const mult = Math.max(1, Math.round(fps / srcFps)); // fpsMult: frejmovi izvora → frejmovi kompozicije
  let at = 0;
  return (
    <>
      {segments.map((s, i) => {
        const dur = segmentFrames(s, srcFps) * mult;
        if (dur <= 0) return null; // isečak zvuka kraći od pola frejma — nema sopstveni frejm
        const el = (
          <Sequence key={`${s.srcStart}-${s.srcEnd}`} from={at} durationInFrames={dur} name={`seg ${s.srcStart.toFixed(2)}–${s.srcEnd.toFixed(2)}s`}>
            <Shot cue={camera?.find((c) => c.seg === i)} dur={dur}>
              <OffthreadVideo src={staticFile(video)} trimBefore={segmentFrom(s, srcFps) * mult} muted={muted} />
            </Shot>
          </Sequence>
        );
        at += dur;
        return el;
      })}
    </>
  );
};

/** Slojevi (dole → gore): snimak (sa zumom) → hook → titlovi; tekst se ne zumira. */
export const CccEdit: React.FC<EditProps> = ({video, audio, segments, captions, hook, captionY, captionStyle, captionAccent, camera, font, layout, captionsFrom, top, fps}) => {
  const spec = font ?? DEFAULT_FONT;
  const fontsReady = useCccFonts(spec);
  return (
    <FontCtx.Provider value={spec}>
    <AbsoluteFill style={{background: '#000'}}>
      {layout?.type === 'split' ? (
        <>
          {/* Gornja polovina: momenti iz plana (engine/ccc/visuals.py), Dark/Light. */}
          <TopHalf height={layout.line} spec={top} />
          {/* Donja polovina: isečak izvornog kadra (cropY → linija), bez zuma. */}
          <div style={{position: 'absolute', left: 0, top: layout.line, width: 1080, height: 1920 - layout.line, overflow: 'hidden'}}>
            <div style={{position: 'absolute', left: 0, top: -(layout.cropY ?? 0), width: 1080, height: 1920}}>
              <Footage video={video} segments={segments} muted={Boolean(audio)} camera={undefined} srcFps={fps} />
            </div>
          </div>
        </>
      ) : (
        <Footage video={video} segments={segments} muted={Boolean(audio)} camera={camera} srcFps={fps} />
      )}
      {/* Zvuk je već isečen u engine-u, sa mikro-fade-om na rezovima (bez klikova). */}
      {audio ? <Audio src={staticFile(audio)} /> : null}
      {hook ? <Hook hook={hook} fontsReady={fontsReady} srcFps={fps} /> : null}
      {/* Hook i titlovi su na ekranu istovremeno; engine postavlja hook ispod titla ili iznad glave. */}
      {fontsReady ? <Captions captions={captions} y={captionY} style={captionStyle ?? 'clean'} accent={captionAccent} from={captionsFrom ?? 0} srcFps={fps} /> : null}
    </AbsoluteFill>
    </FontCtx.Provider>
  );
};
