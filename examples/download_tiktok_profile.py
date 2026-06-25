#!/usr/bin/env python3
"""Download video dari TikTok profile, ranked by views.

Usage:
    python download_tiktok_profile.py <handle> [--count 15]
"""
import argparse
import os
import subprocess
import sys
import time

import requests


def get_view_ranked_videos(handle, count):
    """Buka profile page di Playwright, extract view-ranked list."""
    from playwright.sync_api import sync_playwright
    short_url = f"https://www.tiktok.com/@{handle}"
    captured = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            viewport={"width": 390, "height": 844},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
        )
        page = ctx.new_page()
        page.goto(short_url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(5000)
        for _ in range(8):
            page.evaluate("window.scrollBy(0, 2000)")
            page.wait_for_timeout(800)
        html = page.content()
        browser.close()

    import re
    matches = re.findall(r'href="(https://www\.tiktok\.com/@[\w.]+/video/(\d+))"[^>]*>([^<]*)', html)
    seen = set()
    out = []
    for url, vid, text in matches:
        if vid in seen:
            continue
        seen.add(vid)
        out.append({"url": url, "id": vid, "text": text.strip()})
    return out[:count]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("handle")
    ap.add_argument("--count", type=int, default=15)
    ap.add_argument("--output-dir", default=None)
    args = ap.parse_args()

    out_dir = args.output_dir or os.path.expanduser(f"~/Downloads/tiktok/{args.handle}")
    os.makedirs(out_dir, exist_ok=True)

    print(f"[*] Scraping @{args.handle}...")
    items = get_view_ranked_videos(args.handle, args.count)

    def parse_views(s):
        s = s.strip().split()[0].replace(",", "")
        if s.endswith("K"): return float(s[:-1]) * 1_000
        if s.endswith("M"): return float(s[:-1]) * 1_000_000
        try: return float(s)
        except: return 0

    items.sort(key=lambda x: -parse_views(x["text"]))
    items = items[:args.count]

    print(f"[+] Top {len(items)} by views:")
    for i, item in enumerate(items, 1):
        print(f"  {i}. {item['text']:>8} | {item['id']}")

    print(f"\n[*] Downloading ke {out_dir}/...")
    yt = "/home/ubuntu/.hermes/hermes-agent/venv/bin/yt-dlp"
    for item in items:
        out_path = f"{out_dir}/{item['id']}.mp4"
        if os.path.exists(out_path) and os.path.getsize(out_path) > 100_000:
            print(f"  SKIP {item['id']}")
            continue
        try:
            subprocess.run([
                yt, "-q", "--no-warnings",
                "-f", "best[ext=mp4]/best",
                "-o", out_path,
                item["url"],
                "--extractor-args", f"tiktok:webpage_url=https://m.tiktok.com/v/{item['id']}",
            ], check=True, timeout=120)
            print(f"  OK {item['id']} ({os.path.getsize(out_path)//1024} KB)")
        except subprocess.CalledProcessError as e:
            print(f"  ERR {item['id']}: {e}")


if __name__ == "__main__":
    main()
