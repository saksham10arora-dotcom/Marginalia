from youtube_transcript_api import YouTubeTranscriptApi


def fetch_transcript(video_id: str) -> list[dict]:
    """Fetches {startSec, text} cues for a YouTube video via youtube_transcript_api.

    This runs server-side (not in the browser) because YouTube's timedtext API
    requires a proof-of-origin token when fetched directly from a page/content
    script — confirmed by direct testing: every browser-side fetch to the
    caption track's baseUrl returns HTTP 200 with an empty body, regardless of
    credentials or format params. youtube_transcript_api works around this and
    was already proven reliable on this machine (used for the Stat110 vault
    notes pipeline).
    """
    api = YouTubeTranscriptApi()
    transcript = api.fetch(video_id)
    return [{"startSec": snippet.start, "text": snippet.text} for snippet in transcript]
