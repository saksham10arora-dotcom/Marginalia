import base64
import time

import httpx

from sidecar.frame_extractor import seconds_to_timestamp
from sidecar.prompts import (
    chunk_output_rules,
    screenshot_rules,
    style_block,
    video_context_block,
)

GEMINI_MODEL = "gemini-3.5-flash"
GEMINI_TIMEOUT_SEC = 60
# Google's own 503 message says "Spikes in demand are usually temporary,
# please try again later" — so we do, a couple of times, before giving up.
RETRYABLE_STATUS_CODES = {429, 503}
MAX_ATTEMPTS = 3
RETRY_BACKOFF_SEC = 3


def _build_prompt(video_title, video_url, start_ts, end_ts, transcript_chunk, style_anchors, frame_timestamps):
    """Vision engine: style contract + frame-judging rules + the payload, all
    in one text part (Gemini has no separate system role in this API shape)."""
    return "\n\n".join([
        style_block(style_anchors),
        screenshot_rules(frame_timestamps, scope="this chunk"),
        chunk_output_rules(with_screenshots=True),
        video_context_block(video_title, video_url, start_ts, end_ts, transcript_chunk),
    ])


def frames_to_parts(frames: list[tuple[float, bytes]]) -> list[dict]:
    return [
        {"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(jpeg_bytes).decode()}}
        for _ts, jpeg_bytes in frames
    ]


def post_to_gemini(parts: list[dict], api_key: str) -> str:
    """Shared multimodal call + retry/backoff, used both for per-chunk live
    notes and for the whole-video finalize regeneration (sidecar/finalize.py)
    -- same model, same retry policy, just a different prompt/parts shape."""
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
        f"?key={api_key}"
    )
    body = {"contents": [{"parts": parts}]}

    response = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        response = httpx.post(url, json=body, timeout=GEMINI_TIMEOUT_SEC)
        if response.status_code == 200:
            break
        if response.status_code not in RETRYABLE_STATUS_CODES or attempt == MAX_ATTEMPTS:
            raise RuntimeError(f"Gemini API returned HTTP {response.status_code}: {response.text}")
        time.sleep(RETRY_BACKOFF_SEC * attempt)

    payload = response.json()
    try:
        return payload["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError) as e:
        raise RuntimeError(f"Gemini API returned unexpected response shape: {payload}") from e


def call_gemini(
    transcript_chunk: str,
    video_title: str,
    video_url: str,
    start_ts: str,
    end_ts: str,
    style_anchors: list[str],
    frames: list[tuple[float, bytes]],
    api_key: str,
) -> str:
    frame_timestamps = [seconds_to_timestamp(ts) for ts, _ in frames]
    prompt = _build_prompt(
        video_title, video_url, start_ts, end_ts, transcript_chunk, style_anchors, frame_timestamps,
    )
    parts = [{"text": prompt}] + frames_to_parts(frames)
    return post_to_gemini(parts, api_key)
