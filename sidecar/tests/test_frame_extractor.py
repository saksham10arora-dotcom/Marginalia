import os
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from sidecar.frame_extractor import extract_candidate_frames, seconds_to_timestamp


def test_seconds_to_timestamp_formats_hh_mm_ss():
    assert seconds_to_timestamp(591) == "00:09:51"


def test_seconds_to_timestamp_handles_over_an_hour():
    assert seconds_to_timestamp(3725) == "01:02:05"


def test_seconds_to_timestamp_truncates_fractional_seconds():
    assert seconds_to_timestamp(65.9) == "00:01:05"


def _write_dummy_jpeg(path):
    Image.new("RGB", (4, 4), color=(255, 255, 255)).save(path, "JPEG")


class FakeHash:
    """Minimal stand-in for imagehash.ImageHash supporting subtraction."""

    def __init__(self, value):
        self.value = value

    def __sub__(self, other):
        return abs(self.value - other.value)


def _fake_subprocess_run(dest_dir, num_candidates):
    """Simulates yt-dlp writing a segment file, then ffmpeg sampling it into
    `num_candidates` dummy frames — the two subprocess.run calls
    extract_candidate_frames makes, in order."""
    calls = []

    def run(cmd, **kwargs):
        calls.append(cmd)
        if cmd[0] == "yt-dlp":
            # -o template is the second-to-last arg; write the file it implies.
            out_template = cmd[cmd.index("-o") + 1]
            segment_path = out_template.replace("%(ext)s", "mp4")
            open(segment_path, "wb").write(b"fake video bytes")
        elif cmd[0] == "ffmpeg":
            out_pattern = cmd[-1]
            workdir = os.path.dirname(out_pattern)
            for i in range(1, num_candidates + 1):
                _write_dummy_jpeg(os.path.join(workdir, f"cand_{i:05d}.jpg"))
        return MagicMock(returncode=0)

    return run, calls


@patch("sidecar.frame_extractor.imagehash.phash")
@patch("sidecar.frame_extractor.subprocess.run")
def test_extract_candidate_frames_downloads_segment_then_samples_locally(mock_run, mock_phash):
    run, calls = _fake_subprocess_run(None, 1)
    mock_run.side_effect = run
    mock_phash.side_effect = [FakeHash(0)]

    extract_candidate_frames(
        "https://youtube.com/watch?v=abc123", start_ts="00:00:00", end_ts="00:00:03", max_frames=10,
    )

    yt_dlp_cmd, ffmpeg_cmd = calls
    assert yt_dlp_cmd[0] == "yt-dlp"
    assert "--download-sections" in yt_dlp_cmd
    assert "*00:00:00-00:00:03" in yt_dlp_cmd
    assert "https://youtube.com/watch?v=abc123" in yt_dlp_cmd
    assert ffmpeg_cmd[0] == "ffmpeg"
    assert "-headers" not in ffmpeg_cmd  # local file now, no network headers needed
    assert any(a.endswith("segment.mp4") for a in ffmpeg_cmd)


@patch("sidecar.frame_extractor.time.sleep")
@patch("sidecar.frame_extractor.imagehash.phash")
@patch("sidecar.frame_extractor.subprocess.run")
def test_extract_candidate_frames_retries_transient_download_failure(mock_run, mock_phash, mock_sleep):
    # YouTube's CDN 403s some signed URLs unpredictably -- a retry gets a
    # fresh URL from yt-dlp, which often succeeds.
    calls = []

    def run(cmd, **kwargs):
        calls.append(cmd)
        if cmd[0] == "yt-dlp":
            if len(calls) == 1:
                return MagicMock(returncode=1, stdout="", stderr="HTTP error 403 Forbidden")
            out_template = cmd[cmd.index("-o") + 1]
            open(out_template.replace("%(ext)s", "mp4"), "wb").write(b"fake video bytes")
            return MagicMock(returncode=0)
        if cmd[0] == "ffmpeg":
            out_pattern = cmd[-1]
            _write_dummy_jpeg(os.path.join(os.path.dirname(out_pattern), "cand_00001.jpg"))
            return MagicMock(returncode=0)

    mock_run.side_effect = run
    mock_phash.side_effect = [FakeHash(0)]

    frames = extract_candidate_frames(
        "https://youtube.com/watch?v=abc123", start_ts="00:00:00", end_ts="00:00:03", max_frames=10,
    )

    assert len(frames) == 1
    yt_dlp_calls = [c for c in calls if c[0] == "yt-dlp"]
    assert len(yt_dlp_calls) == 2  # first 403'd, second succeeded
    mock_sleep.assert_called_once()


@patch("sidecar.frame_extractor.time.sleep")
@patch("sidecar.frame_extractor.subprocess.run")
def test_extract_candidate_frames_raises_after_exhausting_download_retries(mock_run, mock_sleep):
    mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="HTTP error 403 Forbidden")

    with pytest.raises(RuntimeError, match="transient YouTube CDN 403"):
        extract_candidate_frames(
            "https://youtube.com/watch?v=abc123", start_ts="00:00:00", end_ts="00:00:03",
        )

    assert mock_run.call_count == 3  # DOWNLOAD_ATTEMPTS


@patch("sidecar.frame_extractor.imagehash.phash")
@patch("sidecar.frame_extractor.subprocess.run")
def test_extract_candidate_frames_dedupes_by_phash(mock_run, mock_phash):
    run, _calls = _fake_subprocess_run(None, 4)
    mock_run.side_effect = run
    # frames 1&2 look alike (hash 0), frame 3 is distinct (hash 20), frame 4 repeats frame 3 (hash 21)
    mock_phash.side_effect = [FakeHash(0), FakeHash(1), FakeHash(20), FakeHash(21)]

    frames = extract_candidate_frames(
        "https://youtube.com/watch?v=abc123", start_ts="00:00:00", end_ts="00:00:12", max_frames=10,
    )

    assert len(frames) == 2  # candidate 1 kept, candidate 2 deduped, candidate 3 kept, candidate 4 deduped
    for ts, jpeg_bytes in frames:
        assert isinstance(ts, float)
        assert jpeg_bytes.startswith(b"\xff\xd8")  # JPEG magic bytes


@patch("sidecar.frame_extractor.imagehash.phash")
@patch("sidecar.frame_extractor.subprocess.run")
def test_extract_candidate_frames_caps_at_max_frames(mock_run, mock_phash):
    run, _calls = _fake_subprocess_run(None, 5)
    mock_run.side_effect = run
    # all 5 candidates are visually distinct from each other
    mock_phash.side_effect = [FakeHash(0), FakeHash(20), FakeHash(40), FakeHash(60), FakeHash(80)]

    frames = extract_candidate_frames(
        "https://youtube.com/watch?v=abc123", start_ts="00:00:00", end_ts="00:00:15", max_frames=2,
    )

    assert len(frames) == 2
