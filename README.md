# media-download

Kumpulan resep download video dari platform sosial — TikTok, X/Twitter,
Instagram, YouTube, Reddit, Vimeo, Facebook. Dibangun di atas `yt-dlp` dengan
fallback khusus per platform untuk kasus-kasus dimana extractor default gagal.

Diekstrak dari workflow AI agent production; setiap resep di sini sudah
terverifikasi lewat download nyata.

## Instalasi — pilih salah satu

**Opsi A: Pakai sebagai skill (recommended untuk AI agent)**

Cukup copy `SKILL.md` ke folder skills agent kamu. Agent langsung tau kapan
dan bagaimana pakai repo ini tanpa perlu baca README.

```bash
# Untuk Hermes Agent:
mkdir -p ~/.hermes/skills/productivity
cp SKILL.md ~/.hermes/skills/productivity/media-download/SKILL.md

# Untuk OpenClaw:
cp SKILL.md ~/.openclaw/skills/media-download.md
```

**Opsi B: Pakai sebagai repo (untuk script manual)**

```bash
git clone https://github.com/0xcruzl/media-download
cd media-download
pip install -r requirements.txt    # yt-dlp, curl_cffi
bash install.sh                    # symlink wrapper scripts
```

Selesai. Tinggal run script di `examples/` atau ikutin resep di `SKILL.md`.

## Apa yang kamu dapat

- **Decision tree** buat pilih extractor yang tepat per platform (gak perlu nebak)
- **Cookie handling** — format Netscape, filter expired, konversi ke Playwright JSON
- **Fallback strategy** untuk 3 mode kegagalan paling umum:
  - X syndication API drop `video_info` untuk upload `ext_tw_video` lama
  - TikTok CDN return audio-only untuk creator cross-region / Singapore
  - Shortlink `vt.tiktok.com` nyangkut di interstitial login wall
- **Bulk scraper** — top-N video by likes dari X, scrape profile video dari TikTok
- **Diagnostic** — one-liner `ffprobe` buat deteksi file region-locked yang rusak

## Struktur repo

```
media-download/
├── README.md                   # file ini
├── SKILL.md                    # manifest skill (drop ke ~/.hermes/skills/)
├── install.sh                  # installer satu baris
├── requirements.txt
├── LICENSE                     # MIT
│
├── scripts/                    # utilitas Python yang bisa langsung dijalankan
│   ├── netscape_to_playwright.py    # konversi cookie X
│   └── x_user_top_media.py          # bulk scrape top-N video X
│
├── references/                 # dokumentasi mendalam (baca untuk konteks)
│   ├── x-twitter.md            # syndication JSON shape, terjemahan UI, GraphQL
│   ├── tiktok.md               # vt.tiktok.com redirect, diagnostic region-lock
│   └── platforms.md            # quirk IG/Reddit/Vimeo/Facebook
│
└── examples/                   # resep copy-paste per platform
    ├── download_x_top_videos.py        # X: top-N video dari user
    ├── download_tiktok_profile.py      # TikTok: scrape profile
    ├── download_ig_photos.py           # IG: download foto saja
    └── record_tiktok_live.sh           # TikTok: rekam LIVE stream
```

Setiap `examples/` self-contained — copy, edit username, run. Setiap
`references/` jelasin *kenapa* resepnya bekerja begitu.

## Cheatsheet platform

| Platform | Resep | Butuh login? | Catatan |
|---|---|---|---|
| X/Twitter single tweet | `examples/download_x_top_videos.py` | disarankan | syndication API jalan tanpa login tapi strip beberapa video |
| X/Twitter top-N dari user | `examples/download_x_top_videos.py` + `scripts/x_user_top_media.py` | ya | GraphQL hijack, sort by likes |
| TikTok video (URL panjang) | yt-dlp dengan `--extractor-args` | tidak | lihat `references/tiktok.md` |
| TikTok profile | `examples/download_tiktok_profile.py` | tidak | list ranked by views via Camofox |
| TikTok LIVE | `examples/record_tiktok_live.sh` | ya | butuh cookie `sessionid_ss` |
| Instagram reel | yt-dlp default | tidak | CDN publik works |
| Instagram foto | `examples/download_ig_photos.py` | tidak | yt-dlp GAK BISA download foto |
| YouTube / Reddit / Vimeo / Facebook | yt-dlp default | tidak | ekstraksi standar |

## Decision tree

```
Punya URL?
├─ X/Twitter tweet URL?
│  ├─ Ada tweet ID → references/x-twitter.md#single-tweet-no-login
│  │  └─ video_info missing → references/x-twitter.md#yt-dlp-cookie-fallback
│  └─ Mau top-N dari user → examples/download_x_top_videos.py
├─ X/Twitter user URL?
│  └─ scripts/x_user_top_media.py
├─ TikTok vt.tiktok.com shortlink?
│  └─ references/tiktok.md#shortlink-redirect
├─ TikTok video URL (panjang)?
│  └─ references/tiktok.md#long-url-download
├─ TikTok profile?
│  └─ examples/download_tiktok_profile.py
├─ TikTok LIVE?
│  └─ examples/record_tiktok_live.sh
└─ Instagram?
   ├─ /reel/ → yt-dlp default
   └─ /p/ (foto) → examples/download_ig_photos.py
```

