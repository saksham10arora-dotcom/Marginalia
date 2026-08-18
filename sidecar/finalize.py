import re

from sidecar.gemini_client import frames_to_parts, post_to_gemini

# Fires once, when the user hits stop, replacing the whole note body. Unlike
# the live per-chunk pipeline (gemini_client.call_gemini), this re-fetches
# the FULL transcript and re-extracts frames across the ENTIRE video, then
# asks for one complete set of notes in a single call -- the same
# whole-video-context approach proven (against a chunk-blind live run, on the
# same video) to produce thematically organized, stat110-quality notes,
# rather than a live note's arbitrary 60-second-chunk boundaries.

VIDEO_ID_RE = re.compile(r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{11})")


def extract_video_id(video_url: str) -> str:
    match = VIDEO_ID_RE.search(video_url)
    if not match:
        raise ValueError(f"Could not extract video ID from URL: {video_url}")
    return match.group(1)


def build_regenerate_prompt(
    transcript_text: str,
    video_title: str,
    video_url: str,
    frame_timestamps: list[str],
    style_anchors: list[str],
) -> str:
    anchors_block = "\n\n---\n\n".join(style_anchors)
    frames_block = (
        "\n".join(f"- {ts}" for ts in frame_timestamps)
        if frame_timestamps
        else "(no candidate screenshots)"
    )
    return f"""You write complete, structured markdown lecture notes from a video transcript.
Match this exact style (frontmatter/H1 excluded -- write only from the TL;DR callout down):

{anchors_block}

You have the FULL transcript of the video below, plus {len(frame_timestamps)} candidate
screenshot(s) spanning its duration, attached in chronological order at these timestamps:

{frames_block}

For each screenshot, judge whether it shows something the transcript alone would miss --
a diagram, formula, or worked example on screen but not fully spoken aloud. If yes, write
that content into your notes yourself, in your own words, as normal prose or math at the
relevant point -- never a description of the image, never an embedded image. Mark the exact
spot with an inline HTML comment `<!-- screenshot: HH:MM:SS -->` using that screenshot's own
timestamp. Ignore screenshots that are empty, mid-transition, or redundant with the transcript.

Produce, in this order:
1. A `> [!abstract] TL;DR` callout (2-4 sentences, prose, one line).
2. `## Section Title [HH:MM:SS](videoUrl&t=Ns)` sections covering the whole video, bold-term
   bullets, grouping content by topic rather than mirroring transcript chunk boundaries.
3. A closing `> [!note] Key terms` callout glossary.

Video: "{video_title}"
Video URL: {video_url}
Full transcript:

{transcript_text}"""


def call_regenerate(
    prompt: str,
    frames: list[tuple[float, bytes]],
    api_key: str,
) -> str:
    parts = [{"text": prompt}] + frames_to_parts(frames)
    return post_to_gemini(parts, api_key)
