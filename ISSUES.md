# Known issues / future work

Tracked here as a local backlog. Worth migrating to real GitHub Issues at
some point, but no rush now that the repo's public.

## Portability (blocks public use)

- ~~`VAULT_PATH` is hardcoded to an absolute path on this machine~~ — done.
  Now `MARGINALIA_VAULT_PATH` env var, defaults to `~/MarginaliaNotes`,
  auto-created on import so a missing folder can no longer crash the sidecar
  at startup (previously `StaticFiles` mount raised immediately).
- **`keys.env` location is still `~/.config/keys.env`** with a bespoke regex
  parser, not a standard `.env` in the project root. Added `keys.env.example`
  at the repo root so the format is at least documented; still not a real
  `.env` a public user would expect by convention.
- ~~Self-inflicted migration gotcha from the `VAULT_PATH` fix above~~ — done.
  `MARGINALIA_VAULT_PATH` is now exported permanently in `~/.zshrc`, and the
  sidecar has been restarted under it — confirmed serving the real 18-doc
  vault, not an empty `~/MarginaliaNotes`.
- ~~README is stale~~ — done. Full rewrite covering the Gemini engine +
  `MARGINALIA_ENGINE` toggle, frame capture, multi-key rotation, the
  finalize-on-stop regeneration step, and the action bar, plus accurate
  test counts (100+34).
- ~~Project renamed from "HoverNotes Clone" to Marginalia, but the local
  folder name and GitHub repo URL still don't match~~ — done. GitHub repo is
  now `Marginalia`, remote updated, git history squashed to drop every old
  reference.

## Known bugs

- ~~Multi-row LaTeX (`\begin{bmatrix}...\end{bmatrix}`, `pmatrix`, `cases`,
  etc.) renders as flattened plain text instead of a real stacked matrix~~
  — done. `renderMarkdown()` now extracts `$$...$$` / `$...$` blocks into
  `\x00MATH<n>\x00` placeholders *before* `marked.parse()` touches them
  (escaping each block's own `<`/`>` at extraction time, same trust model as
  the rest of the function), then restores the pristine, unmangled LaTeX
  afterward — mirrors the existing `SCREENSHOT_MARKER` placeholder pattern.
  Two regression tests added (`renderer.test.js`); confirmed live in the
  actual panel on the same "Vectors" note that surfaced the bug — the matrix
  now renders as a real stacked bracket, not flattened text. Affected both
  engines equally, since it was a rendering-layer bug, not a
  generation-layer one.

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

- **No tests at all for `extension/panel.js`** (473 lines) — not just the
  action bar. Only the pure logic modules (`transcript.js`, `renderer.js`)
  have unit tests; everything stateful/DOM-touching in `panel.js` (file
  browser view state, chunk-send error handling, action bar wiring) is
  manually verified in-browser only. At minimum, the pure helpers
  (`resolveImagePaths`, `escapeHtml`, `documentDomain`, `buildObsidianUri`)
  don't need a DOM and could be extracted and unit-tested.
- ~~No test covering the haiku engine's failure path~~ — done. Added
  `test_note_chunk_haiku_engine_502s_when_claude_cli_missing`, since a
  missing `claude` CLI is exactly what a fresh public clone hits first
  (haiku is the default engine).
- **No CI.** Tests exist (100 backend + 34 JS) but nothing runs them
  automatically on push/PR. Worth a basic GitHub Actions workflow before
  going public, so contributors' PRs get checked.

## Code quality (found in the pre-public-launch audit, not yet fixed)

- **Duplicated style-instruction prompt text** across `haiku_client.py`,
  `gemini_client.py`, and `finalize.py` (same paragraph copy-pasted 3x).
  Should be one shared constant so a style-contract change doesn't need
  updating in lockstep in three places.
- **`panel.js` module state doesn't reset on panel close.** `state.viewingFilename`
  / `state.viewingSource` / `savedBodyHtml` survive a close+reopen, so
  `currentFocus()` can briefly reflect the previous session's saved-file view.
  Not a crash, just confusable — worth resetting explicitly in the `hn-close`
  handler.
- **No Windows support documented.** `source venv/bin/activate` appears 3x in
  the README with no `venv\Scripts\activate` equivalent or caveat.
- **No stated Python version floor.** Code uses `str | None` union syntax
  (3.10+ only) with nothing in the README or a `.python-version` file saying
  so — fails with a confusing `TypeError` on older Pythons instead of a clear
  version error.
- **`assets/preview.png` (1.7MB) + `assets/demo.gif` (2.2MB) are committed
  as regular git blobs**, not Git LFS. Fine at this size, but every future
  clone pays that ~4MB forever since it's baked into history now (squashed
  or not) — worth moving to LFS before adding more/larger media.

