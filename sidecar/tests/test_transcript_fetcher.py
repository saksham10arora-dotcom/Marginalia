from unittest.mock import MagicMock, patch

from sidecar.transcript_fetcher import fetch_transcript


@patch("sidecar.transcript_fetcher.YouTubeTranscriptApi")
def test_fetch_transcript_converts_snippets_to_cues(mock_api_cls):
    snippet1 = MagicMock(start=0.5, text="Hello")
    snippet2 = MagicMock(start=2.0, text="World")
    mock_api_cls.return_value.fetch.return_value = [snippet1, snippet2]

    cues = fetch_transcript("abc123")

    assert cues == [
        {"startSec": 0.5, "text": "Hello"},
        {"startSec": 2.0, "text": "World"},
    ]
    mock_api_cls.return_value.fetch.assert_called_once_with("abc123")
