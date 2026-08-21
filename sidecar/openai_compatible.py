"""One client for every provider that speaks OpenAI's /chat/completions.

That is almost all of them: OpenRouter, Groq, Fireworks, Cerebras, Together,
OpenAI itself, and local servers like Ollama and LM Studio. They differ only
in base URL, model name, and auth -- all of which live in providers.py -- so
adding one is a registry entry, not another client module.

Deliberately mirrors gemini_client's call signature (api_key last, keyword-
passable) so key_rotation.call_with_key_rotation works with it unchanged.
"""
import base64
import os
import time

import httpx

from sidecar.frame_extractor import seconds_to_timestamp
from sidecar.providers import get_provider
from sidecar.prompts import (
    chunk_output_rules,
    screenshot_rules,
    style_block,
    video_context_block,
)

TIMEOUT_SEC = 90  # local models (ollama/lmstudio) on CPU are genuinely slow
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
MAX_ATTEMPTS = 3
RETRY_BACKOFF_SEC = 3


def frames_to_content_parts(frames: list[tuple[float, bytes]]) -> list[dict]:
    """OpenAI's multimodal shape: base64 data URLs inline in the content array."""
    return [
        {
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{base64.b64encode(jpeg_bytes).decode()}"
            },
        }
        for _ts, jpeg_bytes in frames
    ]


def build_messages(
    transcript_chunk: str,
    video_title: str,
    video_url: str,
    start_ts: str,
    end_ts: str,
    style_anchors: list[str],
    frames: list[tuple[float, bytes]],
    supports_vision: bool,
) -> list[dict]:
    """System prompt carries the style contract, user message carries the
    payload -- the split OpenAI-compatible APIs expect, and the same one the
    Claude CLI path uses via --system-prompt.

    Frames are dropped entirely for text-only providers rather than attached
    and hoped for: most reject an image part with a 400, and the ones that
    don't just ignore it while still billing for the tokens.
    """
    use_frames = supports_vision and bool(frames)
    system_parts = [style_block(style_anchors)]
    if use_frames:
        system_parts.append(screenshot_rules([seconds_to_timestamp(ts) for ts, _ in frames]))
    system_parts.append(chunk_output_rules(with_screenshots=use_frames))

    user_text = video_context_block(video_title, video_url, start_ts, end_ts, transcript_chunk)
    if use_frames:
        user_content = [{"type": "text", "text": user_text}] + frames_to_content_parts(frames)
    else:
        user_content = user_text

    return [
        {"role": "system", "content": "\n\n".join(system_parts)},
        {"role": "user", "content": user_content},
    ]


def resolve_model(engine: str) -> str:
    """MARGIN_MODEL overrides the registry default, so switching models on
    a provider never needs a code change."""
    return os.environ.get("MARGIN_MODEL") or get_provider(engine).default_model


def post_chat_completion(messages: list[dict], engine: str, api_key: str = "") -> str:
    """Shared POST + retry, so live chunks and any future whole-video call
    share one retry policy instead of drifting apart."""
    provider = get_provider(engine)
    url = f"{provider.base_url.rstrip('/')}/chat/completions"
    headers = {"Content-Type": "application/json", **provider.extra_headers}
    # Local servers need no auth; sending an empty bearer token upsets some.
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    body = {
        "model": resolve_model(engine),
        "messages": messages,
    }

    response = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        response = httpx.post(url, json=body, headers=headers, timeout=TIMEOUT_SEC)
        if response.status_code == 200:
            break
        if response.status_code not in RETRYABLE_STATUS_CODES or attempt == MAX_ATTEMPTS:
            raise RuntimeError(
                f"{engine} API returned HTTP {response.status_code}: {response.text}"
            )
        time.sleep(RETRY_BACKOFF_SEC * attempt)

    payload = response.json()
    try:
        return payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as e:
        raise RuntimeError(f"{engine} API returned unexpected response shape: {payload}") from e


def call_openai_compatible(
    transcript_chunk: str,
    video_title: str,
    video_url: str,
    start_ts: str,
    end_ts: str,
    style_anchors: list[str],
    frames: list[tuple[float, bytes]],
    engine: str,
    api_key: str = "",
) -> str:
    provider = get_provider(engine)
    messages = build_messages(
        transcript_chunk,
        video_title,
        video_url,
        start_ts,
        end_ts,
        style_anchors,
        frames,
        supports_vision=provider.supports_vision,
    )
    return post_chat_completion(messages, engine, api_key)
