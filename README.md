# makeielts.com

IELTS Reading & Listening practice in the real exam format, with every lost mark explained by the trap behind it.

- `public/` – the deployable site (Vercel: set the output directory to `public`, no build step).
  - `index.html` – the whole app (hash routing, tracking, exam engine).
  - `audio/` – Listening recordings. The site loads them from Cloudflare R2 first (`AUDIO_CDN` in the source) and falls back to these local copies.
- `supabase/functions/grade/` – the edge function that marks full tests server-side, so answer keys never reach the browser.
- `site_src.html` + `make_site.py` – source and build script.
- `content-tools/` – the test pipeline (validate, split public/key, record audio with Kokoro, independent answer check).

Answer keys and test source files are deliberately not in this repo. They live in Supabase (`test_keys`, locked by RLS).
# MakeIelts
