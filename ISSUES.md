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

## Known limitations of the new features

- **Auto-linking does nothing until notes have `aliases:`.** Found by running
  it against the real 18-note vault: zero links fired. The protection logic
  was correct (code, math and existing links all came through untouched), but
  real lecture notes are titled things like "Lecture 4: Linear Algebra
  (cont.); Probability Theory" and nobody writes that phrase in prose, so
  title-only matching almost never matches. Obsidian's `aliases:` frontmatter
  field is now read and is the intended mechanism, but that means the feature
  is opt-in per note rather than automatic. A future version could mine the
  finalize step's own "Key terms" glossary to propose aliases automatically.
- **Finalize-on-Stop is still Gemini-only.** `/finalize-note` calls
  `load_gemini_api_keys()` directly and 502s without one, so a user on
  `groq`/`ollama`/`haiku` gets working live chunks but no whole-video
  regeneration. The live path is fully engine-agnostic; finalize was not
  migrated in the same pass because it has a different prompt shape and its
  own frame-extraction call. This is the biggest inconsistency in the engine
  abstraction right now.
- **Flashcard quality is unvalidated at scale.** Verified working end to end
  (18 real cards from the vectors note, LaTeX intact), but there's no
  evaluation of whether the cards are actually *good* study material across
  different subjects, and no dedupe against cards already exported from the
  same note.
- **Vision support is declared, not detected.** `providers.py` hardcodes
  `supports_vision` per provider based on its default model. Override the
  model with `MARGINALIA_MODEL` and that flag can silently become wrong in
  either direction.

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
- ~~No CI~~ — done. `.github/workflows/ci.yml` runs both suites on every
  push and PR across Ubuntu/macOS/Windows and Python 3.10 + 3.13, and
  uploads a packaged extension zip as a build artifact. 213 tests total
  (177 backend + 36 JS), fully mocked: no network, no keys, no `claude` CLI.

## Code quality (found in the pre-public-launch audit, not yet fixed)

- ~~Duplicated style-instruction prompt text across three clients~~ — done.
  Extracted into `sidecar/prompts.py`; every engine now composes the same
  style contract from one source.
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

### Every AI provider ~~(currently Haiku via local CLI + Gemini via direct API)~~ — mostly DONE

- ~~No shared `Engine` interface; adding a provider meant a new client module
  plus another `if NOTE_ENGINE == "..."` branch~~ — done. `engine_dispatch.py`
  now owns engine selection, `providers.py` is a registry, and
  `openai_compatible.py` is one client for every `/chat/completions` API.
  Adding a provider is a dict entry.
- ~~OpenRouter, Fireworks, Cerebras~~ — done, plus Groq, Together, OpenAI,
  and local Ollama / LM Studio. All share one client and one retry policy.
  `MARGINALIA_MODEL` overrides the model per provider.
- ~~Vision isn't universal; new providers need a capability flag~~ — done.
  `ProviderSpec.supports_vision` gates frame extraction, so text-only engines
  skip the yt-dlp/ffmpeg cost entirely instead of building images nothing
  reads. (Caveat above: the flag is declared per provider, not detected.)
- **Codex still not integrated**, and the ambiguity flagged earlier still
  stands: if the goal is "plug in whatever coding-assistant CLI you already
  pay for, the way `haiku` shells out to the `claude` CLI", that is a
  *subprocess* engine, not a chat-completion provider, and needs its own
  small client rather than a registry entry. Worth deciding which before
  building.
- **Still to do:** per-engine finalize (see the Gemini-only limitation
  above), and automatic fallback when a provider is down or out of quota.

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
- **Not published to the Chrome Web Store.** `scripts/package-extension.sh`
  now builds an upload-ready zip (and CI publishes it as an artifact), so the
  build step exists; what's left is the actual store submission and review,
  which needs a developer account and a privacy-policy page.
