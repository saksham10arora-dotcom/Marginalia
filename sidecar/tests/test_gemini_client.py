import json
from unittest.mock import MagicMock, patch

import pytest

from sidecar.gemini_client import call_gemini


@patch("sidecar.gemini_client.httpx.post")
def test_call_gemini_sends_transcript_and_frames_returns_text(mock_post):
    mock_post.return_value = MagicMock(
        status_code=200,
        json=lambda: {
            "candidates": [{"content": {"parts": [{"text": "## Section [00:01:00](url)\n\nSome notes."}]}}]
        },
    )

    result = call_gemini(
        transcript_chunk="the professor discusses vector spaces",
        video_title="Test Lecture",
        video_url="https://www.youtube.com/watch?v=abc123",
        start_ts="00:01:00",
        end_ts="00:02:00",
        style_anchors=["anchor text"],
        frames=[(65.0, b"\xff\xd8fakejpegbytes")],
        api_key="fake-key",
    )

    assert result == "## Section [00:01:00](url)\n\nSome notes."
    mock_post.assert_called_once()
    url, kwargs = mock_post.call_args.args[0], mock_post.call_args.kwargs
    assert "generativelanguage.googleapis.com" in url
    assert "fake-key" in url
    body = kwargs["json"]
    parts = body["contents"][0]["parts"]
    prompt_text = next(p["text"] for p in parts if "text" in p)
    assert "vector spaces" in prompt_text
    assert "00:01:05" in prompt_text  # frame timestamp, not a filename
    assert "screenshot: HH:MM:SS" in prompt_text  # instructs the marker convention
    assert "![" not in prompt_text  # never instructs an image embed
    assert any(p.get("inline_data", {}).get("mime_type") == "image/jpeg" for p in parts)


@patch("sidecar.gemini_client.httpx.post")
def test_call_gemini_works_with_no_frames(mock_post):
    mock_post.return_value = MagicMock(
        status_code=200,
        json=lambda: {"candidates": [{"content": {"parts": [{"text": "## Section\n\nText only."}]}}]},
    )
    result = call_gemini(
        transcript_chunk="x", video_title="title", video_url="https://youtube.com/watch?v=x",
        start_ts="00:00:00", end_ts="00:01:00", style_anchors=[], frames=[], api_key="fake-key",
    )
    assert result == "## Section\n\nText only."
    body = mock_post.call_args.kwargs["json"]
    parts = body["contents"][0]["parts"]
    assert not any("inline_data" in p for p in parts)


@patch("sidecar.gemini_client.httpx.post")
@patch("sidecar.gemini_client.time.sleep")
def test_call_gemini_raises_after_exhausting_retries_on_retryable_error(mock_sleep, mock_post):
    mock_post.return_value = MagicMock(status_code=429, text="rate limited")
    with pytest.raises(RuntimeError, match="rate limited"):
        call_gemini(
            transcript_chunk="x", video_title="title", video_url="https://youtube.com/watch?v=x",
            start_ts="00:00:00", end_ts="00:01:00", style_anchors=[], frames=[], api_key="fake-key",
        )
    assert mock_post.call_count == 3  # MAX_ATTEMPTS
    assert mock_sleep.call_count == 2  # backs off between attempts, not after the last one


@patch("sidecar.gemini_client.httpx.post")
def test_call_gemini_does_not_retry_non_retryable_errors(mock_post):
    mock_post.return_value = MagicMock(status_code=400, text="bad request")
    with pytest.raises(RuntimeError, match="bad request"):
        call_gemini(
            transcript_chunk="x", video_title="title", video_url="https://youtube.com/watch?v=x",
            start_ts="00:00:00", end_ts="00:01:00", style_anchors=[], frames=[], api_key="fake-key",
        )
    assert mock_post.call_count == 1


@patch("sidecar.gemini_client.httpx.post")
@patch("sidecar.gemini_client.time.sleep")
def test_call_gemini_succeeds_after_transient_503(mock_sleep, mock_post):
    mock_post.side_effect = [
        MagicMock(status_code=503, text="high demand"),
        MagicMock(status_code=200, json=lambda: {
            "candidates": [{"content": {"parts": [{"text": "## Section\n\nRecovered."}]}}]
        }),
    ]
    result = call_gemini(
        transcript_chunk="x", video_title="title", video_url="https://youtube.com/watch?v=x",
        start_ts="00:00:00", end_ts="00:01:00", style_anchors=[], frames=[], api_key="fake-key",
    )
    assert result == "## Section\n\nRecovered."
    assert mock_post.call_count == 2


@patch("sidecar.gemini_client.httpx.post")
def test_call_gemini_raises_on_malformed_response(mock_post):
    mock_post.return_value = MagicMock(status_code=200, json=lambda: {"unexpected": "shape"})
    with pytest.raises(RuntimeError, match="unexpected response shape"):
        call_gemini(
            transcript_chunk="x", video_title="title", video_url="https://youtube.com/watch?v=x",
            start_ts="00:00:00", end_ts="00:01:00", style_anchors=[], frames=[], api_key="fake-key",
        )
