// Render the Instagram cover (a 1080x1920 JPEG still) for a Short or a research clip.
// The Reel uploaders pass it to Instagram as cover_url, so the profile grid shows the headline
// instead of the video's first frame, which is empty paper before the graphics come in.
//
//   node render-cover.mjs --stem 2026-11-16                       (episode Short, from the script)
//   node render-cover.mjs --stem "2026-11-13 2026-11-14"          (several at once)
//   node render-cover.mjs --concept 2026-11-18-forecast-revision-ordering
//
// Reads episodes/scripts/script-<stem>.json or concepts/<stem>.json; needs no audio.
// Writes build/out/planning-desk-<stem>-short-cover.jpg or planning-desk-concept-<stem>-cover.jpg.
import {bundle} from '@remotion/bundler';
import {renderStill, selectComposition} from '@remotion/renderer';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, '..');
const args = Object.fromEntries(
  process.argv.slice(2).reduce((acc, a, i, arr) => (a.startsWith('--') ? [...acc, [a.slice(2), arr[i + 1] && !arr[i + 1].startsWith('--') ? arr[i + 1] : 'true']] : acc), []),
);
const list = (v) => (v && v !== 'true' ? String(v).split(/[\s,]+/).filter(Boolean) : []);
const stems = list(args.stem), concepts = list(args.concept);
if (!stems.length && !concepts.length) throw new Error('Usage: node render-cover.mjs --stem <episode stem> | --concept <concept stem>');

const config = JSON.parse(fs.readFileSync(path.join(root, 'config.json'), 'utf8'));
const read = (...p) => JSON.parse(fs.readFileSync(path.join(root, ...p), 'utf8'));
const day = (iso) => new Date(`${iso}T12:00:00Z`).toLocaleDateString('en-GB', {weekday: 'short', day: 'numeric', month: 'short', timeZone: 'UTC'});
// "Topic: hook" titles put the topic on its own line, so the hook can be set larger.
const split = (title) => {
  const i = title.indexOf(': ');
  if (i <= 0 || i > 34 || title.length - i <= 12) return {topic: '', title};
  const hook = title.slice(i + 2);
  return {topic: title.slice(0, i), title: hook[0].toUpperCase() + hook.slice(1)};
};

const jobs = [];
for (const stem of stems) {
  const s = read('episodes', 'scripts', `script-${stem}.json`);
  const book = s.format === 'saturday';
  const full = (s.short?.title || s.episode_title || s.title || '').trim();
  if (!full) { console.warn(`No title in script-${stem}.json; no cover made.`); continue; }
  const date = s.run_date || stem.slice(0, 10);
  jobs.push({
    file: `planning-desk-${stem}-short-cover.jpg`,
    props: {
      variant: book ? 'book' : 'daily',
      kicker: `${book ? config.formats?.saturday?.title_prefix || 'Book of the week' : 'Daily'} · ${day(date)}`,
      ...split(full), show: config.show,
    },
  });
}
for (const stem of concepts) {
  const c = read('concepts', `${stem}.json`);
  const full = (c.post?.short_title || c.endTitle || c.topic || '').replace(/\s*\|\s*Research\s*$/i, '').trim();
  if (!full) { console.warn(`No title in concepts/${stem}.json; no cover made.`); continue; }
  jobs.push({
    file: `planning-desk-concept-${stem}-cover.jpg`,
    props: {variant: 'research', kicker: `${c.series || 'Research'} · ${day(c.date || stem.slice(0, 10))}`, topic: c.topic || '', title: full, show: config.show},
  });
}

const out = path.join(root, 'build', 'out');
fs.mkdirSync(out, {recursive: true});
const browserExecutable = process.env.REMOTION_BROWSER || null;
const serveUrl = await bundle({entryPoint: path.join(here, 'src', 'cover-index.jsx')});
for (const job of jobs) {
  const composition = await selectComposition({serveUrl, id: 'Cover', inputProps: job.props, browserExecutable});
  const output = path.join(out, job.file);
  await renderStill({composition, serveUrl, output, inputProps: job.props, imageFormat: 'jpeg', jpegQuality: 92, browserExecutable});
  console.log(`Cover ${output}`);
}
