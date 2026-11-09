#!/usr/bin/env python3
"""Shape the stats into the three JSON files the engagement dashboard reads.

Usage:
  python dashboard_data.py --stats STATS_DIR --linkedin linkedin-posts.csv --out OUT_DIR [--today YYYY-MM-DD]

STATS_DIR holds episodes.csv, channels.csv and manual.csv from the repo's stats branch.
linkedin-posts.csv is the private per-post LinkedIn file kept in the claude.ai Project.
Writes OUT_DIR/episodes.json, weeks.json and followers.json (row objects, null where unknown).

Week rule: every number is credited to the week (Monday to Sunday) the episode went out, so a
recent week keeps growing as its episodes collect plays. A week is "complete" once its Sunday
is before --today.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path


def rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def num(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return int(f) if f == int(f) else round(f, 4)


def add(a, b):
    if a is None and b is None:
        return None
    return (a or 0) + (b or 0)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stats", type=Path, required=True)
    ap.add_argument("--linkedin", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--today", default=date.today().isoformat())
    a = ap.parse_args()
    today = date.fromisoformat(a.today)
    a.out.mkdir(parents=True, exist_ok=True)

    li: dict[str, dict] = defaultdict(lambda: {"imp": None, "clicks": None, "reactions": None,
                                               "comments": None, "talk": None, "opening": ""})
    for p in rows(a.linkedin):
        if not p.get("stem"):
            continue
        d = li[p["stem"]]
        c = num(p.get("comments"))
        d["imp"] = add(d["imp"], num(p.get("impressions")))
        d["clicks"] = add(d["clicks"], num(p.get("clicks")))
        d["reactions"] = add(d["reactions"], num(p.get("reactions")))
        d["comments"] = add(d["comments"], c)
        # Each post's first comment is the Page's own, with the episode links.
        d["talk"] = add(d["talk"], max((c or 0) - 1, 0) if c is not None else None)
        imp = num(p.get("impressions")) or 0
        if not d["opening"] or imp > (d.get("_best") or 0):
            d["opening"], d["_best"] = p.get("opening", ""), imp

    episodes = []
    for e in rows(a.stats / "episodes.csv"):
        stem = e["stem"]
        if len(stem) != 10:
            continue
        l = li.get(stem, {})
        episodes.append({
            "date": stem, "day": date.fromisoformat(stem).strftime("%a %-d %b"),
            "format": e.get("format", ""), "weekday": e.get("weekday", ""),
            "title": e.get("title", ""), "hook": e.get("short_title", ""),
            "minutes": num(e.get("minutes")),
            "podcast": num(e.get("op3_all")), "podcast_raw": num(e.get("github_mp3_fetches")),
            "short_views": num(e.get("short_views")), "reel_views": num(e.get("ig_views")),
            "youtube_views": num(e.get("yt_views")),
            "li_impressions": l.get("imp"), "li_clicks": l.get("clicks"),
            "li_reactions": l.get("reactions"), "li_comments": l.get("talk"),
            "li_opening": l.get("opening", ""),
        })
    episodes.sort(key=lambda r: r["date"])

    weeks: dict[str, dict] = {}
    for r in episodes:
        d = date.fromisoformat(r["date"])
        monday = (d - timedelta(days=d.weekday())).isoformat()
        w = weeks.setdefault(monday, {"week": monday, "episodes": 0, "podcast": None, "podcast_raw": None,
                                      "shorts": None, "reels": None, "youtube": None,
                                      "li_impressions": None, "li_reactions": None, "li_comments": None,
                                      "li_clicks": None,
                                      "complete": date.fromisoformat(monday) + timedelta(days=6) < today})
        w["episodes"] += 1
        for k, src in (("podcast", "podcast"), ("podcast_raw", "podcast_raw"), ("shorts", "short_views"),
                       ("reels", "reel_views"), ("youtube", "youtube_views"), ("li_impressions", "li_impressions"),
                       ("li_reactions", "li_reactions"), ("li_comments", "li_comments"), ("li_clicks", "li_clicks")):
            w[k] = add(w[k], r[src])
    week_rows = [weeks[k] for k in sorted(weeks)]

    snap: dict[str, dict] = defaultdict(dict)
    names = {("youtube", "subscribers"): "youtube", ("instagram", "followers"): "instagram",
             ("newsletter", "subscribers"): "newsletter"}
    for c in rows(a.stats / "channels.csv"):
        key = names.get((c.get("channel"), c.get("metric")))
        if key and num(c.get("value")) is not None:
            snap[c["date"]][key] = num(c["value"])
    for m in rows(a.stats / "manual.csv"):
        for col, key in (("spotify_followers", "spotify"), ("apple_followers", "apple"),
                         ("linkedin_followers", "linkedin")):
            if num(m.get(col)) is not None:
                snap[m["date"]][key] = num(m[col])
    followers = [{"date": d, **{k: snap[d].get(k) for k in
                                ("linkedin", "youtube", "instagram", "spotify", "apple", "newsletter")}}
                 for d in sorted(snap)]

    for name, data in (("episodes", episodes), ("weeks", week_rows), ("followers", followers)):
        (a.out / f"{name}.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"{name}.json: {len(data)} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
