import logging
import os
import re
from pathlib import Path

logger = logging.getLogger(__name__)

# The project was called Marginalia before it was called Margin. Every setting
# is read as MARGIN_* first and falls back to the old MARGINALIA_* name, so a
# rename does not silently empty someone's vault or flip their engine back to
# the default. This project has already shipped exactly that bug once (a
# sidecar restart quietly serving an empty default vault), which is why the
# fallback exists rather than a clean break.
_LEGACY_PREFIX = "MARGINALIA_"


def _setting(name: str, default: str | None = None) -> str | None:
    current = os.environ.get(f"MARGIN_{name}")
    if current is not None:
        return current
    legacy = os.environ.get(f"{_LEGACY_PREFIX}{name}")
    if legacy is not None:
        logger.warning(
            "%s%s is deprecated, rename it to MARGIN_%s", _LEGACY_PREFIX, name, name
        )
        return legacy
    return default


def _default_vault_path() -> Path:
    """~/MarginNotes, unless a pre-rename ~/MarginaliaNotes already has notes
    in it -- picking the empty new folder over someone's existing notes would
    look exactly like data loss."""
    new = Path.home() / "MarginNotes"
    legacy = Path.home() / "MarginaliaNotes"
    if not new.exists() and legacy.exists() and any(legacy.rglob("*.md")):
        logger.warning(
            "Using legacy vault %s; rename it to %s or set MARGIN_VAULT_PATH", legacy, new
        )
        return legacy
    return new


# Defaults to ~/MarginNotes so a fresh clone has somewhere to write;
# override with MARGIN_VAULT_PATH to point at an existing Obsidian vault.
# Created on import if it doesn't exist yet -- main.py mounts it as a static
# file directory at startup, which raises immediately if the folder is missing.
_vault_setting = _setting("VAULT_PATH")
VAULT_PATH = Path(_vault_setting) if _vault_setting else _default_vault_path()
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
# cap. Set MARGIN_ENGINE=gemini to override for short/deliberate tests.
NOTE_ENGINE = _setting("ENGINE", "haiku")

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
# a folder of text files. Set MARGIN_AUTOLINK=0 to write plain prose.
AUTOLINK = _setting("AUTOLINK", "1") not in ("0", "false", "False")
# Per generated section. A cap because a lecture that name-drops thirty
# concepts should not produce a section that is more link than sentence.
MAX_AUTOLINKS_PER_SECTION = int(_setting("MAX_AUTOLINKS", "8"))


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
