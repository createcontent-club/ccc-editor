import React from 'react';
import {CalculateMetadataFunction, Composition} from 'remotion';
import {CccEdit, segmentFrames} from './CccEdit';
import type {EditProps} from './types';

const metadata: CalculateMetadataFunction<EditProps> = ({props}) => ({
  fps: props.fps,
  durationInFrames: Math.max(1, props.segments.reduce((sum, s) => sum + segmentFrames(s, props.fps), 0)),
});

/** Prava montaža: sve dolazi iz project.json (--props). Namerno bez ikakvog podrazumevanog teksta. */
const editDefaults: EditProps = {
  video: 'test/test-talk.mp4',
  fps: 30,
  segments: [{srcStart: 0, srcEnd: 6}],
  captions: [],
  hook: null,
  captionY: 1180,
};

/** Samo za proveru instalacije (tools/doctor.py): hook + titlovi na probnom snimku. */
const testProps: EditProps = {
  video: 'test/test-talk.mp4',
  fps: 30,
  segments: [
    {srcStart: 0.0, srcEnd: 2.2},
    {srcStart: 3.2, srcEnd: 6.0},
  ],
  captions: [
    {text: 'Ovo je test', start: 0.0, end: 1.1},
    {text: 'novog CCC engine-a', start: 1.1, end: 2.2, emphasis: ['CCC']},
    {text: 'rezovi titlovi', start: 2.2, end: 3.5, emphasis: ['titlovi']},
    {text: 'i hook rade', start: 3.5, end: 5.0},
  ],
  hook: {lines: ['Remotion je spreman', 'za montažu 🎬'], y: 700, start: 0, end: 2.2},
  captionY: 1180,
};

export const RemotionRoot: React.FC = () => (
  <>
    <Composition id="CccEdit" component={CccEdit} width={1080} height={1920} fps={30} durationInFrames={1}
      defaultProps={editDefaults} calculateMetadata={metadata} />
    <Composition id="CccTest" component={CccEdit} width={1080} height={1920} fps={30} durationInFrames={1}
      defaultProps={testProps} calculateMetadata={metadata} />
  </>
);
