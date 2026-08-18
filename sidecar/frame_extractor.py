import glob
import os
import shutil
import subprocess
import tempfile
import time

import imagehash
from PIL import Image

# yt-dlp resolves a fresh signed CDN URL on every call, and that URL
# intermittently 403s even though yt-dlp itself is the one that just
# resolved it (observed directly: the exact same command succeeds, then
# fails, then succeeds again seconds apart, no code change in between) --
# YouTube's edge servers reject some signed URLs unpredictably. A retry
# gets a brand new URL, which often isn't rejected.
DOWNLOAD_ATTEMPTS = 3
DOWNLOAD_RETRY_BACKOFF_SEC = 2


def _to_seconds(ts: str) -> float:
    parts = [float(p) for p in ts.split(":")]
    while len(parts) < 3:
        parts.insert(0, 0.0)
    return parts[0] * 3600 + parts[1] * 60 + parts[2]


def seconds_to_timestamp(total_sec: float) -> str:
    total_sec = int(total_sec)
    h, rem = divmod(total_sec, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def _download_segment(video_url: str, start_ts: str, end_ts: str, dest_dir: str) -> str:
    """Downloads just [start_ts, end_ts] of the video into dest_dir via
    yt-dlp's own downloader (not a raw ffmpeg network fetch).

    Handing a resolved CDN URL straight to ffmpeg (with matching headers)
    still gets a 403 from YouTube — their edge servers apparently validate
    more than headers (TLS fingerprint, request sequencing) that only
    yt-dlp's own downloader replicates correctly, since it's the thing that
    resolved the URL in the first place. Having yt-dlp download the small
    time range we actually need sidesteps the whole problem: ffmpeg then
    only ever touches a local file, no network involved on its end.
    """
    out_template = os.path.join(dest_dir, "segment.%(ext)s")
    cmd = [
        "yt-dlp", "--no-warnings", "-f", "best",
        "--download-sections", f"*{start_ts}-{end_ts}",
        "-o", out_template, video_url,
    ]

    last_error: subprocess.CalledProcessError | None = None
    for attempt in range(1, DOWNLOAD_ATTEMPTS + 1):
        result = subprocess.run(cmd, timeout=300, capture_output=True, text=True)
        if result.returncode == 0:
            matches = glob.glob(os.path.join(dest_dir, "segment.*"))
            if not matches:
                raise RuntimeError(f"yt-dlp reported success but wrote no segment file for {video_url}")
            return matches[0]
        last_error = subprocess.CalledProcessError(result.returncode, cmd, result.stdout, result.stderr)
        if attempt < DOWNLOAD_ATTEMPTS:
            time.sleep(DOWNLOAD_RETRY_BACKOFF_SEC)

    raise RuntimeError(
        f"yt-dlp failed to download segment after {DOWNLOAD_ATTEMPTS} attempts "
        f"(likely a transient YouTube CDN 403): {last_error.stderr[-500:]}"
    )


def extract_candidate_frames(
    video_url: str,
    start_ts: str,
    end_ts: str,
    interval: float = 3.0,
    hash_threshold: int = 5,
    max_frames: int = 3,
) -> list[tuple[float, bytes]]:
    """Downloads [start_ts, end_ts] of the video, samples one frame every
    `interval` seconds, keeps only visually-distinct frames (perceptual-hash
    dedup), and returns at most `max_frames` as (timestamp_sec, jpeg_bytes)
    — nothing touches disk outside a temp dir that's cleaned up before
    returning."""
    workdir = tempfile.mkdtemp(prefix="hn-frames-")
    try:
        segment_path = _download_segment(video_url, start_ts, end_ts, workdir)

        cmd = [
            "ffmpeg", "-hide_banner", "-loglevel", "error",
            "-i", segment_path, "-vf", f"fps=1/{interval}",
            os.path.join(workdir, "cand_%05d.jpg"),
        ]
        subprocess.run(cmd, check=True, timeout=60)

        cands = sorted(glob.glob(os.path.join(workdir, "cand_*.jpg")))
        offset = _to_seconds(start_ts)

        kept = []  # (timestamp_sec, path, hash)
        last_hash = None
        for idx, fp in enumerate(cands):
            ts = idx * interval + offset
            try:
                h = imagehash.phash(Image.open(fp))
            except Exception:
                continue
            if last_hash is None or (h - last_hash) > hash_threshold:
                kept.append((ts, fp, h))
                last_hash = h

        if len(kept) > max_frames:
            # Greedily keep the most visually-distinct frames from their neighbor.
            scored = [(0.0, kept[0])] + [
                (kept[i][2] - kept[i - 1][2], kept[i]) for i in range(1, len(kept))
            ]
            scored.sort(key=lambda x: x[0], reverse=True)
            keep_set = {id(k[1]) for k in scored[:max_frames]}
            kept = sorted((k for k in kept if id(k) in keep_set), key=lambda k: k[0])

        return [(ts, open(fp, "rb").read()) for ts, fp, _h in kept]
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
