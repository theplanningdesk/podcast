// Render a "Planning concept" clip in both cuts, silent, with an empty audio track so
// Instagram and LinkedIn accept it.
//   node render-concept.mjs --stem 2026-11-10-production-scheduling [--stills 3,13,20,27] [--concurrency 4]
// Reads concepts/<stem>.json; writes build/out/planning-desk-concept-<stem>-9x16.mp4 and -4x5.mp4.
import {bundle} from '@remotion/bundler';
import {renderMedia, renderStill, selectComposition} from '@remotion/renderer';
import {execFileSync} from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, '..');
const args = Object.fromEntries(
  process.argv.slice(2).reduce((acc, a, i, arr) => (a.startsWith('--') ? [...acc, [a.slice(2), arr[i + 1] && !arr[i + 1].startsWith('--') ? arr[i + 1] : 'true']] : acc), []),
);
if (!args.stem) throw new Error('Usage: node render-concept.mjs --stem <concept file stem>');
const d = JSON.parse(fs.readFileSync(path.join(root, 'concepts', `${args.stem}.json`), 'utf8'));
const out = path.join(root, 'build', 'out');
fs.mkdirSync(out, {recursive: true});
const browserExecutable = process.env.REMOTION_BROWSER || null;
const concurrency = Number(args.concurrency || 2);
const serveUrl = await bundle({entryPoint: path.join(here, 'src', 'concept-index.jsx')});

for (const [id, fmt, tag] of [['ConceptV', 'v', '9x16'], ['ConceptP', 'p', '4x5']]) {
  const inputProps = {fmt, d};
  const composition = await selectComposition({serveUrl, id, inputProps, browserExecutable});
  const base = path.join(out, `planning-desk-concept-${args.stem}-${tag}`);
  if (args.stills) {
    for (const s of String(args.stills).split(',').map(Number)) {
      const o = `${base}-${String(s).padStart(2, '0')}s.png`;
      await renderStill({composition, serveUrl, output: o, frame: Math.min(composition.durationInFrames - 1, Math.round(s * 30)), inputProps, browserExecutable});
      console.log(o);
    }
    continue;
  }
  const silent = `${base}.silent.mp4`;
  await renderMedia({composition, serveUrl, codec: 'h264', crf: 18, x264Preset: 'veryfast', outputLocation: silent, inputProps, browserExecutable, concurrency, muted: true});
  const tmp = `${base}.part.mp4`;
  // Remotion's bundled ffmpeg, so the workflow needs no apt install.
  execFileSync('npx', ['remotion', 'ffmpeg', '-v', 'error', '-y', '-i', silent, '-f', 'lavfi', '-i', 'anullsrc=r=48000:cl=stereo',
    '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '64k', '-shortest', '-movflags', '+faststart', tmp], {cwd: here, stdio: 'inherit'});
  fs.renameSync(tmp, `${base}.mp4`);
  fs.rmSync(silent);
  console.log(`${base}.mp4`);
}
