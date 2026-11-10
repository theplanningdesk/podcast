#!/usr/bin/env python3
"""Publish a "Planning concept" clip (concepts/<stem>.json, rendered by video/render-concept.mjs).

  python concept_post.py text 2026-11-10-production-scheduling       # LinkedIn post + first comment text files
  python concept_post.py youtube 2026-11-10-production-scheduling    # 9:16 Short, scheduled for the publish time
  python concept_post.py instagram 2026-11-10-production-scheduling  # 9:16 Reel, published at the publish time
  python concept_post.py withdraw 2026-11-12-network-design           # take its scheduled Short back to private (VIDEO_ID env)
  python concept_post.py due [YYYY-MM-DD]                            # print the stems due on that Stockholm date

The publish time is the concept's "date" plus "publish_local" (default 12:00), Stockholm time.
YouTube gets the Short as a scheduled private video that goes public at that time. Instagram has no
scheduling in its API, so the Reel container is created and processed first and published once the
time arrives (the workflow starts this job just before). LinkedIn Page posting stays manual: the text
files are attached to the release and the dispatcher hands them to Jim in the morning.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from podcast_lib import ROOT, load_config

OUT = ROOT / "build" / "out"
TZ = ZoneInfo("Europe/Stockholm")
REPO = os.environ.get("GITHUB_REPOSITORY", "theplanningdesk/podcast")


def concept(stem: str) -> dict:
    return json.loads((ROOT / "concepts" / f"{stem}.json").read_text(encoding="utf-8"))


def publish_at(c: dict) -> datetime:
    hh, mm = (c.get("publish_local") or "12:00").split(":")
    y, mo, d = map(int, c["date"].split("-"))
    return datetime(y, mo, d, int(hh), int(mm), tzinfo=TZ)


def base(stem: str) -> str:
    return f"planning-desk-concept-{stem}"


def tags_line(c: dict) -> str:
    return " ".join(f"#{h.lstrip('#')}" for h in (c.get("post") or {}).get("hashtags", [])[:5])


def cmd_text(stem: str) -> None:
    c, pod = concept(stem), load_config()["podcast"]
    post = (c.get("post") or {}).get("linkedin", "").strip()
    if not post:
        raise SystemExit(f"No post.linkedin in concepts/{stem}.json")
    links = [f"Spotify: {pod['spotify_url']}" if pod.get("spotify_url") else "",
             f"Apple Podcasts: {pod['apple_url']}" if pod.get("apple_url") else "",
             f"YouTube: {pod['youtube_url']}" if pod.get("youtube_url") else ""]
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{base(stem)}-linkedin.txt").write_text(post + "\n", encoding="utf-8")
    (OUT / f"{base(stem)}-linkedin-comment.txt").write_text(
        "\n".join(["The Planning Desk, supply chain planning news every weekday:"] + [l for l in links if l]) + "\n", encoding="utf-8")
    print(f"LinkedIn text written for {stem}.")


def cmd_youtube(stem: str) -> None:
    from youtube_upload import insert, youtube_client
    c, cfg = concept(stem), load_config()
    p, yt = c.get("post") or {}, cfg.get("youtube", {})
    desc = "\n\n".join(x for x in [p.get("short_caption", "").strip(),
                                   f"Supply chain planning news every weekday: {cfg['podcast']['base_url']}",
                                   tags_line(c), "#Shorts"] if x)
    when = publish_at(c)
    status = {"selfDeclaredMadeForKids": False, "containsSyntheticMedia": True}
    if os.environ.get("YOUTUBE_PRIVACY"):
        status["privacyStatus"] = os.environ["YOUTUBE_PRIVACY"]
    elif when > datetime.now(timezone.utc):
        status.update(privacyStatus="private", publishAt=when.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"))
    else:
        status["privacyStatus"] = yt.get("privacy", "public")
    body = {"snippet": {"title": f"{p.get('short_title', c.get('topic', 'Planning concept'))[:90]} #Shorts",
                        "description": desc[:4900], "tags": yt.get("tags", []) + ["planning concept"],
                        "categoryId": "27", "defaultLanguage": "en", "defaultAudioLanguage": "en"},
            "status": status}
    vid = insert(youtube_client(), body, OUT / f"{base(stem)}-9x16.mp4")
    (OUT / f"{base(stem)}.youtube.txt").write_text(f"https://youtube.com/shorts/{vid}\n", encoding="utf-8")
    print(f"YouTube Short {vid}: {status.get('publishAt') or status['privacyStatus']}")


def cmd_instagram(stem: str) -> None:
    from instagram_upload import API, call, refresh
    c = concept(stem)
    user, token = os.environ["INSTAGRAM_USER_ID"], refresh(os.environ["INSTAGRAM_TOKEN"])
    url = f"https://github.com/{REPO}/releases/download/concept-{stem}/{base(stem)}-9x16.mp4"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=30) as resp:
            url = resp.geturl()
    except Exception as err:
        print(f"Couldn't resolve the release redirect ({err}); using the release link.")
    p = c.get("post") or {}
    caption = "\n\n".join(x for x in [p.get("short_caption", "").strip(), tags_line(c)] if x)[:2100]
    container = call("POST", f"{API}/{user}/media",
                     {"media_type": "REELS", "video_url": url, "caption": caption, "share_to_feed": True}, token)["id"]
    status = ""
    for _ in range(20):
        time.sleep(30)
        status = call("GET", f"{API}/{container}?fields=status_code", token=token).get("status_code", "")
        print(f"  status {status}")
        if status in ("FINISHED", "ERROR", "EXPIRED"):
            break
    if status != "FINISHED":
        raise SystemExit(f"Instagram didn't finish processing the Reel (status {status or 'unknown'}).")
    wait = (publish_at(c) - datetime.now(timezone.utc)).total_seconds()
    if wait > 0:
        print(f"Processed; publishing in {int(wait // 60)} min at {publish_at(c):%H:%M} Stockholm.")
        time.sleep(min(wait, 3 * 3600))
    media = call("POST", f"{API}/{user}/media_publish", {"creation_id": container}, token)["id"]
    link = call("GET", f"{API}/{media}?fields=permalink", token=token).get("permalink", "")
    (OUT / f"{base(stem)}.instagram.txt").write_text(f"{link or media}\n", encoding="utf-8")
    print(f"Published Reel {link or media}")


def cmd_withdraw(stem: str) -> None:
    """Take a scheduled or public Short back to private (kept in YouTube Studio, not deleted)."""
    from youtube_upload import youtube_client
    vid = os.environ.get("VIDEO_ID", "").strip().rstrip("/").split("/")[-1]
    if not vid:
        raise SystemExit(f"No VIDEO_ID given for {stem}")
    yt = youtube_client()
    items = yt.videos().list(part="status", id=vid).execute().get("items", [])
    if not items:
        print(f"{stem}: video {vid} not found; nothing to withdraw.")
        return
    status = items[0]["status"]
    status.pop("publishAt", None)
    status["privacyStatus"] = "private"
    yt.videos().update(part="status", body={"id": vid, "status": status}).execute()
    print(f"{stem}: YouTube {vid} set to private, schedule removed.")


def cmd_due(day: str | None) -> None:
    day = day or datetime.now(TZ).strftime("%Y-%m-%d")
    for f in sorted((ROOT / "concepts").glob(f"{day}-*.json")):
        print(f.stem)


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] not in ("text", "youtube", "instagram", "withdraw", "due"):
        raise SystemExit(__doc__)
    cmd, arg = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else None)
    if cmd == "due":
        cmd_due(arg)
        return 0
    if not arg:
        raise SystemExit(__doc__)
    {"text": cmd_text, "youtube": cmd_youtube, "instagram": cmd_instagram, "withdraw": cmd_withdraw}[cmd](arg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
