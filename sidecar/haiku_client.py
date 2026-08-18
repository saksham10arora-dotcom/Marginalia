import json
import subprocess
import tempfile
from pathlib import Path

CLAUDE_MODEL = "haiku"
CLI_TIMEOUT_SEC = 60  # observed real calls take ~10-15s; generous margin for slower ones


def load_style_anchors(vault_path: Path, count: int = 2) -> list[str]:
    md_files = sorted(vault_path.rglob("*.md"))[:count]
    return [f.read_text() for f in md_files]


def build_system_prompt(style_anchors: list[str]) -> str:
    anchors_block = "\n\n---\n\n".join(style_anchors)
    return f"""You write structured markdown lecture notes from a transcript chunk of a video.

Match this exact style — section headers as `## Title [HH:MM:SS](videoUrl&t=Ns)`, bold-term
bullets, no filler commentary, only the content actually present in the transcript:

{anchors_block}

Output ONLY the new section(s) in this format. Do not repeat the frontmatter or TL;DR —
those are handled separately. Do not invent content not present in the transcript."""


def call_haiku(
    transcript_chunk: str,
    video_title: str,
    video_url: str,
    start_ts: str,
    end_ts: str,
    style_anchors: list[str],
) -> str:
    """Shells out to the Claude Code CLI in headless mode (`claude -p`), which
    authenticates via this machine's existing Claude Pro/Max login. No API key,
    no `anthropic` package. Each call is a fresh, non-persisted session."""
    system_prompt = build_system_prompt(style_anchors)
    user_message = (
        f'Video: "{video_title}"\n'
        f"Video URL: {video_url}\n"
        f"Transcript from {start_ts} to {end_ts}:\n\n{transcript_chunk}"
    )
    result = subprocess.run(
        [
            "claude", "-p",
            "--model", CLAUDE_MODEL,
            "--output-format", "json",
            "--no-session-persistence",
            "--system-prompt", system_prompt,
            "--allowedTools", "",
            # "--allowedTools" is variadic (accepts multiple space-separated
            # tool names), so without a separator the CLI's arg parser
            # greedily swallows the positional user_message as another
            # allowed-tool value, leaving no prompt at all. "--" explicitly
            # ends option parsing before the positional prompt argument.
            "--",
            user_message,
        ],
        capture_output=True,
        text=True,
        timeout=CLI_TIMEOUT_SEC,
        cwd=tempfile.gettempdir(),
    )
    if result.returncode != 0:
        raise RuntimeError(f"claude CLI exited {result.returncode}: {result.stderr}")

    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"claude CLI returned non-JSON output: {result.stdout[:200]!r}"
        ) from e
    if payload.get("is_error"):
        raise RuntimeError(f"claude CLI reported an error: {payload}")

    return payload["result"]
