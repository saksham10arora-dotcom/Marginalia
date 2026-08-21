"""Single source of truth for the note-writing style contract.

Every engine sends the same instructions; only the transport differs (CLI
system-prompt flag, Gemini `parts`, OpenAI `messages`). This used to be the
same paragraph copy-pasted into haiku_client, gemini_client and finalize,
which meant a style change had to be made in three places in lockstep or the
engines would quietly disagree about the output format.

Wording here is load-bearing: it is the prompt. Changing a sentence changes
what the models write, so treat edits as behavior changes, not copy edits.
"""


def style_block(style_anchors: list[str]) -> str:
    """The shared opener: what to write, plus real notes to imitate."""
    anchors_block = "\n\n---\n\n".join(style_anchors)
    return f"""You write structured markdown lecture notes from a transcript chunk of a video.

Match this exact style — section headers as `## Title [HH:MM:SS](videoUrl&t=Ns)`, bold-term
bullets, no filler commentary, only the content actually present in the transcript:

{anchors_block}"""


def screenshot_rules(frame_timestamps: list[str], scope: str = "this chunk") -> str:
    """Vision-engine-only: how to judge candidate frames.

    The core rule is that a useful frame gets *rewritten into prose*, never
    embedded as an image and never described as "the slide shows..." -- the
    note should read as if the writer saw the board, with only an invisible
    HTML comment recording which frame it came from.
    """
    frames_block = (
        "\n".join(f"- {ts}" for ts in frame_timestamps)
        if frame_timestamps
        else "(no candidate screenshots)"
    )
    return f"""You have also been given {len(frame_timestamps)} candidate screenshot(s) taken during {scope},
in chronological order, attached after this text at these timestamps:

{frames_block}

For each screenshot, judge whether it shows something a person reading only the transcript would
miss — a formula, diagram, or worked example written on the board/slide but not fully spoken
aloud. If yes: write that content into your notes yourself, in your own words, as normal prose or
math at the relevant point — never a description of the image, never an embedded image. Mark the
exact spot with an inline HTML comment `<!-- screenshot: HH:MM:SS -->` using that screenshot's own
timestamp. If a screenshot is an empty board, has the speaker blocking the content, is
mid-transition, or just repeats what the transcript already says in words — ignore it completely:
no mention, no marker, nothing."""


def chunk_output_rules(with_screenshots: bool) -> str:
    """The closing constraint for per-chunk (live) generation."""
    source = "transcript or screenshots" if with_screenshots else "transcript"
    return (
        "Output ONLY the new section(s) in this format. Do not repeat the frontmatter or TL;DR — "
        f"those are handled separately. Do not invent content not present in the {source}."
    )


def video_context_block(video_title: str, video_url: str, start_ts: str, end_ts: str, transcript_chunk: str) -> str:
    """The actual payload: which video, which slice, what was said."""
    return (
        f'Video: "{video_title}"\n'
        f"Video URL: {video_url}\n"
        f"Transcript from {start_ts} to {end_ts}:\n\n{transcript_chunk}"
    )
