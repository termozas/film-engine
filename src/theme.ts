/* Look of the film: one place for colours and type. The defaults are a calm product look
   (Source Sans 3, ink and navy). Change these to match the product being filmed. */
import { loadFont } from '@remotion/google-fonts/SourceSans3';

export const { fontFamily } = loadFont('normal', { weights: ['400', '500', '600', '700'], subsets: ['latin'] });

export const INK = '#172033';      // text
export const BRAND = '#165CA8';    // accent: labels, bars, highlights
export const SLATE = '#64748B';    // secondary text
export const SOFT = '#8B97A8';     // footnotes and source lines
export const LINE = 'rgba(23,32,51,0.12)';
export const WASH = '#EEF3FA';
export const AMBER = '#C67A11';    // second series, "removed" marks
export const RED = '#B42318';
export const PAPER = '#F3F6FA';    // backdrop
export const BACKDROP = `radial-gradient(120% 90% at 50% 0%, #FCFDFE 0%, ${PAPER} 55%, #E4EAF2 100%)`;
