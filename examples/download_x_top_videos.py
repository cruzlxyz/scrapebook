#!/usr/bin/env python3
"""Download top-N video dari X account.

Usage:
    python download_x_top_videos.py <screen_name> [--count 10]

Butuh ~/.config/social-dl/cookies/x.com.txt (Netscape format dari browser yang udah login X).
"""
import argparse
import os
import subprocess
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("screen_name")
    ap.add_argument("--count", type=int, default=10)
    ap.add_argument("--output-dir", default=None)
    args = ap.parse_args()

    script = os.path.join(os.path.dirname(__file__), "..", "scripts", "x_user_top_media.py")
    out_dir = args.output_dir or os.path.expanduser(f"~/Downloads/x/{args.screen_name}")

    cmd = [sys.executable, script, args.screen_name, "--count", str(args.count),
           "--type", "video", "--output-dir", out_dir]
    print(f"[*] Running: {' '.join(cmd)}")
    subprocess.run(cmd)


if __name__ == "__main__":
    main()
