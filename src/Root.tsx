import React from 'react';
import { Composition } from 'remotion';
import { Film, FPS, W, H, timeline } from './Film';

export const Root: React.FC = () => (
  <Composition id="Film" component={Film} durationInFrames={Math.max(1, Math.round(timeline().total * FPS))} fps={FPS} width={W} height={H} />
);
