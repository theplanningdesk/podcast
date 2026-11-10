# Research clips (Wednesdays)

30-second silent motion graphics that explain one open-access paper in the show's field, posted
Wednesdays at 12:00 Stockholm on YouTube Shorts and Instagram Reels (9:16) and the LinkedIn Page
(4:5, posted by hand). The paper link goes in the first comment, and the authors' institutions are
tagged from the Page.

One file per clip: `concepts/<publish date>-<slug>.json`. Pushing it to main runs the "Concept clip"
workflow, which renders both cuts into the release `concept-<stem>`, writes the LinkedIn post and
first-comment text, and schedules the YouTube Short for the publish time. Between 10:00 and 15:00 on
the day, the workflow posts the Reel to Instagram at 12:00 (or as soon after as GitHub runs it). Edit
a file before its day and it re-renders, but the YouTube Short is uploaded only once; take it back
with the workflow's "withdraw" action first if it must change.

## Where papers come from

The "Paper scout" workflow runs on Sunday mornings. It asks OpenAlex for open-access papers from the
last 75 days in trusted journals (by ISSN, list in tools/paper_scout.py) and arXiv preprints from the
last 45 days, keeps those that are about supply chain planning or design, skips vendor and MDPI
papers and anything already used here, ranks them for planners (Nordic and DACH authors, journal,
practice signals, quantified results) and writes `papers/shortlist.md` and `shortlist.json` to the
`sources` branch. Full text is saved as `papers/<openalex id>.txt` only where the licence allows
sharing (Creative Commons or public domain) and the PDF can be downloaded. Publishers often block
downloads; an `OPENALEX_API_KEY` repo secret (free key) lets the scout fetch OpenAlex's own copies.

## Rules for a research clip

- Only papers whose full text is free to read, and only from the full text, never the abstract alone.
- Every number on screen and in the post traces to a page, table or section; list them in
  `source.checked`. Arithmetic of our own (a percentage between two table values) is marked as such.
- Say what the paper shows, not more: "in a new study", "in the base case", never "a plant cut".
- Redraw, don't copy figures. A timeline or schematic that isn't the paper's data says "illustrative".
- No employer, partner or vendor names; skip vendor-authored papers.

## Format

- `date`, `publish_local` ("12:00"), `topic`, `kicker` ("Research"), `series` ("Research").
- `viz`: the visual that carries the story (video/src/concept/viz): `oven`, `gantt`, `network`, `fan`,
  `echelon`. A new kind of story needs a new visual, registered in `viz/index.js`.
- `source`: `cite` (full), `card` (short, for the end card), `title`, `authors`, `institutions`,
  `venue`, `year`, `doi`, `openalex`, `licence`, `checked` (where each number comes from).
- `model`: the data the visual animates.
- `acts`: four beats (problem, why, fix, what-if), each `{start, head, sub}`, starting at frames
  0, 210, 420 and 630 at 30 fps. `endStart` 810 and `total` 900 give a 3-second end card.
- `kpis`: two counters with `steps` `[[frame, value], ...]`; they turn from orange to ink at
  `goodFrom` (set a large `goodFrom` on a KPI that gets worse, like waiting time).
- `endTitle`, `endTag`, `footnote` (names the source table), `cta`.
- `post`: `linkedin` (Page post, ending with the paper-link line and hashtags), `comment_paper`
  (first line of the first comment, with the DOI link), `short_title`, `short_caption`, `hashtags`,
  `tags` (organisations to @-tag on LinkedIn).

Local preview: `cd video && node render-concept.mjs --stem <stem> --stills 3,13,20,27`.
