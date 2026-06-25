---
name: scrapebook
description: Download video dan audio dari platform sosial (X/Twitter, TikTok, YouTube, Instagram, Reddit, Vimeo, Facebook) pake yt-dlp. Cover install PEP 668, workflow test-before-download, quirks URL ID resolution, deteksi deleted/private, format cookie Camofox/Playwright (konversi Netscape → Playwright JSON), dan X/Twitter syndication API buat ekstraksi URL video tanpa login. Pake skill ini waktu user minta download, simpan, atau arsipkan video/audio dari URL sosial media.
tags: [media, download, video, audio, yt-dlp, social-media, x, twitter, tiktok, youtube, gallery-dl, cookies, authenticated, impersonate, curl_cffi]
---

# scrapebook

Download video dan audio dari platform sosial. Tool utama: **yt-dlp**. Fallback: syndication API, scrape Camofox, Playwright + browser context.

## Cara install

Cukup copy `SKILL.md` ini ke folder skills agent. Gak perlu clone repo penuh kalau cuma butuh panduan.

```bash
# Untuk Hermes Agent:
mkdir -p ~/.hermes/skills/productivity
cp SKILL.md ~/.hermes/skills/productivity/scrapebook/SKILL.md

# Untuk OpenClaw:
cp SKILL.md ~/.openclaw/skills/scrapebook.md
```

Atau clone repo penuh kalau mau run script manual:

```bash
git clone https://github.com/cruzlxyz/scrapebook
cd scrapebook
pip install -r requirements.txt    # yt-dlp, curl_cffi
bash install.sh                    # symlink wrapper scripts
```

## Struktur repo

```
scrapebook/
├── README.md
├── SKILL.md                      # file ini
├── install.sh
├── requirements.txt
├── LICENSE
├── scripts/
│   ├── netscape_to_playwright.py # konversi cookie X
│   └── x_user_top_media.py       # bulk scrape top-N X
├── references/
│   ├── x-twitter.md              # syndication + GraphQL deep-dive
│   ├── tiktok.md                 # vt.tiktok.com + region-lock
│   └── platforms.md              # quirk IG/Reddit/Vimeo/Facebook
└── examples/
    ├── download_x_top_videos.py
    ├── download_tiktok_profile.py
    ├── download_ig_photos.py
    └── record_tiktok_live.sh
```

## Decision tree cepat

1. **X/Twitter single tweet** → syndication API (`cdn.syndication.twimg.com/tweet-result?id=<TWEET_ID>&token=0`), pilih mp4 variant bitrate tertinggi. TANPA LOGIN.
2. **X/Twitter user timeline** → syndication gak expose. Pake Playwright + Netscape cookies dari `~/.config/social-dl/cookies/x.com.txt` (mobile UA) → scrape regex `/status/(\d+)`. Buat **top-N by popularity** → hijack response GraphQL `UserMedia` (lihat `scripts/x_user_top_media.py`).
3. **TikTok single video** → yt-dlp dengan mobile URL + Chrome-145 impersonate. Desktop URL → 403.
4. **TikTok profile scrape** → yt-dlp `--flat-playlist` dulu; kalau rate-limited, fallback ke Camofox + auth cookies → `SIGI_STATE.ItemModule[id].video.playAddr`.
5. **IG reels** → yt-dlp (works, CDN publik).
6. **IG foto** → **yt-dlp GAK BISA**. Lihat `examples/download_ig_photos.py` (Playwright mobile UA + canvas extraction).
7. **YouTube / Reddit / Vimeo / Facebook** → yt-dlp default.
8. **Generic paste URL** → `yt-dlp --dump-json --skip-download "<url>"` dulu buat test ekstraksi.

## Install dependency

PEP 668 ngeblokir system pip — selalu pake venv:

```bash
~/.hermes/hermes-agent/venv/bin/pip install -U yt-dlp curl_cffi
```

Atau pake installer bundled:

```bash
bash install.sh
```

## X/Twitter — syndication API (tanpa login)

Pattern buat URL video single tweet:

```python
import requests, json, re
tweet_id = "2069771028948299979"
r = requests.get(f"https://cdn.syndication.twimg.com/tweet-result?id={tweet_id}&token=0",
                 headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
d = r.json()
vids = [v for v in d["mediaDetails"][0]["video_info"]["variants"] if v["content_type"] == "video/mp4"]
best = max(vids, key=lambda x: x.get("bitrate", 0))
# download best["url"] ke ~/Downloads/x/<screen_name>/<tweet_id>.mp4
```

