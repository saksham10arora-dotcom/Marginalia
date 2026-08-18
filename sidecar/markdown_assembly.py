import re
from difflib import SequenceMatcher

HEADING_RE = re.compile(r"^##\s+(.+?)\s*\[", re.MULTILINE)
# This regex matches a timestamp+link and removes it to extract the body text.
# It correctly handles URLs with zero or one level of nested parentheses (e.g., Wikipedia URLs like
# https://en.wikipedia.org/wiki/Generics_(programming)). This is sufficient for this project's real
# use case (YouTube video links with ?t=Ns params, never nested-parens URLs).
# LIMITATION: URLs with two or more levels of nested parentheses or genuinely unbalanced parens will
# leak trailing text into the extracted body (e.g. for "https://example.com/(a(b(c)d)e))" the body
# extraction will leave "e))" as junk). This degrades similarity comparison but does not crash.
# A general fix would require a balanced-paren scanner, which is overkill given this project's
# actual URL patterns. See test_link_remainder_regex_documents_two_level_nesting_limitation for
# what the current behavior is.
LINK_REMAINDER_RE = re.compile(r"^[^\]]*\]\((?:[^()]*|\([^)]*\))*\)")
BODY_SIMILARITY_THRESHOLD = 0.8


def _normalize_heading(heading: str) -> str:
    """Normalize heading for comparison: lowercase, strip trailing punctuation."""
    heading = heading.casefold().strip()
    # Strip trailing punctuation like :, ., etc.
    heading = heading.rstrip(":.!?,;- \t")
    return heading


def _heading_text(section: str) -> str | None:
    match = HEADING_RE.search(section)
    return match.group(1).strip() if match else None


def _body_text(section: str) -> str:
    # Strip the heading line, keep the rest.
    lines = section.split("\n", 1)
    return lines[1].strip() if len(lines) > 1 else ""


def dedupe_section(existing_content: str, new_section: str) -> str | None:
    new_heading = _heading_text(new_section)
    if new_heading is None:
        return new_section  # Not a `##` section (e.g. a TL;DR block) — never dedupe those.

    new_body = _body_text(new_section)

    for existing_heading_match in HEADING_RE.finditer(existing_content):
        # Normalize both headings before comparing to catch near-duplicates with case/punctuation differences.
        if _normalize_heading(existing_heading_match.group(1).strip()) != _normalize_heading(new_heading):
            continue
        # Same heading text — check whether the body is substantially the same too.
        start = existing_heading_match.end()
        next_heading = HEADING_RE.search(existing_content, start)
        end = next_heading.start() if next_heading else len(existing_content)
        existing_body = existing_content[start:end].strip()
        # Remove the full timestamp+link remainder, handling URLs with balanced parentheses.
        existing_body = LINK_REMAINDER_RE.sub("", existing_body, count=1).strip()

        similarity = SequenceMatcher(None, existing_body, new_body).ratio()
        if similarity >= BODY_SIMILARITY_THRESHOLD:
            return None

    return new_section
