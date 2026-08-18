# Gemini multimodal note generation

## Why

The current pipeline (`sidecar/haiku_client.py`) only ever sees transcript
text. It has no way to catch content that's on the board/slide but never
said out loud. The Stat110 pipeline (`scripts/gemini_notes.py` in the obs
vault) already solved this for offline/batch lecture notes by sending
Gemini both the transcript and the video's screenshots, letting Gemini
judge which screenshots add real information. This spec adapts that same
approach to Marginalia's live, incremental (60-second-chunk)
architecture.

## What's different from the Stat110 pipeline

Stat110's pipeline downloads the whole video with `yt-dlp` up front (it's
an offline batch job for one finished lecture) and writes prose-only
descriptions of useful frames, with an invisible HTML comment as the only
trace of which frame was used — no screenshot ever appears in the note.

Marginalia is live: the video is still playing, and notes are
written 60 seconds at a time as chunks arrive. And per this session's
discussion, screenshots that pass Gemini's usefulness check should be
**visibly embedded** in the note (not just described in prose), since a
real diagram is more faithful than an AI's paraphrase of one.

## Architecture

No changes to the Chrome extension — the engine choice is entirely
server-side, so the extension keeps sending the same `/note-chunk`
payload it always has.

### New files

**`sidecar/frame_extractor.py`**
- `resolve_stream_url(video_url) -> str`: runs `yt-dlp -g <url>` once per
  video to get a direct CDN stream URL (no download). Cached in memory
  keyed by video_id, since the signed URL stays valid for hours and
  chunks for the same video arrive repeatedly.
- `extract_candidate_frames(stream_url, start_ts, end_ts, max_frames=3) ->
  list[(timestamp_sec, jpeg_bytes)]`: vendors the ffmpeg interval-sample +
  perceptual-hash dedup logic from `scripts/wn_frames.py` (unchanged
  algorithm — 1 frame/3s, keep only if visually distinct from the last
  kept frame), pointed at the remote stream URL instead of a local file so
  no video download is needed. ffmpeg can seek within a remote HTTP(S)
  stream with `-ss`/`-to` the same way it seeks a local file.

**`sidecar/gemini_client.py`**
- `call_gemini(transcript_chunk, video_title, video_url, start_ts, end_ts,
  style_anchors, frames) -> str`: mirrors `call_haiku()`'s signature so
  `main.py` can call either interchangeably. Sends transcript + candidate
  frame images to `gemini-3.5-flash` in one multimodal `httpx` POST.
- Each candidate frame gets a deterministic filename before the call
  (`<video-slug>-t<HHMMSS>.jpg`). The prompt instructs Gemini: for each
  frame, judge whether it shows something the transcript doesn't already
  say — a formula, diagram, or worked example. If yes, embed it with
  `![Captured video screenshot](hover-notes-images/<that-exact-filename>)`
  at the relevant point, plus a sentence on what's new in it, plus the
  capture timestamp. If no — empty board, redundant with transcript,
  speaker blocking it — skip it completely, no mention at all.
- After the response comes back, `main.py` regex-scans the returned
  markdown for `hover-notes-images/<filename>` references and only writes
  the matching candidate frame's bytes to disk for filenames Gemini
  actually used. Frames it silently dropped are discarded, never touching
  disk. This is the single source of truth for "which frame got kept" —
  no separate structured output needed, just string-matching against
  Gemini's own markdown.

### Changed files

**`sidecar/config.py`**: adds `NOTE_ENGINE =
os.environ.get("HOVERNOTES_ENGINE", "haiku")` and Gemini key loading
(same `~/.config/keys.env` regex-parse pattern `scripts/gemini_notes.py`
already uses — no new dependency).

**`sidecar/main.py`**: `note_chunk()` branches on `NOTE_ENGINE`. Haiku
path is unchanged. Gemini path additionally resolves the stream URL,
extracts candidate frames for that chunk's `[start_ts, end_ts]` window,
passes them into `call_gemini()`, and saves any frames Gemini actually
used into `note_path.parent / "hover-notes-images"` (matching the existing
convention seen in already-generated notes). Both paths still go through
the existing `dedupe_section()` / `append_section()` pipeline unchanged.

**`extension/manifest.json`**: description currently says *"No cloud, no
photos — text only."* This becomes false under the Gemini engine and gets
updated.

## Data flow (Gemini engine, one chunk)

1. Extension POSTs `/note-chunk` with `transcript_chunk`, `start_ts`,
   `end_ts`, `video_url`, etc. — unchanged from today.
2. `main.py` resolves/reuses the cached stream URL for this video.
3. `frame_extractor.extract_candidate_frames()` grabs ~1-4 candidate
   frames from just this chunk's time window.
4. `gemini_client.call_gemini()` sends transcript + candidate frames to
   Gemini, gets back markdown (some frames embedded, most not).
5. `main.py` saves only the frames actually referenced in the response
   into the note's `hover-notes-images/` folder.
6. Existing dedupe/append logic writes the section into the vault note,
   same as the Haiku path.

## Error handling

- No ffmpeg/yt-dlp available, or extraction throws for any reason: caught
  and logged, chunk proceeds with `frames=[]` (text-only Gemini call,
  degrades gracefully rather than failing the whole chunk).
- Gemini API error (rate limit, network, bad response): raises, surfaces
  as HTTP 502 from `/note-chunk` — same pattern the Haiku path already
  uses today. No automatic runtime fallback to Haiku; the engine choice is
  a static config toggle, not a dynamic failover.

## Testing

- `test_frame_extractor.py`: mocks `subprocess.run` for both the
  `yt-dlp -g` call and the ffmpeg sampling call; verifies dedup logic and
  URL caching behavior.
- `test_gemini_client.py`: mocks the `httpx` POST; verifies prompt
  construction, frame encoding, and response parsing — mirrors the
  existing `test_haiku_client.py` structure.
- `test_main.py`: adds coverage for the `NOTE_ENGINE=gemini` branch
  (mocking `call_gemini` and `frame_extractor`), verifying only
  Gemini-referenced frames get written to disk.

## Out of scope

- No extension/UI changes — engine selection is a server-side env var.
- No automatic fallback between engines on runtime failure.
- No changes to the Stat110 pipeline's own scripts — this vendors the
  frame-extraction algorithm, it doesn't import across repos.
