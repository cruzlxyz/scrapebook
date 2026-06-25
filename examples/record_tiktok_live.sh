#!/usr/bin/env bash
# Rekam TikTok LIVE stream.
#
# Usage:
#     ./record_tiktok_live.sh <username> [--mode manual|automatic] [--output DIR]
#
# Butuh ~/tiktok-live-recorder/src/cookies.json dengan sessionid_ss.

set -euo pipefail

USER="${1:?username required}"
shift
# strip leading `--` if present
[[ "${1:-}" == "--" ]] && shift

OUTPUT="$HOME/Downloads/tiktok/$USER"
MODE="manual"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --mode) MODE="$2"; shift 2 ;;
        --output) OUTPUT="$2"; shift 2 ;;
        *) echo "Unknown flag: $1"; exit 1 ;;
    esac
done

mkdir -p "$OUTPUT"

echo "[*] Recording @$USER live → $OUTPUT (mode=$MODE)"

~/.local/bin/tiktok-live-recorder \
    -user "$USER" \
    -mode "$MODE" \
    -output "$OUTPUT" \
    -no-update-check