## Future scope (explicitly out of scope for now — not a v1.0/v1.1 blocker)

The long-term vision: every browser, every AI provider, every OS, every
lecture platform — not just YouTube on Chrome with Haiku or Gemini. None of
this is started. Recording it now so the direction is explicit and the
current architecture's real constraints (below) don't get rediscovered from
scratch later.

### Every browser (currently Chrome/Chromium only)

- The extension is 100% `chrome.*` APIs (`chrome.runtime`, `chrome.action`,
  `chrome.storage` if/when used, `chrome.tabs`) with no browser-abstraction
  layer. Edge/Brave/Arc/Opera are Chromium-based and should mostly work
  unmodified since they implement the same `chrome.*` surface — but this has
  never actually been tested on any of them.
- **Firefox** needs either the `browser.*` namespace directly or the
  `webextension-polyfill` shim, plus Firefox's own manifest quirks
  (`browser_specific_settings`, background page vs. service worker
  differences under MV3). Real work, not a toggle.
- **Safari** is the hard one: Safari Web Extensions require converting the
  extension via Apple's `safari-web-extension-converter` into an actual Xcode
  project, and distribution outside the Mac App Store is limited. This is
  the single biggest lift in the "every browser" goal.
- **Mobile browsers** (Chrome/Firefox on Android, Safari on iOS) are a
  separate problem entirely — most don't support extensions in a way that
  could inject this kind of panel at all.

### Every AI provider (currently Haiku via local CLI + Gemini via direct API)

- `haiku_client.py` (shells out to the local `claude` CLI) and
  `gemini_client.py` (direct multimodal `httpx` POST) are fundamentally
  different plumbing today, picked via one static `NOTE_ENGINE` env var in
  `sidecar/config.py`. There's no shared `Engine` interface — adding a
  provider currently means writing a whole new client module and another
  `if NOTE_ENGINE == "..."` branch in `main.py`, not registering a plugin.
- Real fix, before any new provider gets added: define one interface (e.g.
  `generate_section(transcript, style_anchors, frames) -> str`) that every
  engine implements, and make `NOTE_ENGINE` select from a provider registry
  instead of a hardcoded branch.
- **OpenRouter, Fireworks, Cerebras** are all OpenAI-compatible chat-completion
  APIs — these three are genuinely the easy additions once the interface
  above exists, likely sharing one generic "OpenAI-compatible" client with a
  different `base_url`/model per provider, not three separate client files.
- **Codex**: worth double-checking intent here before building anything — OpenAI's
  Codex/coding models aren't really shaped for lecture-note generation from a
  transcript. If the actual goal is "let people plug in whatever coding
  assistant CLI they already pay for, the way Haiku uses the `claude` CLI,"
  that's a different (and reasonable) integration than "add Codex as a
  chat-completion provider" — worth clarifying which one before implementing.
- **Vision isn't universal.** Only the Gemini engine handles frames today;
  Haiku is transcript-only by design (see `config.py`'s comment on why). Any
  new provider needs an explicit capability flag (`supports_vision: bool`),
  not an assumption that every engine can do both modes — otherwise a
  text-only provider silently gets asked for something it can't do.

### Every OS (currently macOS/Linux, informally)

- Already tracked above (no Windows testing, `venv/bin/activate` throughout
  the README). Restating here as part of the bigger picture: real
  cross-platform support means CI running the test suite on Windows/macOS/
  Linux, not just "probably works since it's mostly pathlib."

### Beyond YouTube: local files, Coursera, Udemy, etc.

- **Local video files**: no path for this exists today at all.
  `transcript_fetcher.py` is built entirely around `youtube_transcript_api`
  — a local `.mp4` has no captions API to call. This needs a real
  speech-to-text pipeline (Whisper or similar) as a new transcript source,
  not a config change.
- **Udemy / Coursera / other paid platforms**: fundamentally different from
  YouTube. These are paywalled and often DRM'd; scraping a transcript
  requires a logged-in session (cookies/auth passed from the extension to
  the sidecar) and per-platform DOM scraping since each site's caption UI
  (where one exists at all — many Udemy courses ship with no captions) is
  different. Also a materially different legal/ToS risk profile than reading
  a public YouTube video's own public transcript API — worth thinking through
  before scraping paid course content, not just an engineering task.
- Each new platform is a new `content_scripts` match pattern in
  `manifest.json` plus real site-specific injection/scraping code — this
  scales linearly with the number of platforms, there's no generic "any
  video site" shortcut.

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
