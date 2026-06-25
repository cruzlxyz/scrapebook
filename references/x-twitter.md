# X/Twitter — Deep Dive

## single-tweet-no-login

Pattern syndication API buat extract video URL tanpa login.

`https://cdn.syndication.twimg.com/tweet-result?id=<TWEET_ID>&token=0` return JSON payload. Ambil `mediaDetails[0].video_info.variants[]`, filter `content_type === "video/mp4"`, pilih bitrate tertinggi.

Batasan:
- Untuk tweet yang dihapus/suspended → return `{}` atau 404.
- Untuk upload `ext_tw_video` lama → `mediaDetails` ada tapi `video_info.variants` kosong (atau `mediaDetails: []` sama sekali).
- `view_count` selalu 0 — pakai `favorite_count` untuk ranking popularitas.

## yt-dlp-cookie-fallback

Waktu syndication strip `video_info`, fallback ke yt-dlp dengan Netscape cookies:

```bash
yt-dlp --cookies ~/.config/social-dl/cookies/x.com.txt \
  -f "best[ext=mp4]/best" \
  -o "~/Downloads/x/<screen_name>/<tweet_id>.mp4" \
  "https://x.com/<screen_name>/status/<tweet_id>"
```

yt-dlp handle bearer-token exchange-nya internal — gak bisa di-reverse-engineer manual via `page.content()` regex (modern X gak expose URL mp4 di HTML publik lagi).

## cookie-setup

Export Netscape format dari browser yang udah login via extension cookies (e.g. "Get cookies.txt LOCA"). Save ke `~/.config/social-dl/cookies/x.com.txt`.

Validasi:
```bash
head -1 ~/.config/social-dl/cookies/x.com.txt
# Harus: # Netscape HTTP Cookie File
```

Filter expired otomatis sama `netscape_to_playwright.py` — entry dengan timestamp < now di-skip.

## graphql-walker-issues

GraphQL UserMedia hijack tangkap response `i/api/graphql/DpzwOu8Idtlbfqh-Hf718Q/UserMedia` via Playwright `page.on("response")`. Response shape bisa nested:

- **Default** (shallow walker cukup):
  ```
  data.user.result.timeline.timeline.instructions[].entries[] → item.itemContent.tweet_results.result
  ```

- **Wrapped** (perlu recursive walker):
  ```
  data.user.result.timeline.timeline.instructions[].entries[].content.items[] →
    entryId + item.itemContent.tweet_results.result
  ```
  Lihat di `data.user.result.timeline.timeline.instructions[]` dengan type `TimelineTimelineModule`. Recursive walker di `scripts/x_user_top_media.py` handle kedua-duanya.

Pitfall lain:
- Endpoint `__a=1&__d=dis` udah mati → 404.
- Direct fetch dari `page.evaluate()` ke endpoint UserMedia → 403 (gak ada header `x-twitter-*`).
- Sort by `favorite_count` (likes) — `view_count` di-strip ke 0.
- "195 foto & video" di tab Media ≠ 195 video — banyak akun mostly foto. Filter `type === "video"` sebelum sort.

## terjemahan-ui-indonesia

x.com auto-translate ke bahasa user. UI label jadi:
- "Posts" → "Postingan"
- "Replies" → "Balasan"
- "Media" → "Media" (gak berubah)
- "Following" → "Mengikuti"
- "Followers" → "Pengikut"
- "Joined <month>" → "Bergabung <month>"

Field name berubah tapi value numeric (follower count, like count) tetap konsisten.

## mobile-redirect-pitfall

`requests` ke `mobile.twitter.com/<user>/status/<id>` → 302 chain ke `x-safari-https://redirect.x.com/...` → InvalidSchema error karena Python gak handle `x-safari-https://` scheme.

**Fix:** Selalu pakai `https://x.com/...` (HTTPS langsung), atau via Playwright kalau butuh browser context.
