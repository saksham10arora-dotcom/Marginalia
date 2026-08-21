from unittest.mock import MagicMock, patch

import pytest

from sidecar.openai_compatible import (
    build_messages,
    call_openai_compatible,
    post_chat_completion,
    resolve_model,
)
from sidecar.providers import PROVIDERS, get_provider, is_openai_compatible


def _ok(text="## Section [00:01:00](url)\n\nNotes."):
    return MagicMock(status_code=200, json=lambda: {"choices": [{"message": {"content": text}}]})


# --- registry ---

def test_every_registered_provider_has_a_usable_base_url_and_model():
    for name, spec in PROVIDERS.items():
        assert spec.base_url.startswith("http"), name
        assert spec.default_model, name


def test_is_openai_compatible_rejects_the_native_engines():
    # haiku (local CLI) and gemini (its own API shape) are not in the registry.
    assert not is_openai_compatible("haiku")
    assert not is_openai_compatible("gemini")
    assert is_openai_compatible("groq")


def test_get_provider_raises_a_helpful_error_for_an_unknown_engine():
    with pytest.raises(ValueError, match="Known engines"):
        get_provider("not-a-provider")


def test_resolve_model_prefers_the_env_override(monkeypatch):
    monkeypatch.setenv("MARGIN_MODEL", "some/custom-model")
    assert resolve_model("groq") == "some/custom-model"


def test_resolve_model_falls_back_to_the_registry_default(monkeypatch):
    monkeypatch.delenv("MARGIN_MODEL", raising=False)
    assert resolve_model("groq") == PROVIDERS["groq"].default_model


# --- message building ---

def test_build_messages_puts_style_in_system_and_transcript_in_user():
    messages = build_messages(
        "vectors are ordered lists", "Lecture", "https://x", "00:01:00", "00:02:00",
        ["anchor"], [], supports_vision=False,
    )
    assert [m["role"] for m in messages] == ["system", "user"]
    assert "structured markdown" in messages[0]["content"].lower()
    assert "vectors are ordered lists" in messages[1]["content"]


def test_build_messages_drops_frames_for_a_text_only_provider():
    messages = build_messages(
        "text", "Lecture", "https://x", "00:01:00", "00:02:00",
        ["anchor"], [(65.0, b"\xff\xd8jpeg")], supports_vision=False,
    )
    # Plain string content, no image parts, and no screenshot instructions
    # the model could not act on anyway.
    assert isinstance(messages[1]["content"], str)
    assert "screenshot" not in messages[0]["content"].lower()


def test_build_messages_attaches_frames_as_data_urls_for_a_vision_provider():
    messages = build_messages(
        "text", "Lecture", "https://x", "00:01:00", "00:02:00",
        ["anchor"], [(65.0, b"\xff\xd8jpeg")], supports_vision=True,
    )
    parts = messages[1]["content"]
    assert isinstance(parts, list)
    image_parts = [p for p in parts if p["type"] == "image_url"]
    assert len(image_parts) == 1
    assert image_parts[0]["image_url"]["url"].startswith("data:image/jpeg;base64,")
    assert "screenshot: HH:MM:SS" in messages[0]["content"]
    assert "00:01:05" in messages[0]["content"]  # the frame's own timestamp


# --- transport ---

@patch("sidecar.openai_compatible.httpx.post")
def test_call_openai_compatible_posts_to_the_provider_and_returns_text(mock_post):
    mock_post.return_value = _ok()
    result = call_openai_compatible(
        transcript_chunk="vector spaces", video_title="L", video_url="https://x",
        start_ts="00:01:00", end_ts="00:02:00", style_anchors=["a"], frames=[],
        engine="groq", api_key="secret-key",
    )
    assert result == "## Section [00:01:00](url)\n\nNotes."
    url = mock_post.call_args.args[0]
    assert url == "https://api.groq.com/openai/v1/chat/completions"
    assert mock_post.call_args.kwargs["headers"]["Authorization"] == "Bearer secret-key"


@patch("sidecar.openai_compatible.httpx.post")
def test_openrouter_sends_its_attribution_headers(mock_post):
    mock_post.return_value = _ok()
    post_chat_completion([{"role": "user", "content": "hi"}], "openrouter", "k")
    headers = mock_post.call_args.kwargs["headers"]
    assert "HTTP-Referer" in headers and "X-Title" in headers


@patch("sidecar.openai_compatible.httpx.post")
def test_local_provider_sends_no_authorization_header(mock_post):
    # Ollama/LM Studio need no auth, and an empty bearer token upsets some.
    mock_post.return_value = _ok()
    post_chat_completion([{"role": "user", "content": "hi"}], "ollama", "")
    assert "Authorization" not in mock_post.call_args.kwargs["headers"]


@patch("sidecar.openai_compatible.time.sleep")
@patch("sidecar.openai_compatible.httpx.post")
def test_retries_a_429_then_succeeds(mock_post, _sleep):
    mock_post.side_effect = [MagicMock(status_code=429, text="slow down"), _ok("recovered")]
    assert post_chat_completion([{"role": "user", "content": "x"}], "groq", "k") == "recovered"
    assert mock_post.call_count == 2


@patch("sidecar.openai_compatible.httpx.post")
def test_does_not_retry_a_401_and_surfaces_the_status(mock_post):
    mock_post.return_value = MagicMock(status_code=401, text="bad key")
    with pytest.raises(RuntimeError, match="401"):
        post_chat_completion([{"role": "user", "content": "x"}], "groq", "k")
    assert mock_post.call_count == 1


@patch("sidecar.openai_compatible.httpx.post")
def test_raises_on_an_unexpected_response_shape(mock_post):
    mock_post.return_value = MagicMock(status_code=200, json=lambda: {"unexpected": True})
    with pytest.raises(RuntimeError, match="unexpected response shape"):
        post_chat_completion([{"role": "user", "content": "x"}], "groq", "k")
