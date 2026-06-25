# Platform Lainnya

## Instagram

### Reels (video)
yt-dlp works langsung, CDN publik. Pattern biasa:
```bash
yt-dlp -f "best[ext=mp4]/best" "https://www.instagram.com/reel/<ID>/"
```

### Photos
**yt-dlp GAK BISA.** Return error "No video formats found".

Solusi: Playwright mobile UA + canvas extraction. Lihat `examples/download_ig_photos.py` (akan datang).

Workflow:
1. Login-free, mobile UA
2. Navigate ke `https://www.instagram.com/<user>/`
3. Scroll 8x untuk load more
4. Untuk setiap `<article>`, klik untuk expand
5. Screenshot canvas (extract `src` URL dari `<img>` di modal)
6. Download `?format=jpg&name=orig` untuk original size

### Highlight: rate-limit
Instagram aggressive rate-limit kalau scrape cepet. Tambahin `page.wait_for_timeout(3000-5000)` antar request.

## YouTube
yt-dlp default, no special handling. Format selector `best[ext=mp4]/best` works untuk most cases. Untuk playlist, `--yes-playlist`.

## Reddit
yt-dlp default, support video hosting Reddit (`v.redd.it`) dan embeds (YouTube, streamable). Untuk GIF → MP4: `yt-dlp -f "best[ext=mp4]/best" "https://reddit.com/r/<sub>/comments/<id>"`.

## Vimeo
yt-dlp default, kadang perlu `--referer "https://vimeo.com/<id>"` untuk protected video.

## Facebook
yt-dlp default tapi sering dapet 403 / login wall. Solusi: `--cookies` dari browser yang udah login Facebook.

```bash
yt-dlp --cookies ~/.config/social-dl/cookies/facebook.com.txt \
  -f "best[ext=mp4]/best" \
  "https://www.facebook.com/watch/?v=<id>"
```

## Generic URL
Waktu URL gak match extractor apapun, coba `--dump-json` dulu untuk lihat apa yang ke-detect:
```bash
yt-dlp --dump-json --skip-download "<unknown_url>" 2>&1 | head -50
```
