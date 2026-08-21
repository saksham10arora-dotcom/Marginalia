import os
import re
from pathlib import Path

# Defaults to ~/MarginaliaNotes so a fresh clone has somewhere to write;
# override with MARGINALIA_VAULT_PATH to point at an existing Obsidian vault.
# Created on import if it doesn't exist yet -- main.py mounts it as a static
# file directory at startup, which raises immediately if the folder is missing.
VAULT_PATH = Path(os.environ.get("MARGINALIA_VAULT_PATH", str(Path.home() / "MarginaliaNotes")))
VAULT_PATH.mkdir(parents=True, exist_ok=True)

# "gemini" (transcript + candidate video frames) or "haiku" (transcript only,
# via the local `claude` CLI). Static config toggle, not a runtime fallback.
# Haiku is the default. Gemini's free tier is genuinely $0, but capped at 20
# generateContent calls/day for gemini-3.5-flash, shared across the whole
# Google Cloud project -- confirmed by hitting a 429 RESOURCE_EXHAUSTED
# after ~6 chunk calls on a single 10-minute video. Live note-taking fires
# one call per ~60s chunk for every video watched all day; a single normal
# lecture-length video would exhaust the entire day's quota on its own, and
# starve the batch /watch pipeline (which needs it far less -- one call per
# whole video) of the same shared pool. Haiku's local-CLI path has no such
# cap. Set MARGINALIA_ENGINE=gemini to override for short/deliberate tests.
NOTE_ENGINE = os.environ.get("MARGINALIA_ENGINE", "haiku")

# Single source of truth for the frontmatter `engine:` field, so a note
# always records which model actually wrote it rather than a hardcoded value.
ENGINE_LABELS = {
    "gemini": "gemini-3.5-flash",
    "haiku": "claude-haiku-4-5-20251001",
}

KEYS_PATH = Path.home() / ".config" / "keys.env"

# Auto-wikilink concepts in generated notes against titles already in the
# vault, turning isolated notes into a connected Obsidian graph. On by
# default -- it is most of the reason to keep notes in Obsidian rather than
# a folder of text files. Set MARGINALIA_AUTOLINK=0 to write plain prose.
AUTOLINK = os.environ.get("MARGINALIA_AUTOLINK", "1") not in ("0", "false", "False")
# Per generated section. A cap because a lecture that name-drops thirty
# concepts should not produce a section that is more link than sentence.
MAX_AUTOLINKS_PER_SECTION = int(os.environ.get("MARGINALIA_MAX_AUTOLINKS", "8"))


def load_api_keys(env_name: str) -> list[str]:
    """All configured keys for one env var name, in numbered order:
    NAME, then NAME_2, NAME_3, ... -- e.g. one per account, each with its own
    independent daily free-tier quota. Ignores commented-out lines (leading `#`).

    Generic so every provider in providers.py gets multi-key rotation for free,
    not just Gemini (which is where the pattern started, because its free tier
    caps at 20 calls/day/key).
    """
    if not KEYS_PATH.exists():
        return []
    pattern = re.compile(rf'^\s*{re.escape(env_name)}(?:_(\d+))?\s*=\s*"?([^"\n]+)"?')
    numbered: dict[int, str] = {}
    for line in KEYS_PATH.read_text().splitlines():
        if line.strip().startswith("#"):
            continue
        match = pattern.match(line)
        if match:
            suffix, value = match.groups()
            numbered[int(suffix) if suffix else 1] = value.strip()
    return [numbered[i] for i in sorted(numbered)]


def load_gemini_api_keys() -> list[str]:
    return load_api_keys("GEMINI_API_KEY")
