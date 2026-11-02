#!/usr/bin/env python3
"""Turn LinkedIn Page "content" exports into per-episode CSVs for the stats readout.

LinkedIn has no API open to this Page, so the producer downloads the export by hand
(Page admin view > Analytics > Content > Export) and drops it in the claude.ai Project.
The Monday readout runs this script on it. Only numbers, dates, post links and the first
words of each post are kept: the export's "Posted by" column (an admin's name) is dropped.

Usage:
  python linkedin_import.py --episodes episodes.json --posts linkedin-posts.csv \\
      --daily linkedin-daily.csv EXPORT.xls [EXPORT2.xlsx ...]

--posts and --daily are read first if they exist, then updated in place: each post keeps
the numbers from the newest export that contains it, and each day the newest value.
Needs pandas plus xlrd (.xls) or openpyxl (.xlsx).
"""
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path

import pandas as pd

POST_FIELDS = ["stem", "format", "posted", "impressions", "clicks", "ctr", "reactions", "comments",
               "reposts", "engagement_rate", "as_of", "post_link", "opening"]
DAILY_FIELDS = ["date", "impressions", "unique_impressions", "clicks", "reactions", "comments",
                "reposts", "engagement_rate", "as_of"]


def us_date(v) -> str:
    """LinkedIn writes MM/DD/YYYY (UTC); return YYYY-MM-DD."""
    if isinstance(v, datetime):
        return v.date().isoformat()
    return datetime.strptime(str(v).strip(), "%m/%d/%Y").date().isoformat()


def sheet(path: Path, name: str) -> pd.DataFrame:
    df = pd.read_excel(path, sheet_name=name, header=1)
    return df.dropna(axis=1, how="all").dropna(axis=0, how="all")


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def num(v) -> str:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return ""
    return str(int(f)) if f == int(f) else f"{f:.4f}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("exports", nargs="+", type=Path)
    ap.add_argument("--episodes", type=Path, required=True, help="docs/episodes.json from the podcast repo")
    ap.add_argument("--posts", type=Path, required=True)
    ap.add_argument("--daily", type=Path, required=True)
    a = ap.parse_args()

    formats = {}
    for e in json.loads(a.episodes.read_text(encoding="utf-8")):
        stem = e.get("stem") or e["guid"].replace("planning-desk-", "")
        formats[stem[:10]] = (stem, e.get("format", "weekly"))

    posts = {r["post_link"]: r for r in read_csv(a.posts)}
    daily = {r["date"]: r for r in read_csv(a.daily)}

    for path in a.exports:
        metrics = sheet(path, "Metrics")
        as_of = max(us_date(d) for d in metrics["Date"])
        for _, m in metrics.iterrows():
            d = us_date(m["Date"])
            if d in daily and daily[d].get("as_of", "") > as_of:
                continue
            daily[d] = {"date": d, "impressions": num(m.get("Impressions (total)")),
                        "unique_impressions": num(m.get("Unique impressions (organic)")),
                        "clicks": num(m.get("Clicks (total)")), "reactions": num(m.get("Reactions (total)")),
                        "comments": num(m.get("Comments (total)")), "reposts": num(m.get("Reposts (total)")),
                        "engagement_rate": num(m.get("Engagement rate (total)")), "as_of": as_of}

        for _, p in sheet(path, "All posts").iterrows():
            link = str(p.get("Post link", "")).strip()
            if not link or link == "nan":
                continue
            if link in posts and posts[link].get("as_of", "") > as_of:
                continue
            posted = us_date(p["Created date"])
            stem, fmt = formats.get(posted, ("", ""))
            opening = " ".join(str(p.get("Post title", "")).split())[:90]
            posts[link] = {"stem": stem, "format": fmt, "posted": posted,
                           "impressions": num(p.get("Impressions")), "clicks": num(p.get("Clicks")),
                           "ctr": num(p.get("Click through rate (CTR)")), "reactions": num(p.get("Likes")),
                           "comments": num(p.get("Comments")), "reposts": num(p.get("Reposts")),
                           "engagement_rate": num(p.get("Engagement rate")), "as_of": as_of,
                           "post_link": link, "opening": opening}
        print(f"{path.name}: data up to {as_of}")

    write_csv(a.posts, sorted(posts.values(), key=lambda r: r["posted"]), POST_FIELDS)
    write_csv(a.daily, sorted(daily.values(), key=lambda r: r["date"]), DAILY_FIELDS)
    print(f"{len(posts)} posts in {a.posts.name}, {len(daily)} days in {a.daily.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
