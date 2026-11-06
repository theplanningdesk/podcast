# Planning concept clips

30-second silent motion graphics that explain one planning concept with an illustrative case.
They go out Tuesday and Thursday at 12:00 Stockholm, on YouTube Shorts and Instagram Reels (9:16)
and the LinkedIn Page (4:5, posted by hand).

One file per clip: `concepts/<publish date>-<slug>.json`. Pushing it to main runs the "Concept clip"
workflow, which renders both cuts into the release `concept-<stem>`, writes the LinkedIn post and
first-comment text, and schedules the YouTube Short for the publish time. Just before 12:00 on the
day, the workflow posts the Reel to Instagram. Edit a file before its day and it re-renders, but the
YouTube Short is only uploaded once; delete it in YouTube Studio first if it must change.

## Format

- `date`, `publish_local` ("12:00"), `topic` (also the end-card title's subject).
- `viz`: which visual carries the story: `gantt`, `network`, `fan` or `echelon` (video/src/concept/viz).
  A new kind of story needs a new visual there, registered in `viz/index.js`.
- `model`: the data the visual animates, computed by a small model so every number agrees.
  The models behind the first four are in tools/concept-models.
- `acts`: four beats (problem, why, fix, what-if), each `{start, head, sub}`, starting at frames
  0, 210, 420 and 630 at 30 fps. `endStart` 810 and `total` 900 give a 3-second end card.
- `kpis`: two counters, each with `steps` `[[frame, value], ...]`; they turn from orange to ink at `goodFrom`.
- `endTitle`, `endTag`, `footnote` (always says "Invented numbers"), `cta`.
- `post`: `linkedin` (Page post, ending with "Links in the first comment." and hashtags),
  `short_title`, `short_caption`, `hashtags`.

Rules as for the show: no employer, partner or vendor names; invented companies and numbers are
labelled as such on screen and in the caption.

Local preview: `cd video && node render-concept.mjs --stem <stem> --stills 3,13,20,27`.