Pitfall:
- Return `{}` atau 404 untuk tweet yang dihapus/di-suspend.
- `lang=zxx` artinya gak ada teks (cuma media).
- Pilih `bitrate` bukan `width` — bucket width ngulang di bitrate yang sama.
- Gak perlu login, gak ada rate-limit di volume rendah (beberapa/detik).
- **`mediaDetails` kosong untuk tweet yang ada video** — untuk beberapa tweet video, endpoint syndication return payload lengkap tapi dengan `mediaDetails: []` (bahkan thumbnail foto juga gak ada). Tweet jelas punya konten video, tapi endpoint publik strip semuanya. Solusi: yt-dlp dengan Netscape cookies di `https://x.com/<user>/status/<id>`.

## X/Twitter — per-tweet fallback via yt-dlp + Netscape cookies

Kalau syndication strip `video_info`, atau GraphQL hijack gak nangkep tweet-nya (sering kejadian untuk pinned post / tweet high-engagement bahkan setelah 40 scroll), pake yt-dlp langsung:

```bash
~/.hermes/hermes-agent/venv/bin/yt-dlp \
-f "best[ext=mp4]/best" \
-o "~/Downloads/x/<screen_name>/<tweet_id>.mp4" \
--cookies ~/.config/social-dl/cookies/x.com.txt \
"https://x.com/<screen_name>/status/<tweet_id>"
```

**Catatan path:** binary ada di `~/.hermes/hermes-agent/venv/bin/yt-dlp` (absolute). Di dalam `execute_code`'s `subprocess.run`, `~` GAK di-expand — pake `os.path.expanduser()` dulu. Di dalam tool `terminal()`, `~` di-expand sama shell.

## X/Twitter — user timeline (butuh login)

Syndication gak return user timeline. Workflow:
1. Load Netscape cookies dari `~/.config/social-dl/cookies/x.com.txt`
2. Konversi ke Playwright JSON (drop expired, strip `\n`, strip field `httpOnly` — Playwright nolak)
3. Launch chromium dengan iPhone mobile UA
4. Buat **listing video-only** → navigate ke `https://x.com/<screen_name>/media` (JANGAN tab Posts `/` — replies bikin polusi list ID). Scroll 8x untuk load lebih banyak.
5. Extract tweet IDs: `re.findall(r'/status/(\d{10,})', page.content())`
6. Untuk setiap ID, hit syndication API → pilih mp4 terbaik → download
7. **Sort by `favorite_count`** (likes) — syndication strip `view_count` ke 0, jadi likes satu-satunya proxy popularitas yang reliable.

```python
import time, re
from playwright.sync_api import sync_playwright

cookies = []
with open("/home/ubuntu/.config/social-dl/cookies/x.com.txt") as f:
    for line in f:
        if line.startswith("#") or not line.strip(): continue
        parts = line.split("\t")
        if len(parts) < 7: continue
        exp = int(parts[4]) if parts[4].isdigit() else -1
        if exp > 0 and exp < time.time(): continue  # skip expired
        cookies.append({
            "name": parts[5],
            "value": parts[6].strip(),
            "domain": parts[0] if parts[0].startswith(".") else "." + parts[0],
            "path": parts[2],
            "secure": parts[3] == "TRUE",
            "expires": exp if exp > 0 else -1,
        })

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(
        viewport={"width": 390, "height": 844},
        user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    )
    ctx.add_cookies(cookies)
    page = ctx.new_page()
    page.goto("https://x.com/<screen_name>", wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(5000)
    html = page.content()
    ids = list(dict.fromkeys(re.findall(r'/status/(\d{10,})', html)))
    # dedupe, lalu syndication API untuk masing-masing
```

Pitfall:
- `requests` (bukan Playwright) → `x-safari-https://redirect.x.com/...` chain 302 → error InvalidSchema. Pake Playwright.
- Tab default "Posts" cuma load ~10-20 yang paling recent. Pindah ke tab "Media" buat listing video-only.
- Tab Replies juga return ID — filter atau pake tab Posts.
- UI Indonesia di x.com auto-translate → "Bergabung Mei 2026", "Postingan finez", "Mengikuti", "Pengikut". Field name berubah tapi value masih kebaca.

## TikTok — short URL profile + per-post view ranking

Shortlink `vt.tiktok.com/...` (sering dipake di DM / repost) bawa interstitial yang ngebrek `requests`. Buka via Camofox, terus run JS di halaman profile buat extract ranked list — view count di-render sebagai teks di setiap card.

