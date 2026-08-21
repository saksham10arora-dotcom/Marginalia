"""One place that knows which engine is configured and how to call it.

Before this, main.py branched on `NOTE_ENGINE == "gemini"` inline, which meant
every new provider needed another branch in the request handler. Now the
handler asks for a section and this module figures out the rest: which client,
which keys, whether to bother extracting frames at all.

Two entry points:
  generate_section() -- the note-writing path, vision-aware
  complete()         -- a single prompt in, text out, for flashcards and
                        anything else that is not per-chunk note generation
"""
import logging

from sidecar import config
from sidecar.config import ENGINE_LABELS, load_api_keys, load_gemini_api_keys
from sidecar.gemini_client import GEMINI_MODEL, call_gemini, post_to_gemini
from sidecar.haiku_client import call_haiku, complete_with_haiku
from sidecar.key_rotation import call_with_key_rotation
from sidecar.openai_compatible import (
    call_openai_compatible,
    post_chat_completion,
    resolve_model,
)
from sidecar.providers import get_provider, is_openai_compatible

logger = logging.getLogger(__name__)


def current_engine() -> str:
    """Read through to the config module rather than caching a copy, so the
    engine is whatever is configured *now*."""
    return config.NOTE_ENGINE


def engine_supports_vision(engine: str | None = None) -> bool:
    """Whether it is worth paying the yt-dlp/ffmpeg cost for this engine.

    Frame extraction takes real seconds per chunk. Doing it for a text-only
    engine burns that time to build images nothing will ever look at.
    """
    engine = engine or current_engine()
    if engine == "gemini":
        return True
    if engine == "haiku":
        return False
    return is_openai_compatible(engine) and get_provider(engine).supports_vision


def engine_label(engine: str | None = None) -> str:
    """What lands in the note's `engine:` frontmatter field, so a note always
    records which model actually wrote it."""
    engine = engine or current_engine()
    if engine in ENGINE_LABELS:
        return ENGINE_LABELS[engine]
    if is_openai_compatible(engine):
        return f"{engine}/{resolve_model(engine)}"
    return engine


def _keys_for(engine: str) -> list[str]:
    if engine == "gemini":
        return load_gemini_api_keys()
    if not is_openai_compatible(engine):
        return []
    provider = get_provider(engine)
    if not provider.key_names:
        return [""]  # local server, no auth
    for name in provider.key_names:
        keys = load_api_keys(name)
        if keys:
            return keys
    raise RuntimeError(
        f"No API key for engine {engine!r}. Add {provider.key_names[0]} to ~/.config/keys.env "
        f"(see keys.env.example)."
    )


def generate_section(
    transcript_chunk: str,
    video_title: str,
    video_url: str,
    start_ts: str,
    end_ts: str,
    style_anchors: list[str],
    frames: list[tuple[float, bytes]],
    engine: str | None = None,
) -> str:
    engine = engine or current_engine()
    if engine == "haiku":
        return call_haiku(
            transcript_chunk=transcript_chunk,
            video_title=video_title,
            video_url=video_url,
            start_ts=start_ts,
            end_ts=end_ts,
            style_anchors=style_anchors,
        )

    keys = _keys_for(engine)

    if engine == "gemini":
        if not keys:
            raise RuntimeError("No GEMINI_API_KEY found in ~/.config/keys.env")
        return call_with_key_rotation(
            call_gemini,
            keys,
            transcript_chunk=transcript_chunk,
            video_title=video_title,
            video_url=video_url,
            start_ts=start_ts,
            end_ts=end_ts,
            style_anchors=style_anchors,
            frames=frames,
        )

    if is_openai_compatible(engine):
        return call_with_key_rotation(
            call_openai_compatible,
            keys,
            transcript_chunk=transcript_chunk,
            video_title=video_title,
            video_url=video_url,
            start_ts=start_ts,
            end_ts=end_ts,
            style_anchors=style_anchors,
            frames=frames,
            engine=engine,
        )

    raise ValueError(f"Unknown engine: {engine!r}")


def complete(prompt: str, engine: str | None = None) -> str:
    """Generic single-prompt completion, engine-agnostic."""
    engine = engine or current_engine()
    if engine == "haiku":
        return complete_with_haiku(prompt)

    keys = _keys_for(engine)

    if engine == "gemini":
        if not keys:
            raise RuntimeError("No GEMINI_API_KEY found in ~/.config/keys.env")
        return call_with_key_rotation(post_to_gemini, keys, [{"text": prompt}])

    if is_openai_compatible(engine):
        messages = [{"role": "user", "content": prompt}]
        return call_with_key_rotation(post_chat_completion, keys, messages, engine)

    raise ValueError(f"Unknown engine: {engine!r}")
