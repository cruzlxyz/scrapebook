#!/usr/bin/env python3
"""Download foto Instagram (yt-dlp gak bisa).

Workflow: Playwright mobile UA + scroll + canvas screenshot extraction.
"""
import argparse
import os
import re
import time

# Placeholder — implementasi penuh menyusul. Lihat:
# https://github.com/cruzlxyz/instagram-photo-download (akan datang)
# Atau skill instagram-photo-download di ~/.hermes/skills/


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("username")
    ap.add_argument("--count", type=int, default=20)
    args = ap.parse_args()

    print(f"[*] TODO: download {args.count} foto dari @{args.username}")
    print("    Lihat skill ~/.hermes/skills/productivity/instagram-photo-download/SKILL.md")


if __name__ == "__main__":
    main()
