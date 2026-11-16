#!/usr/bin/env python3
"""Post a weekday Short to Instagram as a Reel (Instagram API with Instagram Login).

Needs repository secrets INSTAGRAM_USER_ID and INSTAGRAM_TOKEN (a long-lived token).
Meta fetches the video from a public URL, so the Short must already be attached to the
episode's GitHub release. The token is refreshed on every run; if the refresh returns a
new token and GH_ADMIN_TOKEN is set, the INSTAGRAM_TOKEN secret is updated too.

Usage: python instagram_upload.py 2026-11-02
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

from podcast_lib import ROOT, load_config

API = "https://graph.instagram.com/v26.0"
REPO = os.environ.get("GITHUB_REPOSITORY", "theplanningdesk/podcast")


def call(method: str, url: str, data: dict | None = None, token: str | None = None) -> dict:
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, method=method)
    if body is not None:
        req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as err:
        raise SystemExit(f"Instagram API {err.code}: {err.read().decode(errors='replace')[:800]}") from err


def refresh(token: str) -> str:
    """Long-lived tokens last 60 days; refreshing resets the clock."""
    try:
        res = call("GET", f"https://graph.instagram.com/refresh_access_token?grant_type=ig_refresh_token&access_token={urllib.parse.quote(token)}")
    except SystemExit as err:
        print(f"Token refresh skipped: {err}")
        return token
    new = res.get("access_token") or token
    days = int(res.get("expires_in", 0)) // 86400
    print(f"Instagram token refreshed, valid for {days} more days.")
    if new != token:
        admin = os.environ.get("GH_ADMIN_TOKEN")
        if admin:
            subprocess.run(["gh", "secret", "set", "INSTAGRAM_TOKEN", "-R", REPO, "--body", new],
                           env={**os.environ, "GH_TOKEN": admin}, check=True, capture_output=True)
            print("Stored the refreshed token in the INSTAGRAM_TOKEN secret.")
        else:
            print("::warning::Instagram returned a new token but GH_ADMIN_TOKEN isn't set, so it wasn't saved.")
    return new


def release_url(tag: str, name: str) -> str | None:
    """Release download links redirect to a signed file URL; hand Meta the final URL.

    Returns None when the release has no such file.
    """
    url = f"https://github.com/{REPO}/releases/download/{tag}/{name}"
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.geturl()
    except urllib.error.HTTPError as err:
        if err.code == 404:
            return None
        print(f"Couldn't resolve the release redirect ({err}); using the release link.")
        return url
    except Exception as err:  # fall back to the redirecting link
        print(f"Couldn't resolve the release redirect ({err}); using the release link.")
        return url


def create_reel(user: str, token: str, video_url: str, caption: str,
                cover_url: str | None = None, thumb_offset_ms: int = 2000) -> str:
    """Create a Reel container, wait until Instagram has processed it and return its id.

    The profile grid shows the Reel's cover. Without one Instagram takes the video's first frame,
    which is empty paper before the graphics come in. So: use the rendered cover image when there
    is one, and if Instagram turns that down (or there's none) fall back to a frame a little way
    into the video. A cover problem never stops the Reel from going out.
    """
    base = {"media_type": "REELS", "video_url": video_url, "caption": caption, "share_to_feed": True}
    attempts = ([("the cover image", {**base, "cover_url": cover_url})] if cover_url else []) \
        + [(f"the frame at {thumb_offset_ms / 1000:g} s as cover", {**base, "thumb_offset": thumb_offset_ms})]
    problem = "no attempt made"
    for i, (label, payload) in enumerate(attempts):
        last = i == len(attempts) - 1
        try:
            container = call("POST", f"{API}/{user}/media", payload, token)["id"]
        except SystemExit as err:
            if last:
                raise
            print(f"::warning::Instagram refused the Reel with {label} ({err}); trying without it.")
            continue
        print(f"Container {container} created with {label}; waiting for Instagram to process the video.")
        status = ""
        for _ in range(20):  # up to 10 minutes
            time.sleep(30)
            status = call("GET", f"{API}/{container}?fields=status_code", token=token).get("status_code", "")
            print(f"  status {status}")
            if status in ("FINISHED", "ERROR", "EXPIRED"):
                break
        if status == "FINISHED":
            return container
        problem = f"status {status or 'unknown'}"
        if not last and status == "ERROR":
            print(f"::warning::Instagram couldn't process the Reel with {label}; trying without it.")
            continue
        break
    raise SystemExit(f"Instagram didn't finish processing the Reel ({problem}).")


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    stem = sys.argv[1]
    cfg = load_config()
    user, token = os.environ["INSTAGRAM_USER_ID"], os.environ["INSTAGRAM_TOKEN"]
    token = refresh(token)

    script = json.loads((ROOT / "episodes" / "scripts" / f"script-{stem}.json").read_text(encoding="utf-8"))
    short = script.get("short") or {}
    tags = " ".join(f"#{h.lstrip('#')}" for h in short.get("hashtags", [])[:5])
    caption = "\n\n".join(x for x in [(short.get("caption") or "").strip(), tags] if x)[:2100]

    tag = f"episode-{stem}"
    video = release_url(tag, f"planning-desk-{stem}-short.mp4")
    if not video:
        raise SystemExit(f"The release {tag} has no planning-desk-{stem}-short.mp4.")
    cover = release_url(tag, f"planning-desk-{stem}-short-cover.jpg")
    if not cover:
        print("::warning::No cover image in the release; using a frame from the video.")
    container = create_reel(user, token, video, caption, cover)
    media = call("POST", f"{API}/{user}/media_publish", {"creation_id": container}, token)["id"]
    link = call("GET", f"{API}/{media}?fields=permalink", token=token).get("permalink", "")
    print(f"Published Reel {link or media}")
    (ROOT / "build" / "out" / f"planning-desk-{stem}-short.instagram.txt").write_text(f"{link or media}\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
