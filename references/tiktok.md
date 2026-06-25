# TikTok — Deep Dive

## shortlink-redirect

`vt.tiktok.com/<CODE>` adalah interstitial redirect — `requests` follow chain tapi mendarat di login wall. Solusi: buka via browser dulu.

```bash
~/.local/bin/camofox open "https://vt.tiktok.com/<CODE>/"
sleep 5
# Document.title sekarang nunjukin username asli, body nunjukin "X foto & video"
```

Atau via Playwright:
```python
page.goto(short_url, wait_until="domcontentloaded", timeout=30000)
page.wait_for_timeout(5000)
# page.url sekarang long URL dengan username
```

Setelah resolve, download via URL panjang `https://www.tiktok.com/@<handle>/video/<ID>` dengan yt-dlp langsung (gak butuh impersonate).

## long-url-download

```bash
yt-dlp -f "best[ext=mp4]/best" \
  "https://www.tiktok.com/@user/video/<ID>" \
  --extractor-args "tiktok:webpage_url=https://m.tiktok.com/v/<ID>"
```

`webpage_url` extractor arg paksa yt-dlp pake mobile API yang lebih permisif — desktop URL sering return 403.

## view-count-parsing

Card video di profile page punya view count sebagai text di anchor `a[href*="/video/"]`. Format gak konsisten:

| Tipe | Contoh |
|---|---|
| Ratusan | `"9558"`, `"906"` |
| Ribuan | `"13.1K"`, `"636.5K"` |
| Jutaan | `"1.2M"`, `"622K"` (kadang K buat juta) |
| Pinned indicator | `"1509\nPinned"` |

Parse function:
```python
def parse_views(s):
    s = s.strip().split()[0].replace(",", "")
    if s.endswith("K"): return float(s[:-1]) * 1_000
    if s.endswith("M"): return float(s[:-1]) * 1_000_000
    if s.endswith("B"): return float(s[:-1]) * 1_000_000_000
    try: return float(s)
    except: return 0
```

Sort descending → top-N by views.

## region-locked-audio-only

**Symptom:** yt-dlp selesai tanpa error, file `.mp4` tersimpan, tapi pas dibuka cuma audio doang.

**Diagnostik:**
```bash
ffprobe -v error -show_streams video.mp4 2>&1 | grep codec_type
# Output: audio (no video line) → region-locked junk
```

**Root cause:** TikTok CDN route request ke IDC regional terdekat (`alisg`, `useast2a`, dll). Beberapa creator (terverifikasi: Singapore creator `@chintya.ay`, video `7648584635051527431`) hanya serve audio track ke IDC tertentu — video master di-block di layer CDN.

URL yang ke-capture di debug log:
```
mime_type=audio_mpeg
```
Itu konfirmasi audio-only stream.

**Fix:** Gak ada. Tested:
- `--cookies ~/.config/social-dl/cookies/tiktok.com.txt` → tetep audio-only
- `--impersonate chrome` → `Unable to extract universal data for rehydration`
- `/embed/v2/<id>` → unsupported
- Ganti `tt-target-idc` di cookies.json → tetep audio-only

**Action:** Hapus file, kasih tau user video ID spesifik itu region-locked, skip.

## live-recorder-cookies

Tool `tiktok-live-recorder` perlu session cookies TikTok. Extract via Playwright `ctx.cookies()` setelah navigate ke TikTok logged-in page, simpan ke `~/tiktok-live-recorder/src/cookies.json`:

```json
{
  "sessionid_ss": "<required>",
  "tt-target-idc": "useast2a",
  "msToken": "<optional>",
  "odin_tt": "<optional>"
}
```

Tanpa `sessionid_ss` → HTTP 403 di `webcast/room/enter/` → error `LiveNotFound: Unable to retrieve live streaming url`.

`sessionid_ss` itu HttpOnly — gak bisa di-read via `document.cookie`. Harus via Playwright `ctx.cookies()` atau DevTools Application tab.

## stale-live-detection

Antara user bilang "live" dan recorder beneran jalan, beberapa menit bisa lewat (terverifikasi: 2 jam delay di kasus `@cumanbahangabutorang`). Selalu re-check live status via Camofox segera sebelum launch recorder:

```python
page.goto(f"https://www.tiktok.com/@{user}/live")
print(page.title())
# "is LIVE - TikTok LIVE" → live aktif, gas record
# "Something is wrong on our end" → udah abis, abort
```

Kalo live page bilang offline, jangan launch recorder — bakal exit dengan `USER_NOT_CURRENTLY_LIVE` dan waste waktu.

## camofox-vs-playwright

Untuk cookie extraction di TikTok:
- **Camofox** (`~/.local/bin/camofox eval "document.cookie"`) → cuma return non-HttpOnly cookies. `sessionid_ss` HttpOnly → gak ke-capture.
- **Playwright** (`ctx.cookies()` setelah navigate) → return full list, HttpOnly included.

Pake Playwright untuk setup `cookies.json`.