```bash
~/.local/bin/camofox open "https://vt.tiktok.com/<CODE>/"
# stdout: tabId: <uuid>
sleep 5
~/.local/bin/camofox eval "JSON.stringify(Array.from(document.querySelectorAll('a[href*=\"/video/\"]')).map(a => ({url: a.getAttribute('href'), text: a.innerText.slice(0,150)})))" "<tabId>"
```

Field `text` adalah view count (mis. `"636.5K"`, `"310K"`, `"9558"`). Sort by parsed number desc waktu user bilang "top N by views". Lalu download by URL `https://www.tiktok.com/@<handle>/video/<ID>` via yt-dlp — URL panjang itu jalan langsung tanpa impersonate. Body teks profile juga nge-reveal username/bio/followers (mis. `RatcihMitcha (@atihhh.__) | TikTok` title).

Parse view count:
```python
def parse_views(s):
    s = s.strip().split()[0].replace(",", "")  # strip "Pinned", koma
    if s.endswith("K"): return float(s[:-1]) * 1_000
    if s.endswith("M"): return float(s[:-1]) * 1_000_000
    if s.endswith("B"): return float(s[:-1]) * 1_000_000_000
    try: return float(s)
    except: return 0
```

## TikTok — single video

```bash
yt-dlp -f "best[ext=mp4]/best" \
  "https://www.tiktok.com/@user/video/<ID>" \
  --extractor-args "tiktok:webpage_url=https://m.tiktok.com/v/<ID>"
# mobile URL menghindari 403; short URL vt.tiktok.com redirect → resolve dulu
```

**Pitfall — region-locked / cross-region audio-only output:** beberapa creator (terverifikasi di creator Singapore `@chintya.ay`, video `7648584635051527431`, Jun 2026) return file `.mp4` yang valid tapi MP3-only — `ffprobe` nunjukin `codec_name=mp3`, gak ada video stream, ~175KB, 11s. URL CDN-nya mengandung `mime_type=audio_mpeg`. Gak ada fix: cookies gak ngebantu, `--impersonate chrome` error `Unable to extract universal data for rehydration`, `/embed/v2/<id>` gak disupport. **Skip file-nya dan kasih tau user video ID spesifik itu region-locked.**

Diagnostic sebelum nyatain "selesai":
```bash
ffprobe -v error -show_streams <file>.mp4 2>&1 | grep codec_type
# Kalau cuma "audio" → region-locked, file junk, hapus dan kasih warning
```

## TikTok — profile scrape

```bash
yt-dlp --flat-playlist --print "%(id)s|%(title)s|%(view_count)s|%(duration)s" \
  "https://www.tiktok.com/@<user>" 2>&1 | head -30
```
Lalu iterate ID-nya.

Kalau rate-limited: Camofox + auth cookies → eval JS:
```javascript
JSON.stringify(window.SIGI_STATE.ItemModule)
```
Extract `playAddr`, download via `page.request.get()` dengan browser-context cookies.

## TikTok — rekam LIVE stream