## Setup cookie

X/Twitter dan TikTok LIVE keduanya lebih bagus pake cookie authenticated.
Walkthrough lengkap di `references/x-twitter.md#cookie-setup` dan
`references/tiktok.md#live-recorder-cookies`.

### X/Twitter — format Netscape

```bash
yt-dlp --cookies ~/.config/social-dl/cookies/x.com.txt \
  -f "best[ext=mp4]/best" \
  -o "%(id)s.%(ext)s" \
  "https://x.com/<user>/status/<tweet_id>"
```

### TikTok LIVE — format JSON

Simpan di `cookies.json` sebelah recorder:

```json
{
  "sessionid_ss": "<extract dari browser ctx.cookies()>",
  "tt-target-idc": "useast2a",
  "msToken": "<opsional>",
  "odin_tt": "<opsional>"
}
```

Tanpa `sessionid_ss`, recorder gagal dengan `LiveNotFound: Unable to retrieve
live streaming url` (HTTP 403 di endpoint webcast).

## Pitfall umum

| Gejala | Penyebab | Lihat dimana |
|---|---|---|
| `yt-dlp` Twitter gagal di login wall | Tidak ada cookie | `references/x-twitter.md#per-tweet-fallback-via-yt-dlp--netscape-cookies` |
| `yt-dlp` return audio-only mp4 untuk video TikTok | Region-locked (creator Singapore → `alisg` IDC) | `references/tiktok.md#region-locked-audio-only` |
| URL `vt.tiktok.com` hang di interstitial | `requests` follow redirect chain ke login wall | `references/tiktok.md#shortlink-redirect` |
| X syndication return tweet tapi tidak ada `video_info` | Upload `ext_tw_video` lama | `references/x-twitter.md#single-tweet-no-login` |
| Top-N X scrape return 0 video | Wrapper `TimelineTimelineModule.items[]` di sekitar tweet | `references/x-twitter.md#graphql-walker-issues` |
| TikTok LIVE recorder bilang "Unable to retrieve live streaming url" | Tidak ada `sessionid_ss` di `cookies.json` | `references/tiktok.md#live-recorder-cookies` |
| TikTok LIVE recorder exit langsung bilang "not currently hosting" | Creator baru aja ended live-nya | `references/tiktok.md#stale-live-detection` |

## Diagnostic: file ini beneran video?

Setelah download, verifikasi file-nya bukan junk region-locked:

```bash
ffprobe -v error -show_streams video.mp4 2>&1 | grep codec_type
# Kalau output cuma "audio" → region-locked, file MP3-only, hapus
```

Penjelasan lengkap di `references/tiktok.md#region-locked-audio-only`.

## Agent yang kompatibel

Dibuat untuk drop ke framework AI agent apapun yang punya tiga kapabilitas:
shell execution, browser automation, dan filesystem access. Terverifikasi jalan di:

- **[Hermes Agent](https://github.com/hermes-agent/hermes-agent)** — environment
  authoring utama. Langsung jalan via toolset `terminal`, `browser`, dan `file`.
  Untuk hasil terbaik, copy `SKILL.md` ke `~/.hermes/skills/productivity/media-download/SKILL.md`.
- **OpenClaw** — jalan dengan cara yang sama; tool `shell_exec` + `browser_navigate`
  OpenClaw cover semua resep di repo ini. Pakai script di `examples/` sebagai
  template task OpenClaw.

### Requirements untuk agent apapun

| Kapabilitas | Dipake untuk |
|---|---|
| Shell execution | Call `yt-dlp`, diagnostic `ffprobe`, operasi file |
| Browser automation | Camofox/Playwright buat shortlink TikTok, login X, ekstrak canvas foto IG |
| File system | Read/write cookie, simpan download ke `~/Downloads/<platform>/` |

Kalau agent kamu punya ketiganya, semua script di repo ini jalan apa adanya.

## Kenapa repo ini ada

Default `yt-dlp` kerja untuk ~80% kasus. 20% sisanya adalah gotcha spesifik
platform (region lock, syndication strip, interstitial redirect, GraphQL
wrapping) yang gak obvious sampai kamu ketemu langsung. Repo ini dokumentasi
semua pitfall yang udah kita temuin dan workaround yang work.

Kalau resep berhenti kerja, buka issue dengan:
1. Command persis yang kamu run
2. Output error (pake flag `-v`)
3. URL sample yang reproduce

## Lisensi

MIT
