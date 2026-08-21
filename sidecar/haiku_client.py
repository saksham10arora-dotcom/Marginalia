import json
import subprocess
import tempfile
from pathlib import Path

from sidecar.prompts import chunk_output_rules, style_block, video_context_block

CLAUDE_MODEL = "haiku"
CLI_TIMEOUT_SEC = 60  # observed real calls take ~10-15s; generous margin for slower ones


def load_style_anchors(vault_path: Path, count: int = 2) -> list[str]:
    md_files = sorted(vault_path.rglob("*.md"))[:count]
    return [f.read_text() for f in md_files]


def build_system_prompt(style_anchors: list[str]) -> str:
    """Transcript-only: this engine never sees frames, so no screenshot rules."""
    return f"{style_block(style_anchors)}\n\n{chunk_output_rules(with_screenshots=False)}"


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
    user_message = video_context_block(video_title, video_url, start_ts, end_ts, transcript_chunk)
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


def complete_with_haiku(prompt: str, system_prompt: str = "") -> str:
    """Generic single-prompt completion via the same CLI path as call_haiku.

    Used by anything that is not per-chunk note generation (flashcards, etc.)
    so those features work on the default engine with no API key either.
    """
    args = ["claude", "-p", "--model", CLAUDE_MODEL, "--output-format", "json",
            "--no-session-persistence"]
    if system_prompt:
        args += ["--system-prompt", system_prompt]
    args += ["--allowedTools", "", "--", prompt]

    result = subprocess.run(
        args, capture_output=True, text=True,
        timeout=CLI_TIMEOUT_SEC, cwd=tempfile.gettempdir(),
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
