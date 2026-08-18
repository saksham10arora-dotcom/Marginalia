# Known issues / future work

Tracked here locally while the repo is private. Move each to a real GitHub
Issue when this goes public.

## Portability (blocks public use)

- **`VAULT_PATH` is hardcoded** to an absolute path on this machine
  (`sidecar/config.py`). Anyone else running this needs to edit source to
  point it at their own vault — should be an env var with a sane default,
  documented in the README.
- **`keys.env` location is hardcoded** to `~/.config/keys.env` with a bespoke
  regex parser, not a standard `.env` in the project root. Works fine for
  personal use; a public user would expect `.env` + a documented format.
- ~~README is stale~~ — done. Full rewrite covering the Gemini engine +
  `MARGINALIA_ENGINE` toggle, frame capture, multi-key rotation, the
  finalize-on-stop regeneration step, and the action bar, plus accurate
  test counts (102+32).
- ~~Project renamed from "HoverNotes Clone" to Marginalia, but the local
  folder name and GitHub repo URL still don't match~~ — done. GitHub repo is
  now `Marginalia`, remote updated, git history squashed to drop every old
  reference.

## Reliability

- **Frame capture still depends on YouTube's CDN behaving.** Fixed the
  worst of it (yt-dlp downloads the needed clip directly instead of handing
  ffmpeg a raw URL, plus a 3-attempt retry for the intermittent 403s), but
  this is fundamentally scraping a platform that can change its bot
  detection at any time. If frame capture silently stops working again,
  check `_download_segment()` in `sidecar/frame_extractor.py` first — the
  retry count/backoff may need tuning, or yt-dlp itself may need an update
  (`pip install -U yt-dlp` / `pipx upgrade yt-dlp`) if YouTube changed
  something upstream.
- **Gemini free tier is capped** at 20 `generateContent` calls/day *per key*
  for `gemini-3.5-flash`. Currently mitigated with 3-key rotation (60/day
  total) in `sidecar/key_rotation.py` — if usage grows, either add more
  keys or budget for a paid tier.
- **No automatic engine fallback.** If Gemini's daily quota is exhausted
  mid-session, `/note-chunk` and `/finalize-note` both fail with a 502
  rather than silently dropping to Haiku. Given `NOTE_ENGINE` is a static
  config choice per the original design decision, this is intentional, but
  worth reconsidering if it becomes annoying in practice.

## Test coverage gaps

- **No JS tests for the action bar** (`extension/panel.js`'s copy/download/
  open-in-obsidian/browse-files buttons, added this session). Only the pure
  logic modules (`transcript.js`, `renderer.js`) have unit tests; DOM-level
  interaction is manually verified in-browser only.
- **No CI.** Tests exist (102 backend + 28 JS) but nothing runs them
  automatically on push/PR. Worth a basic GitHub Actions workflow before
  going public, so contributors' PRs get checked.

## Product gaps (not urgent, just noted)

- **Live per-chunk notes are chunk-blind** by design — each 60s chunk only
  sees its own transcript slice, so section boundaries can be arbitrary
  mid-thought. The finalize-on-stop step closes this gap by regenerating
  the whole note with full video context, but the live *in-progress* view
  (before you hit Stop) still has this limitation. Not planned to fix —
  live is meant to be a rough draft, finalize is the real output — but
  worth being explicit about if a user asks why the live notes look choppy.
- **No packaging for the Chrome extension.** Must be loaded unpacked via
  Developer Mode; not published to the Chrome Web Store. Fine for personal
  use, would need a build/publish step for wider distribution.