Tool: [`Michele0303/tiktok-live-recorder`](https://github.com/Michele0303/tiktok-live-recorder) (clone ke `~/tiktok-live-recorder`, terus `uv venv && uv sync`). Bungkus dengan shell script di `~/.local/bin/tiktok-live-recorder` yang `cd` ke repo dan `uv run python src/main.py "$@"`.

```bash
tiktok-live-recorder -user <username> -mode manual -output ~/Downloads/tiktok/<username> -no-update-check
# Atau auto-wait + record waktu creator live:
tiktok-live-recorder -user <username> -mode automatic -automatic_interval 5
```

**Butuh cookie session TikTok** — tanpa itu tool return `LiveNotFound: Unable to retrieve live streaming url` (HTTP 403 di `https://webcast.tiktok.com/webcast/room/enter/`). Isi `~/tiktok-live-recorder/src/cookies.json`:

```json
{
  "sessionid_ss": "<extract dari logged-in browser context>",
  "tt-target-idc": "useast2a",
  "msToken": "<opsional tapi ngebantu>",
  "odin_tt": "<opsional>"
}
```

Pitfall:
- **`uv` wajib** — project ini ship `uv.lock` dan expect `uv sync`, bukan `pip install` biasa. Install `uv` via `curl -LsSf https://astral.sh/uv/install.sh | sh` dan tambahin `~/.local/bin` ke PATH.
- **`-mode manual` exit segera setelah live end** — tool poll room, record selama live, exit bersih.
- **Error `RETRIEVE_LIVE_URL` punya dua penyebab** — auth failure (gak ada `sessionid_ss` → 403) DAN "creator baru aja ended live-nya" (webcast return gak ada `live_url` untuk room offline). Cek halaman live di Camofox dulu: kalau title diakhiri `is LIVE - TikTok LIVE`, cookie masalahnya; kalau title nunjukin `Something is wrong on our end`, live-nya emang udah abis.
- **`USER_NOT_CURRENTLY_LIVE` itu final** — konfirm offline, jangan retry di loop.
- **Deteksi live basi** — antara "user bilang live" dan recorder beneran jalan, beberapa menit bisa lewat. Selalu re-check status live via Camofox segera sebelum launch recorder.

## Pitfall umum

- **yt-dlp Twitter single tweet gagal di login wall** → pake syndication API.
- **yt-dlp Instagram foto** → "No video formats found" → defer ke `examples/download_ig_photos.py`.
- **`hermes update` bunuh yt-dlp/curl_cffi** → install ulang via pip.
- **Mirror Nitter sering offline** (403/refused) → jangan andalin.
- **User mau file VIDEO, bukan screenshot thumbnail** — waktu "Liat N video" diminta, kirim masing-masing `.mp4` langsung via `MEDIA:/path`. Kirim thumbnail JPG hasil `ffmpeg` kena koreksi ("jngan di ss tapi videonya"). Extract thumbnail cuma sebagai fallback kalau video kegedean buat di-attach.
- **Syndication API drop `video_info` untuk beberapa tweet** — upload `ext_tw_video` lama return `{}` atau gak ada `mediaDetails[0].video_info` padahal tweet IS contain video. Selalu pake GraphQL `UserMedia` hijack untuk ranking-by-popularity; cuma pake syndication untuk direct URL extraction kalau tweet ID udah diketahui.
- **GraphQL UserMedia hijack skip beberapa top video bahkan dengan 40 scroll** — pinned post dan tweet high-engagement kadang gak muncul di response `UserMedia` yang ke-capture. Kalau target ID missing setelah hijack, fallback ke per-tweet yt-dlp dengan cookies.
- **Cookie X format Netscape** — `~/.config/social-dl/cookies/x.com.txt` itu export Netscape ytdlp. Pass langsung ke yt-dlp via `--cookies <path>`. Cuma konversi ke Playwright JSON kalau scraping via Playwright `add_cookies()`.
- **Short URL `vt.tiktok.com` butuh browser beneran** — `requests` follow chain tapi mendarat di interstitial login wall. Pake Camofox `open` (binary di `~/.local/bin/camofox`); setelah `open` return `tabId: <uuid>` di stdout, tunggu 4 detik untuk redirect, terus `camofox eval` buat ambil data.
- **Tab `/media` lebih bagus dari tab `/` Posts** buat scrape video — tab Posts campur replies ke timeline; `/media` adalah gallery dan kasih post ID yang bersih.
- **Shortlink `vt.tiktok.com` resolve di Camofox** — buka short URL, tunggu 5 detik untuk redirect, terus `document.title` nge-reveal username asli.

## X/Twitter — bulk scrape video/foto via GraphQL hijack (butuh login)

Syndication API GAK expose user media list, DAN return foto-only untuk banyak tweet lama (dimana `extended_entities.media[].type === "photo"` meskipun ada video ter-attach). Untuk "top N video/foto dari user ini" → hijack response GraphQL `UserMedia` yang ditembak tab Media.

### Robust recursive walker (resep utama)

Shallow walker di versi sebelumnya return 0 video di akun yang mana entry-nya dibungkus dalam `TimelineTimelineModule.items[]` (jadi default di `@plaaxne` Jun 2026). Recursive walker handle semua kedalaman nesting:

```python
from playwright.sync_api import sync_playwright
import time, json

cookies = []
with open("/home/ubuntu/.config/social-dl/cookies/x.com.txt") as f:
    for line in f:
        if line.startswith("#") or not line.strip(): continue
        parts = line.split("\t")
        if len(parts) < 7: continue
        exp = int(parts[4]) if parts[4].isdigit() else -1
        if exp > 0 and exp < time.time(): continue
        cookies.append({
            "name": parts[5], "value": parts[6].strip(),
            "domain": parts[0] if parts[0].startswith(".") else "." + parts[0],
            "path": parts[2], "secure": parts[3] == "TRUE",
            "expires": exp if exp > 0 else -1,
        })

captured = []
videos = []
seen = set()

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(viewport={"width": 390, "height": 844},
        user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")
    ctx.add_cookies(cookies)
    page = ctx.new_page()
    def on_resp(r):
        if "UserMedia" in r.url and r.status == 200:
            try: captured.append(r.json())
            except: pass
    page.on("response", on_resp)
    page.goto("https://x.com/<screen_name>/media", wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(5000)
    for _ in range(40):
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
                    if m.get("type") == "video":
                        mp4s = [v for v in m["video_info"]["variants"]
                                if v.get("content_type") == "video/mp4"]
                        if mp4s:
                            best = max(mp4s, key=lambda x: x.get("bitrate", 0))
                            videos.append({
                                "id": tid,
                                "url": best["url"],
                                "likes": legacy.get("favorite_count", 0),
                                "rt": legacy.get("retweet_count", 0),
                                "dur_ms": m["video_info"].get("duration_millis", 0),
                                "created_at": legacy.get("created_at"),
                            })
                            seen.add(tid); break
        for v in obj.values(): walk(v)
    elif isinstance(obj, list):
        for v in obj: walk(v)

for body in captured: walk(body)
videos.sort(key=lambda x: -x["likes"])
```

Untuk foto, ganti branch `type == "video"` dengan:
```python
if m.get("type") == "photo":
    base = m.get("media_url_https", "")
    videos.append({
        "id": tid, "likes": legacy.get("favorite_count", 0),
        "urls": [base + "?format=jpg&name=orig"] if base else [],
        "created_at": legacy.get("created_at"),
    })
    seen.add(tid); break
```

`?format=jpg&name=orig` return JPG original yang di-upload (100-450KB kecil / ~3MB high-res).

### Pitfall — GraphQL hijack

- **Endpoint `/__a=1&__d=dis` udah mati** untuk X.com — return 404. Pake `i/api/graphql/DpzwOu8Idtlbfqh-Hf718Q/UserMedia` (yang ditembak UI X sendiri), di-capture via Playwright `page.on("response")`.
- **Direct `fetch()` dari `page.evaluate()` ke endpoint yang sama dengan cookie `csrf` → 403** bahkan dengan cookie valid. Request yang di-init browser (via listener `page.on("response")`) kerja karena bawa header `x-twitter-*` yang bener yang ditambahin X otomatis.
- **Syndication API return tipe `photo` untuk tweet yang JUGA contain video** — extractor syndication drop `video_info` untuk upload `ext_tw_video` lama. Selalu pake GraphQL hijack buat klasifikasi "user punya video".
- **Total tab Media ≠ semua video** — banyak akun nunjukin "195 foto & video" tapi cuma 11 yang video. Foto jauh lebih banyak dari video; request user untuk "top 10 video" butuh filter `type==="video"` sebelum sort.
- **Sort by `favorite_count`** — syndication `view_count` itu 0, dan GraphQL hijack juga gak expose view count secara reliable. Likes adalah proxy popularitas.

## Output path

- X/Twitter video: `~/Downloads/x/<screen_name>/<tweet_id>.mp4`
- X/Twitter foto: `~/Downloads/x/<screen_name>/photos/<tweet_id>_<idx>.jpg` (pake subfolder `photos/` buat pisah dari video)
- TikTok video: `~/Downloads/tiktok/<handle>/<video_id>.mp4`
- TikTok LIVE: `~/Downloads/tiktok/<handle>/<timestamp>.mp4` (auto-named sama recorder)
- IG foto: `~/Downloads/instagram/<username>/photos/<shortcode>_<idx>.jpg`

## Referensi

- `references/x-twitter.md` — syndication JSON shape lengkap, pitfall mobile redirect, terjemahan UI Indonesia, pola bulk download
- `references/tiktok.md` — vt.tiktok.com shortlink redirect, diagnostic region-lock, setup cookie LIVE recorder
- `references/platforms.md` — quirk IG/Reddit/Vimeo/Facebook

## Script

- `scripts/netscape_to_playwright.py` — konversi `~/.config/social-dl/cookies/x.com.txt` (Netscape) ke list cookie Playwright JSON, skip yang expired
- `scripts/x_user_top_media.py` — bulk scrape top-N video (atau foto) dari akun X via GraphQL UserMedia hijack; handle load cookie + scroll + capture response GraphQL + filter per-tipe + sort-by-likes + download
