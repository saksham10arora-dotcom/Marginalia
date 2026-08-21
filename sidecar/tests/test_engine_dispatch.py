from unittest.mock import patch

import pytest

import sidecar.config as config_module
from sidecar import engine_dispatch


def test_vision_support_matches_the_engine_family(monkeypatch):
    assert engine_dispatch.engine_supports_vision("gemini") is True
    assert engine_dispatch.engine_supports_vision("haiku") is False
    assert engine_dispatch.engine_supports_vision("openrouter") is True
    # Text-only provider: frames must not be extracted for it at all.
    assert engine_dispatch.engine_supports_vision("groq") is False


def test_current_engine_reads_config_at_call_time(monkeypatch):
    # Regression guard: this used to be frozen as a default arg at import,
    # so changing the configured engine had no effect until a restart.
    monkeypatch.setattr(config_module, "NOTE_ENGINE", "groq")
    assert engine_dispatch.current_engine() == "groq"


def test_engine_label_uses_the_static_map_for_native_engines():
    assert engine_dispatch.engine_label("haiku") == "claude-haiku-4-5-20251001"
    assert engine_dispatch.engine_label("gemini") == "gemini-3.5-flash"


def test_engine_label_records_provider_and_model_for_openai_compatible(monkeypatch):
    monkeypatch.delenv("MARGINALIA_MODEL", raising=False)
    assert engine_dispatch.engine_label("groq") == "groq/llama-3.3-70b-versatile"


@patch("sidecar.engine_dispatch.call_haiku", return_value="## S\n\nbody")
def test_generate_section_routes_haiku_without_needing_keys(mock_haiku):
    out = engine_dispatch.generate_section(
        transcript_chunk="t", video_title="T", video_url="u",
        start_ts="00:00:00", end_ts="00:01:00", style_anchors=[], frames=[],
        engine="haiku",
    )
    assert out == "## S\n\nbody"
    mock_haiku.assert_called_once()


@patch("sidecar.engine_dispatch.call_openai_compatible", return_value="## S\n\nbody")
@patch("sidecar.engine_dispatch.load_api_keys", return_value=["k1"])
def test_generate_section_routes_openai_compatible_with_the_engine_name(mock_keys, mock_call):
    out = engine_dispatch.generate_section(
        transcript_chunk="t", video_title="T", video_url="u",
        start_ts="00:00:00", end_ts="00:01:00", style_anchors=[], frames=[],
        engine="fireworks",
    )
    assert out == "## S\n\nbody"
    assert mock_call.call_args.kwargs["engine"] == "fireworks"
    assert mock_call.call_args.kwargs["api_key"] == "k1"


@patch("sidecar.engine_dispatch.load_api_keys", return_value=[])
def test_missing_key_names_the_env_var_the_user_has_to_add(mock_keys):
    with pytest.raises(RuntimeError, match="FIREWORKS_API_KEY"):
        engine_dispatch.generate_section(
            transcript_chunk="t", video_title="T", video_url="u",
            start_ts="00:00:00", end_ts="00:01:00", style_anchors=[], frames=[],
            engine="fireworks",
        )


@patch("sidecar.engine_dispatch.call_openai_compatible", return_value="ok")
def test_local_providers_need_no_key_at_all(mock_call):
    out = engine_dispatch.generate_section(
        transcript_chunk="t", video_title="T", video_url="u",
        start_ts="00:00:00", end_ts="00:01:00", style_anchors=[], frames=[],
        engine="ollama",
    )
    assert out == "ok"
    assert mock_call.call_args.kwargs["api_key"] == ""


def test_generate_section_rejects_an_unknown_engine():
    with pytest.raises((ValueError, RuntimeError)):
        engine_dispatch.generate_section(
            transcript_chunk="t", video_title="T", video_url="u",
            start_ts="00:00:00", end_ts="00:01:00", style_anchors=[], frames=[],
            engine="does-not-exist",
        )


@patch("sidecar.engine_dispatch.complete_with_haiku", return_value="Q: a\nA: b")
def test_complete_routes_to_the_configured_engine(mock_complete):
    assert engine_dispatch.complete("prompt", engine="haiku") == "Q: a\nA: b"
    mock_complete.assert_called_once_with("prompt")


@patch("sidecar.engine_dispatch.post_chat_completion", return_value="text out")
@patch("sidecar.engine_dispatch.load_api_keys", return_value=["k"])
def test_complete_sends_a_single_user_message_for_openai_compatible(mock_keys, mock_post):
    assert engine_dispatch.complete("write cards", engine="groq") == "text out"
    messages = mock_post.call_args.args[0]
    assert messages == [{"role": "user", "content": "write cards"}]
