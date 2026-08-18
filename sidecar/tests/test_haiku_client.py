import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from sidecar.haiku_client import load_style_anchors, build_system_prompt, call_haiku

FIXTURES = Path(__file__).parent / "fixtures"


def test_load_style_anchors_reads_md_files_from_vault(tmp_path):
    (tmp_path / "note1.md").write_text("---\ntitle: one\n---\n\ncontent one")
    (tmp_path / "note2.md").write_text("---\ntitle: two\n---\n\ncontent two")
    anchors = load_style_anchors(tmp_path, count=2)
    assert len(anchors) == 2
    assert all("title:" in a for a in anchors)


def test_load_style_anchors_caps_at_requested_count(tmp_path):
    for i in range(5):
        (tmp_path / f"note{i}.md").write_text(f"---\ntitle: {i}\n---\n\ncontent")
    anchors = load_style_anchors(tmp_path, count=2)
    assert len(anchors) == 2


def test_build_system_prompt_embeds_style_anchors():
    anchor = FIXTURES.joinpath("style_anchor.md").read_text()
    prompt = build_system_prompt([anchor])
    assert "Lecture 2: Linear Algebra" in prompt
    assert "structured markdown" in prompt.lower()
    assert "## " in prompt  # instructs section-header format


@patch("sidecar.haiku_client.subprocess.run")
def test_call_haiku_sends_transcript_and_returns_text(mock_run):
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout=json.dumps({
            "type": "result", "subtype": "success", "is_error": False,
            "result": "## New Section [00:01:00](url)\n\nContent here.",
        }),
        stderr="",
    )

    result = call_haiku(
        transcript_chunk="the professor discusses vector spaces",
        video_title="Lecture 2",
        video_url="https://www.youtube.com/watch?v=abc123",
        start_ts="00:01:00",
        end_ts="00:02:00",
        style_anchors=["anchor text"],
    )

    assert result == "## New Section [00:01:00](url)\n\nContent here."
    mock_run.assert_called_once()
    cli_args = mock_run.call_args.args[0]
    assert cli_args[0] == "claude"
    assert "--model" in cli_args
    assert cli_args[cli_args.index("--model") + 1] == "haiku"
    assert "vector spaces" in cli_args[-1]  # user message is the final positional arg
    assert "https://www.youtube.com/watch?v=abc123" in cli_args[-1]


@patch("sidecar.haiku_client.subprocess.run")
def test_call_haiku_raises_on_nonzero_exit(mock_run):
    mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="not logged in")
    with pytest.raises(RuntimeError, match="not logged in"):
        call_haiku("x", "title", "https://youtube.com/watch?v=x", "00:00:00", "00:01:00", [])


@patch("sidecar.haiku_client.subprocess.run")
def test_call_haiku_raises_when_cli_reports_error(mock_run):
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout=json.dumps({"type": "result", "is_error": True, "result": None}),
        stderr="",
    )
    with pytest.raises(RuntimeError, match="reported an error"):
        call_haiku("x", "title", "https://youtube.com/watch?v=x", "00:00:00", "00:01:00", [])


@patch("sidecar.haiku_client.subprocess.run")
def test_call_haiku_raises_runtimeerror_on_malformed_json(mock_run):
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout="not valid json{{{",
        stderr="",
    )
    with pytest.raises(RuntimeError, match="non-JSON output"):
        call_haiku("x", "title", "https://youtube.com/watch?v=x", "00:00:00", "00:01:00", [])
