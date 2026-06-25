#!/usr/bin/env python3
"""Bulk scrape top-N video (atau foto) dari akun X via GraphQL UserMedia hijack.

Usage:
    python x_user_top_media.py <screen_name> --count 10 --type video
    python x_user_top_media.py <screen_name> --count 20 --type photo --output-dir ~/Downloads/x/<user>/photos
"""
import argparse
import json
import os
import sys
import time

from playwright.sync_api import sync_playwright


def load_netscape_cookies(path):
    cookies = []
    now = time.time()
    with open(path) as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue
            parts = line.split("\t")
            if len(parts) < 7:
                continue
            domain, _, path_, secure, expires, name, value = parts[:7]
            exp = int(expires) if expires.isdigit() else -1
            if exp > 0 and exp < now:
                continue
            cookies.append({
                "name": name, "value": value.strip(),
                "domain": domain if domain.startswith(".") else "." + domain,
                "path": path_, "secure": secure == "TRUE",
                "expires": exp if exp > 0 else -1,
            })
    return cookies


def scrape(screen_name, cookie_path, media_type="video", scroll_rounds=40):
    cookies = load_netscape_cookies(cookie_path)
    captured = []
    media = []
    seen = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            viewport={"width": 390, "height": 844},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
        )
        ctx.add_cookies(cookies)
        page = ctx.new_page()

        def on_resp(r):
            if "UserMedia" in r.url and r.status == 200:
                try:
                    captured.append(r.json())
                except Exception:
                    pass

        page.on("response", on_resp)
        page.goto(f"https://x.com/{screen_name}/media",
                  wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(5000)
        for _ in range(scroll_rounds):
            page.evaluate("window.scrollBy(0, 2500)")
            page.wait_for_timeout(800)
        browser.close()

    def walk(obj):
        if isinstance(obj, dict):
            if "rest_id" in obj and "legacy" in obj:
                tr = obj
                if tr.get("__typename") == "TweetWithVisibilityResults":
                    tr = tr.get("tweet", tr)
                tid = tr.get("rest_id")
                if tid and tid not in seen:
                    legacy = tr.get("legacy", {})
                    media_list = (legacy.get("extended_entities", {}).get("media")
                                  or legacy.get("entities", {}).get("media") or [])
                    for m in media_list:
                        if media_type == "video" and m.get("type") == "video":
                            mp4s = [v for v in m["video_info"]["variants"]
                                    if v.get("content_type") == "video/mp4"]
                            if mp4s:
                                best = max(mp4s, key=lambda x: x.get("bitrate", 0))
                                media.append({
                                    "id": tid,
                                    "url": best["url"],
                                    "likes": legacy.get("favorite_count", 0),
                                    "rt": legacy.get("retweet_count", 0),
                                    "dur_ms": m["video_info"].get("duration_millis", 0),
                                    "created_at": legacy.get("created_at"),
                                })
                                seen.add(tid)
                                break
                        elif media_type == "photo" and m.get("type") == "photo":
                            base = m.get("media_url_https", "")
                            media.append({
                                "id": tid,
                                "url": base + "?format=jpg&name=orig" if base else "",
                                "likes": legacy.get("favorite_count", 0),
                                "rt": legacy.get("retweet_count", 0),
                                "created_at": legacy.get("created_at"),
                            })
                            seen.add(tid)
                            break
            for v in obj.values():
                walk(v)
        elif isinstance(obj, list):
            for v in obj:
                walk(v)

    for body in captured:
        walk(body)

    media.sort(key=lambda x: -x["likes"])
    return media


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("screen_name")
    ap.add_argument("--cookies", default=os.path.expanduser("~/.config/social-dl/cookies/x.com.txt"))
    ap.add_argument("--count", type=int, default=10)
    ap.add_argument("--type", choices=["video", "photo"], default="video")
    ap.add_argument("--output-dir", help="Download ke direktori ini")
    args = ap.parse_args()

    print(f"[*] Scraping top {args.count} {args.type} dari @{args.screen_name}...")
    items = scrape(args.screen_name, args.cookies, args.type)
    top = items[:args.count]

    print(f"[+] Found {len(items)} total, returning top {len(top)}:")
    for i, item in enumerate(top, 1):
        size = ""
        if "dur_ms" in item:
            size = f" | {item['dur_ms']/1000:.1f}s"
        print(f"  {i}. {item['likes']:>6} likes{size} | {item['id']}")

    if args.output_dir:
        import requests
        os.makedirs(args.output_dir, exist_ok=True)
        for item in top:
            ext = "mp4" if args.type == "video" else "jpg"
            out = f"{args.output_dir}/{item['id']}.{ext}"
            if os.path.exists(out) and os.path.getsize(out) > 100_000:
                print(f"  SKIP {item['id']}")
                continue
            try:
                r = requests.get(item["url"], headers={"User-Agent": "Mozilla/5.0"}, timeout=180, stream=True)
                with open(out, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1024 * 256):
                        if chunk:
                            f.write(chunk)
                print(f"  OK {item['id']} ({os.path.getsize(out)//1024} KB)")
            except Exception as e:
                print(f"  ERR {item['id']}: {e}")


if __name__ == "__main__":
    main()
