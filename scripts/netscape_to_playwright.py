#!/usr/bin/env python3
"""Convert Netscape cookie file ke Playwright JSON cookie list.

Skip expired entries. Strip `httpOnly` field (Playwright rejects it).

Usage:
    python netscape_to_playwright.py ~/.config/social-dl/cookies/x.com.txt > cookies.json
"""
import sys
import json
import time


def main(path):
    cookies = []
    now = time.time()
    with open(path) as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue
            parts = line.split("\t")
            if len(parts) < 7:
                continue
            domain, _, path, secure, expires, name, value = parts[:7]
            exp = int(expires) if expires.isdigit() else -1
            if exp > 0 and exp < now:
                continue  # skip expired
            cookies.append({
                "name": name,
                "value": value.strip(),
                "domain": domain if domain.startswith(".") else "." + domain,
                "path": path,
                "secure": secure == "TRUE",
                "expires": exp if exp > 0 else -1,
                # NOTE: `httpOnly` field sengaja di-strip — Playwright nolak
            })
    print(json.dumps(cookies, indent=2))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__, file=sys.stderr)
        sys.exit(1)
    main(sys.argv[1])
