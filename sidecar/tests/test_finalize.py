from unittest.mock import MagicMock, patch

import pytest

from sidecar.finalize import extract_video_id, build_regenerate_prompt, call_regenerate


def test_extract_video_id_from_watch_url():
    assert extract_video_id("https://www.youtube.com/watch?v=fNk_zzaMoSs") == "fNk_zzaMoSs"


def test_extract_video_id_from_watch_url_with_extra_params():
    assert extract_video_id("https://www.youtube.com/watch?v=abc12345678&t=90s") == "abc12345678"


def test_extract_video_id_from_short_url():
    assert extract_video_id("https://youtu.be/abc12345678") == "abc12345678"


def test_extract_video_id_raises_on_unparseable_url():
    with pytest.raises(ValueError, match="Could not extract video ID"):
        extract_video_id("https://example.com/not-a-video")


def test_build_regenerate_prompt_includes_full_transcript_and_frame_timestamps():
    prompt = build_regenerate_prompt(
        transcript_text="the professor discusses vector spaces at length",
        video_title="Vectors",
        video_url="https://www.youtube.com/watch?v=abc123",
        frame_timestamps=["00:00:21", "00:01:45"],
        style_anchors=["anchor text"],
    )
    assert "the professor discusses vector spaces at length" in prompt
    assert "00:00:21" in prompt
    assert "00:01:45" in prompt
    assert "anchor text" in prompt
    assert "FULL transcript" in prompt
    assert "grouping content by topic" in prompt
    assert "screenshot: HH:MM:SS" in prompt
    assert "never an embedded image" in prompt


def test_build_regenerate_prompt_handles_no_frames():
    prompt = build_regenerate_prompt(
        transcript_text="text only",
        video_title="Vectors",
        video_url="https://www.youtube.com/watch?v=abc123",
        frame_timestamps=[],
        style_anchors=["anchor text"],
    )
    assert "(no candidate screenshots)" in prompt


@patch("sidecar.finalize.post_to_gemini")
def test_call_regenerate_sends_prompt_and_frames_returns_text(mock_post):
    mock_post.return_value = "> [!abstract] TL;DR\n> Summary.\n\n## Vectors [00:00:00](url)\n\nContent."

    result = call_regenerate(
        prompt="full prompt text",
        frames=[(21.0, b"\xff\xd8fakejpegbytes")],
        api_key="fake-key",
    )

    assert result == "> [!abstract] TL;DR\n> Summary.\n\n## Vectors [00:00:00](url)\n\nContent."
    mock_post.assert_called_once()
    parts = mock_post.call_args.args[0]
    assert any("full prompt text" in p.get("text", "") for p in parts)
    assert any(p.get("inline_data", {}).get("mime_type") == "image/jpeg" for p in parts)
    assert mock_post.call_args.args[1] == "fake-key"


@patch("sidecar.finalize.post_to_gemini")
def test_call_regenerate_works_with_no_frames(mock_post):
    mock_post.return_value = "body text"
    result = call_regenerate(prompt="full prompt text", frames=[], api_key="fake-key")
    assert result == "body text"
    parts = mock_post.call_args.args[0]
    assert len(parts) == 1  # text only, no image parts
