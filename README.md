# 📓 Marginalia

![Platform](https://img.shields.io/badge/platform-Chrome_Extension-4285F4?style=flat-square)
![Manifest](https://img.shields.io/badge/manifest-V3-4285F4?style=flat-square)
![Engines](https://img.shields.io/badge/engines-Haiku_%7C_Gemini_%7C_OpenRouter_%7C_Groq_%7C_local-8A2BE2?style=flat-square)
![Version](https://img.shields.io/badge/version-0.1.0-orange?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)
![Status](https://img.shields.io/badge/status-public-brightgreen?style=flat-square)

> **Live lecture notes from YouTube, written straight into your Obsidian vault while you watch.** Press Start, keep watching, and a real note builds itself in a side panel: timestamped sections, math rendered properly, board content folded into the text when it adds something the transcript alone would miss.

> _The margin, but of the video instead of the page._

```
███╗   ███╗ █████╗ ██████╗  ██████╗ ██╗███╗   ██╗ █████╗ ██╗     ██╗ █████╗ 
████╗ ████║██╔══██╗██╔══██╗██╔════╝ ██║████╗  ██║██╔══██╗██║     ██║██╔══██╗
██╔████╔██║███████║██████╔╝██║  ███╗██║██╔██╗ ██║███████║██║     ██║███████║
██║╚██╔╝██║██╔══██║██╔══██╗██║   ██║██║██║╚██╗██║██╔══██║██║     ██║██╔══██║
██║ ╚═╝ ██║██║  ██║██║  ██║╚██████╔╝██║██║ ╚████║██║  ██║███████╗██║██║  ██║
╚═╝     ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝╚══════╝╚═╝╚═╝  ╚═╝
```

---

## 📋 Table of Contents

1. [The Problem](#-the-problem)
2. [The Solution](#-the-solution)
3. [Features](#-features)
4. [Preview](#-preview)
5. [Architecture](#-architecture)
6. [Frame Selection Pipeline](#-frame-selection-pipeline)
7. [Installation](#-installation)
8. [How to Use](#-how-to-use)
9. [Setting Up the Gemini Engine](#-setting-up-the-gemini-engine-optional)
10. [Choosing an Engine](#-choosing-an-engine)
11. [Flashcards](#-flashcards)
12. [Vault Auto-Linking](#-vault-auto-linking)
13. [File Structure](#-file-structure)
14. [Testing](#-testing)
15. [Security Notes](#-security-notes)
16. [Roadmap](#-roadmap)
17. [FAQ](#-faq)
18. [Why I Built This](#-why-i-built-this)
19. [License](#-license)

---

## 😤 The Problem

You're watching a lecture. You either:

- Keep pausing every 30 seconds to write something down, and never actually finish the video, or
- Watch it straight through, take no notes, and have nothing to study from a week later.

HoverNotes (the real, paid extension) solves this well. But it's paid, and I wanted to actually understand how a "watch a video, get a live note" pipeline works instead of just paying for someone else's.

This is the problem Marginalia was built to solve.

---

## 💡 The Solution

```
YouTube video ──▶ transcript + (optional) video frames ──▶ note-writing model
                                                                    │
                                                                    ▼
                                              a real, growing note in a side panel
                                                                    │
                                              you hit Stop  ────────┘
                                                                    │
                                                                    ▼
                              full-video re-generation (TL;DR, thematic sections, glossary)
                                                                    │
                                                                    ▼
                                                        written into your Obsidian vault
```

**Marginalia** is a Chrome extension that:

1. **Injects a panel** into any YouTube video page, no click required
2. **Batches the transcript** into ~60-second chunks as the video plays and POSTs each to a local FastAPI sidecar
3. **Writes a real note section** for every chunk and appends it straight into your Obsidian vault
4. **Regenerates the whole note** the moment you hit Stop, using the full transcript (and optionally the video's frames) for real coherence instead of a script's worth of headers
5. **Optionally watches the frames too** (Gemini engine) and folds board or slide content into the note when the transcript alone would miss it

No cloud servers beyond whichever model API you've configured (Anthropic via your own `claude` CLI login, or Google's Gemini). No sign-up, no accounts of its own. Everything runs on `localhost`.

---

## ✨ Features

### 📝 Note Generation

| Feature | Status |
|---|---|
| Live, incremental notes (~every 60s of video) | ✅ Live |
| Timestamped section links (`[HH:MM:SS](videoUrl&t=Ns)`) | ✅ Live |
| Full-context regeneration on Stop (TL;DR + thematic sections + glossary) | ✅ Live |
| Duplicate-section detection (won't repeat a section it already wrote) | ✅ Live |
| Math rendering (KaTeX, `$...$` / `$$...$$`) | ✅ Live |

### 🧠 Engines

| Feature | Status |
|---|---|
| `haiku` engine, transcript only, your existing Claude Pro/Max login | ✅ Default |
| `gemini` engine, transcript + candidate video frames | ✅ Optional |
| Any OpenAI-compatible provider (OpenRouter, Groq, Fireworks, Cerebras, Together, OpenAI) | ✅ Live |
| Fully local, zero-cost engines (Ollama, LM Studio) | ✅ Live |
| Vision auto-detection: frames are only captured for engines that can see | ✅ Live |
| Per-frame usefulness judgment (paraphrase into prose, or silently discard) | ✅ Live |
| Invisible `<!-- screenshot: HH:MM:SS -->` provenance marker, never a pasted image | ✅ Live |
| Multi-key rotation across Gemini's 20-calls/day/key free tier | ✅ Live |

### 🗂️ In-Panel File Browser

| Feature | Status |
|---|---|
| Search past notes by title | ✅ Live |
| Open a note inline (screenshots + math render correctly) | ✅ Live |
| Jump back to the live session without losing it | ✅ Live |
| Toolbar icon toggles the panel on/off, any time | ✅ Live |

### 🛠️ Action Bar

| Feature | Status |
|---|---|
| 🌐 Open the source video | ✅ Live |
| 📋 Copy the note as markdown | ✅ Live |
| ⬇️ Download the note as `.md` | ✅ Live |
| 🕐 Browse all notes | ✅ Live |
| 🎴 Export Anki flashcards from the note | ✅ Live |
| 🔗 Open the note directly in Obsidian (`obsidian://open`) | ✅ Live |

### 🧠 Study Tools

| Feature | Status |
|---|---|
| One-click Anki flashcard export (Q/A cards, LaTeX preserved) | ✅ Live |
| Auto-wikilinking into your existing Obsidian graph | ✅ Live |
| Obsidian `aliases:` support, so prose mentions link to the right note | ✅ Live |

---

## 🖼️ Preview

### The panel, live, mid-lecture

![Marginalia panel open on a Statistics 110 lecture, generating notes with rendered math](assets/preview.png)

> A real session: Harvard's Stat 110 (Probability), notes generating live in the side panel as the lecture plays, section headers, KaTeX-rendered math, a worked example, all written straight into the vault note in the background.

### Opening a past note from the in-panel file browser

![Demo: opening the file browser and viewing a previously-generated note with rendered math](assets/demo.gif)

> A real, previously-generated note for this exact video (3Blue1Brown's *Essence of Linear Algebra*, Chapter 1), opened from the panel's file browser: TL;DR, timestamped sections, and inline math rendering.

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                       Chrome Extension (MV3)                             │
│                                                                            │
│  ┌────────────────────┐   ┌──────────────────┐   ┌────────────────────┐ │
│  │  content-script.js  │──▶│     panel.js      │──▶│    renderer.js     │ │
│  │  injects the panel, │   │  batching, state,  │   │  markdown → HTML,  │ │
│  │  reserves page space│   │  action bar wiring │   │  XSS sanitization  │ │
│  └──────────┬───────────┘  └─────────┬─────────┘   └─────────────────────┘ │
│             │                        │                                    │
│  ┌──────────▼───────────┐  ┌─────────▼─────────┐                          │
│  │    background.js      │  │   transcript.js    │                        │
│  │  toolbar-icon toggle   │  │  batching helpers  │                        │
│  └───────────────────────┘  └────────────────────┘                        │
└───────────────────────────────────┬──────────────────────────────────────┘
                                     │ HTTP, localhost:8765
                                     ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                    FastAPI Sidecar (sidecar/)                            │
│                                                                            │
│   main.py ── routes: /note-chunk, /finalize-note, /documents, /transcript │
│      │                                                                    │
│      ├─▶ haiku_client.py ──── claude CLI, transcript-only                │
│      ├─▶ gemini_client.py ─── Gemini API, transcript + frames            │
│      │        │                                                          │
│      │        ├─▶ frame_extractor.py ── yt-dlp download + phash sampling │
│      │        └─▶ key_rotation.py ───── round-robins multiple API keys   │
│      ├─▶ finalize.py ──────── whole-video regeneration on Stop           │
│      ├─▶ transcript_fetcher.py ── youtube_transcript_api                 │
│      └─▶ vault_writer.py ──── frontmatter, file I/O, dedupe              │
└───────────────────────────────────┬──────────────────────────────────────┘
                                     ▼
                          your Obsidian vault (.md + images)
```

### How it works under the hood

`content-script.js` injects the panel on every YouTube watch page, reserves layout space so the video actually shrinks instead of being covered, and polls the sidecar's `/health` every 15s for the live status dot.

`panel.js` batches the transcript into ~60s chunks as the video plays, POSTs each to `/note-chunk`, and renders the response. On Stop, it calls `/finalize-note`.

`main.py` routes to either `haiku_client.py` or `gemini_client.py` depending on `NOTE_ENGINE`. The Gemini path also calls `frame_extractor.py` for that chunk's time window, best-effort: a frame-capture failure degrades to text-only, never blocks the note.

`finalize.py` discards the rough live draft, refetches the full transcript, re-extracts frames across the whole video, and makes one Gemini call for the complete note.

`vault_writer.py` handles frontmatter, filename collisions, and `dedupe_section()` so a retried chunk never gets written twice.

---

## ⚙️ Frame Selection Pipeline

> **Status:** shipped, hardened against a real YouTube CDN reliability problem hit mid-project.

```
Chunk time window (e.g. 00:01:00-00:02:00)
        │
        ▼
1. DOWNLOAD
   yt-dlp downloads just that clip directly (its own downloader handles YouTube's
   bot detection correctly, since it's what resolved the URL) -- 3 retries, since
   the exact same request has been observed succeeding and failing seconds apart

        │
        ▼
2. INTERVAL SAMPLING
   ffmpeg samples one candidate frame every 3 seconds from the local clip
   (no more network calls involved from here on)

        │
        ▼
3. PERCEPTUAL HASH DEDUP
   imagehash.phash() on each candidate; a frame is kept only if its hash differs
   from the last kept frame by more than a Hamming-distance threshold -- a static
   slide held for 10s, or minor camera jitter, collapses down to one frame

        │
        ▼
4. GEMINI JUDGES EACH SURVIVING FRAME
   shows a formula/diagram not in the transcript?  -> paraphrase into prose,
                                                       mark with <!-- screenshot: HH:MM:SS -->
   empty, redundant, mid-transition?                -> discard, no trace in the note
```

Why download the clip instead of handing `ffmpeg` a raw stream URL directly? Confirmed live, by direct experimentation: YouTube's edge servers reject some signed URLs unpredictably, even with matching request headers, even when the *exact same URL* `yt-dlp` itself just resolved gets handed straight back to it seconds later. `yt-dlp`'s own downloader replicates whatever YouTube actually requires (proven, since it's what got the URL in the first place); `ffmpeg` fetching that URL independently does not.

---

## 🚀 Installation

Since this is a personal, unpublished project, it runs from source in **Developer Mode**.

**Prerequisites:** Python 3.10+, Node.js, [`yt-dlp`](https://github.com/yt-dlp/yt-dlp) and `ffmpeg` on your `PATH` (only needed for the optional Gemini engine's frame capture; skip those two if you're sticking with the default Haiku engine).

**Platform:** macOS, Linux and Windows. The sidecar's full test suite runs on all three in CI against Python 3.10 and 3.13. Commands below are shown for macOS/Linux with a Windows variant where they differ. The one genuinely unverified path on Windows is frame capture, since the yt-dlp/ffmpeg subprocess calls are mocked in tests and have only been exercised by hand on macOS.

**No Claude Pro/Max?** The default engine below needs an existing `claude` CLI login. If you don't have one, skip straight to [Setting Up the Gemini Engine](#-setting-up-the-gemini-engine-optional) instead: free API key, no CLI required.

### Step 1: Confirm the Haiku engine works

Default engine, no extra setup. Needs the `claude` CLI already installed and logged into a Claude Pro/Max account.

```bash
claude -p --model haiku "say hi"
```

### Step 2: Set up the sidecar

```bash
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r sidecar/requirements.txt
npm install
```

### Step 3: Point it at your own vault (optional)

Defaults to `~/MarginaliaNotes`, created automatically on first run. To point it at an existing [Obsidian](https://obsidian.md) vault instead:

```bash
export MARGINALIA_VAULT_PATH=/path/to/your/vault
```

On Windows (PowerShell):

```powershell
$env:MARGINALIA_VAULT_PATH = "C:\path\to\your\vault"
```

### Step 4: Start the sidecar

```bash
source venv/bin/activate && uvicorn sidecar.main:app --port 8765
```

On Windows (PowerShell):

```powershell
venv\Scripts\activate; uvicorn sidecar.main:app --port 8765
```

### Step 5: Load the extension

Go to `chrome://extensions`, enable **Developer Mode**, click **Load unpacked**, and select the `extension/` folder.

---

## 🛠️ How to Use

### Basic usage (Haiku engine, no API key required)

#### 1. Open any YouTube video with captions

The extension activates automatically on `/watch` pages; no click required.

#### 2. Hit Start AI Notes

Click the toolbar icon if the panel isn't already visible, then **Start AI Notes** in the panel's toolbar. Keep watching; a new section appears roughly every 60 seconds.

#### 3. Hit Stop AI Notes when you're done

The note gets rewritten with a TL;DR, thematic sections, and a glossary, using the full video's context instead of the rough live draft.

#### 4. Use the action bar

Open the source video, copy or download the note, browse past notes, or open the current one directly in Obsidian.

---

## 🔑 Setting Up the Gemini Engine (optional)

> Vision, not compression, is the point here. The transcript alone misses anything written on a board or slide but never said out loud; the Gemini engine catches that, via the pipeline described [above](#-frame-selection-pipeline).

### Step 1: Get a free Gemini API key

Go to [Google AI Studio](https://aistudio.google.com/), sign in, and create a key.

### Step 2: Add it to `~/.config/keys.env`

Copy [`keys.env.example`](keys.env.example) to `~/.config/keys.env` and fill in your key:

```bash
GEMINI_API_KEY=AIzaSy...yourkey...
GEMINI_API_KEY_2=AIzaSy...secondkey...   # optional, extra Google account
GEMINI_API_KEY_3=AIzaSy...thirdkey...    # optional
```

### Step 3: Start the sidecar with the engine flag

```bash
MARGINALIA_ENGINE=gemini uvicorn sidecar.main:app --port 8765
```

### Why multiple keys?

Gemini's free tier caps at 20 `generateContent` calls/day *per key* for `gemini-3.5-flash`. Live note-taking fires roughly one call per 60s chunk, so a single normal-length lecture can burn a whole day's quota on its own. `key_rotation.py` round-robins across however many keys you configure, falling through immediately on a 429 instead of backing off a quota that won't reset for hours anyway.

> **Privacy:** with the Gemini engine active, that chunk's transcript text and candidate frames are sent to Google's API. The `haiku` engine sends transcript text to Anthropic via your existing `claude` CLI login. Neither engine sends anything anywhere else; the sidecar itself has no telemetry and talks to nothing but `localhost` and whichever engine you picked.

---

## 🔌 Choosing an Engine

`MARGINALIA_ENGINE` picks who writes the notes. Everything past the first two
speaks OpenAI's `/chat/completions`, so adding a provider is a registry entry
in `sidecar/providers.py`, not a new client module.

| Engine | Cost | Vision | Key needed |
|---|---|---|---|
| `haiku` *(default)* | Your existing Claude Pro/Max plan | No | None, uses the `claude` CLI |
| `gemini` | Free tier, 20 calls/day/key | **Yes** | `GEMINI_API_KEY` |
| `openrouter` | Pay per token | **Yes** | `OPENROUTER_API_KEY` |
| `groq` | Free tier, very fast | No | `GROQ_API_KEY` |
| `fireworks` | Pay per token | No | `FIREWORKS_API_KEY` |
| `cerebras` | Free tier | No | `CEREBRAS_API_KEY` |
| `together` | Pay per token | No | `TOGETHER_API_KEY` |
| `openai` | Pay per token | **Yes** | `OPENAI_API_KEY` |
| `ollama` | **Free, fully local** | No | None |
| `lmstudio` | **Free, fully local** | No | None |

```bash
# Fastest free cloud option
MARGINALIA_ENGINE=groq uvicorn sidecar.main:app --port 8765

# Fully local, nothing leaves your machine
MARGINALIA_ENGINE=ollama MARGINALIA_MODEL=llama3.2 uvicorn sidecar.main:app --port 8765

# Any specific model on a provider
MARGINALIA_ENGINE=openrouter MARGINALIA_MODEL=openai/gpt-4o-mini uvicorn sidecar.main:app --port 8765
```

Frame capture is skipped automatically on text-only engines. It costs real
seconds per chunk, so there is no point paying it to build images a text-only
model will never look at.

Every provider gets multi-key rotation for free: add `GROQ_API_KEY_2`,
`GROQ_API_KEY_3` and so on, and `key_rotation.py` round-robins across them.

---

## 🎴 Flashcards

Notes you never reopen are worth roughly nothing. The 🎴 button in the action
bar turns the current note into Anki cards in one click.

```bash
curl -X POST http://localhost:8765/export/flashcards \
  -H "Content-Type: application/json" \
  -d '{"filename":"stat110/lec1.md","tags":"stat110"}'
```

The panel downloads a `.txt` you drag straight into Anki: no plugin, no
`.apkg` tooling, no import-dialog settings to get right. Real output from the
3Blue1Brown vectors note:

```
Q: How does the tip-to-tail method construct the sum of two vectors geometrically?
A: Place the second vector's tail at the tip of the first; draw the sum from
   the first vector's tail to the second vector's tip.

Q: How is vector addition performed on two coordinate lists?
A: Add corresponding components: $\begin{bmatrix} a \\ b \end{bmatrix} +
   \begin{bmatrix} c \\ d \end{bmatrix} = \begin{bmatrix} a+c \\ b+d \end{bmatrix}$
```

LaTeX survives intact, so formula cards render properly in Anki instead of
arriving as flattened text. Works on every engine, including the default one
that needs no API key.

---

## 🕸️ Vault Auto-Linking

A note that says "eigenvalues" is dead text. `[[Eigenvalues]]` is a real edge
in your Obsidian graph, and it shows up in that note's backlinks without you
doing anything. Marginalia adds those edges as it writes.

It refuses to link things that only look like prose: LaTeX, code blocks,
existing links, headings, and the invisible screenshot markers all come
through untouched.

**To make this actually fire, add `aliases:` to your notes.** This is not
optional polish, it is the whole mechanism. Real lecture notes are titled
things like `"Lecture 4: Linear Algebra (cont.); Probability Theory"`, and
nobody writes that phrase in prose, so matching on titles alone almost never
fires. Obsidian's own `aliases:` field is the fix:

```yaml
---
title: "Lecture 4: Linear Algebra (cont.); Probability Theory"
aliases:
  - linear algebra
  - probability theory
---
```

Now any future note that mentions "linear algebra" links straight to it:

```markdown
Today we connect this to [[Lecture 4: Linear Algebra (cont.); Probability Theory|linear algebra]].
```

One edge per destination note, first mention only, capped at 8 per section, so
notes stay readable instead of turning solid blue. Disable entirely with
`MARGINALIA_AUTOLINK=0`.

---

## 📁 File Structure

```
marginalia/
├── extension/
│   ├── manifest.json          ← MV3 config, host permissions
│   ├── background.js          ← toolbar-icon click → toggle panel
│   ├── content-script.js      ← injects the panel, page-layout reflow
│   ├── panel.js                ← batching, state, action bar, file browser
│   ├── renderer.js            ← markdown → HTML, XSS sanitization
│   ├── transcript.js          ← chunk-batching helpers
│   ├── panel.css              ← panel UI, typography, action bar
│   └── *.test.js              ← vitest unit tests
├── sidecar/
│   ├── main.py                 ← FastAPI routes
│   ├── config.py               ← engine toggle, key loading
│   ├── providers.py           ← OpenAI-compatible provider registry
│   ├── engine_dispatch.py     ← picks the engine, routes the call
│   ├── openai_compatible.py   ← one client for every /chat/completions API
│   ├── prompts.py             ← shared note-writing style contract
│   ├── vault_linker.py        ← auto-wikilinking into the Obsidian graph
│   ├── anki_export.py         ← note → Anki flashcards (TSV)
│   ├── haiku_client.py        ← claude CLI, transcript-only
│   ├── gemini_client.py       ← Gemini API, transcript + frames
│   ├── frame_extractor.py     ← yt-dlp download + perceptual-hash sampling
│   ├── key_rotation.py        ← multi-key round-robin
│   ├── finalize.py             ← whole-video regeneration on Stop
│   ├── transcript_fetcher.py  ← youtube_transcript_api
│   ├── vault_writer.py        ← frontmatter, file I/O, dedupe
│   └── tests/                  ← pytest suite
├── scripts/
│   └── package-extension.sh   ← builds the Chrome Web Store zip
├── .github/workflows/ci.yml   ← both suites, 3 OSes, Python 3.10 + 3.13
├── ISSUES.md                   ← known issues and future scope
└── README.md
```

### Key constants

| File | Constant | Default | Description |
|---|---|---|---|
| `sidecar/config.py` | `NOTE_ENGINE` | `"haiku"` | `MARGINALIA_ENGINE` env var overrides |
| `sidecar/config.py` | `AUTOLINK` | `True` | `MARGINALIA_AUTOLINK=0` writes plain prose |
| `sidecar/config.py` | `MAX_AUTOLINKS_PER_SECTION` | `8` | Wikilink cap per generated section |
| `sidecar/config.py` | `VAULT_PATH` | `~/MarginaliaNotes` | `MARGINALIA_VAULT_PATH` env var overrides |
| `sidecar/providers.py` | `PROVIDERS` | 8 providers | `MARGINALIA_MODEL` overrides any default model |
| `sidecar/anki_export.py` | `MAX_CARDS` | `25` | Cap on flashcards per note |
| `sidecar/vault_linker.py` | `MIN_TITLE_LENGTH` | `4` | Below this, titles are too generic to link |
| `sidecar/frame_extractor.py` | `interval` | `3.0` sec | How often a candidate frame is sampled |
| `sidecar/frame_extractor.py` | `hash_threshold` | `5` | Hamming distance a frame must clear vs. the last kept one |
| `sidecar/frame_extractor.py` | `DOWNLOAD_ATTEMPTS` | `3` | Retries on YouTube CDN 403 |
| `sidecar/gemini_client.py` | `MAX_ATTEMPTS` | `3` | Retries on Gemini 429/503 |
| `extension/panel.js` | `BATCH_DURATION_SEC` | `60` | Live chunk size, in video-seconds |

---

## 🧪 Testing

```bash
# Sidecar (177 tests)
source venv/bin/activate && python -m pytest sidecar/tests/ -v   # Windows: venv\Scripts\activate

# Extension pure-logic units (36 tests)
npm test

# Build the Chrome Web Store zip
bash scripts/package-extension.sh
```

213 tests total, all mocked: no network, no API keys, no `claude` CLI needed. CI runs both suites on Ubuntu, macOS and Windows against Python 3.10 and 3.13.

Everything DOM-level (panel rendering, in-browser interactions) is manually verified in a live browser, not covered by the automated suites above.

---

## 🔒 Security Notes

Notes are rendered as live HTML (not plain text) to support markdown formatting and math rendering. Note content and metadata originate from public YouTube video transcripts and titles, which are not fully trusted input: an attacker could craft a maliciously-worded video title or transcript to target the extension. The renderer sanitizes unsafe URL schemes (`javascript:`, `data:`) in links and images, and HTML-escapes video titles and domains before inserting them into the DOM. The one deliberate, narrow exception is the Gemini engine's `<!-- screenshot: HH:MM:SS -->` provenance marker, matched by a strict digits-only pattern that can't smuggle a script tag and rendered as fully invisible, matching how Obsidian treats real HTML comments. If you encounter unexpected script execution in the panel, report it as a security issue.

---

## 🗺️ Roadmap

Full backlog lives in [`ISSUES.md`](ISSUES.md).

### v0.2.0: Portability
- [x] Configurable `VAULT_PATH` (env var, sane default) instead of hardcoded
- [x] Provider-agnostic engines (OpenRouter, Groq, Fireworks, Cerebras, Together, OpenAI, Ollama, LM Studio)
- [ ] Standard `.env` for the Gemini keys instead of the bespoke `~/.config/keys.env` parser (a documented [`keys.env.example`](keys.env.example) exists in the meantime)

### v0.3.0: Infrastructure
- [x] Basic CI (GitHub Actions) running both test suites on every push
- [x] Chrome Web Store packaging script (`scripts/package-extension.sh`)
- [ ] Actually submit to the Chrome Web Store

### v1.0.0: Public
- [ ] Everything above cleared
- [x] Real screenshots and a short demo GIF in this README

---

## ❓ FAQ

**Q: The panel shows "Sidecar offline."**
A: The sidecar isn't running, or crashed. Start it with the command in [Installation](#-installation), step 4. The status dot polls `/health` every 15s and updates automatically once it's back.

**Q: Live notes look choppy / sections end mid-thought.**
A: Expected. Each 60s chunk only sees its own transcript slice, which is why Stop's full-context regeneration exists. Live is a rough draft; the real output happens on Stop.

**Q: Gemini engine gives a 502 error.**
A: Either no `GEMINI_API_KEY` is configured, or you've exhausted the daily quota on all configured keys. Add a key, or wait for the daily reset (~24h from first use).

**Q: Frame capture isn't finding anything / no screenshots in the note.**
A: Either the video has nothing worth capturing (Gemini judged every frame redundant or empty, which is correct behavior, not a bug), or YouTube's CDN rejected the download. Check the sidecar logs for `"Frame extraction failed"`; if it's a 403, that's the known CDN flakiness described in the [Frame Selection Pipeline](#-frame-selection-pipeline), already retried 3 times before falling back to text-only.

**Q: Can I use this on Udemy / Coursera / a local video file?**
A: Not yet. YouTube only for now. A later, separate project.

---

## 💭 Why I Built This

It went through a few real iterations, not a one-shot build:

- Started transcript-only (Claude Haiku via the local `claude` CLI, no API key, no vision).
- Tried scraping YouTube's own transcript panel DOM: brittle, broke whenever YouTube changed a class name. Switched to `youtube_transcript_api` server-side instead.
- Added the Gemini engine because some of what's worth noting is written on the board and never said out loud. Ran a real side-by-side experiment (live chunk-by-chunk vs. whole-video batch) to check whether frame capture actually helped, or just added noise. It helped, on the same chunk-blindness axis that turned out to matter more than which model was writing.
- Rebuilt the finalize step around that finding: instead of tuning live per-chunk notes forever, the whole note gets regenerated with full-video context the moment you hit Stop.

---

## 📄 License

MIT License, see [LICENSE](LICENSE) for details.

---

<div align="center">

Built with ❤️ by Saksham Arora

</div>
