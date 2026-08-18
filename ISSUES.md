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
- ~~README is stale~~ — done. Full rewrite covering the Gemini engine +
  `MARGINALIA_ENGINE` toggle, frame capture, multi-key rotation, the
  finalize-on-stop regeneration step, and the action bar, plus accurate
  test counts (100+34).
- ~~Project renamed from "HoverNotes Clone" to Marginalia, but the local
  folder name and GitHub repo URL still don't match~~ — done. GitHub repo is
  now `Marginalia`, remote updated, git history squashed to drop every old
  reference.

## Known bugs

- **Multi-row LaTeX (`\begin{bmatrix}...\end{bmatrix}`, `pmatrix`, `cases`, etc.)
  renders as flattened plain text instead of a real stacked matrix.** Found
  while recording the demo GIF for this README (2026-08-19), on the "Vectors"
  note's `2 \cdot \begin{bmatrix} 3 \\ 1 \end{bmatrix} = \begin{bmatrix} 6 \\ 2
  \end{bmatrix}` line — rendered as `2 · [3 1] = [6 2]`. Simple inline math
  with no `\\` (`$\vec{v}$`, `$(x,y)$`) renders fine. Root cause: in
  `extension/renderer.js`, `renderMarkdown()` runs `marked.parse()` on the raw
  markdown (including the `$$...$$` block) *before* `renderMathInElement()`
  ever sees it. Markdown's own backslash-escape handling collapses the `\\`
  row-separator inside the math block down to a single `\`, which breaks the
  LaTeX row syntax by the time KaTeX's auto-render walks the DOM — and
  `throwOnError: false` means it fails silently instead of showing an error.
  Fix should mirror the existing `SCREENSHOT_MARKER` placeholder-swap pattern
  already in that file: extract `$$...$$` / `$...$` blocks into placeholders
  *before* `marked.parse()`, restore the original untouched LaTeX source
  after, so KaTeX sees pristine `\\` sequences. Affects both engines equally
  since it's a rendering-layer bug, not a generation-layer one.

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
