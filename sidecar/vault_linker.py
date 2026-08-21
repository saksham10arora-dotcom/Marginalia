"""Turn isolated lecture notes into a connected Obsidian graph.

A note that says "eigenvalues" is dead text. `[[Eigenvalues]]` is a real edge
to the note you already wrote about them three lectures ago, and it shows up
in that note's backlinks without you doing anything. This module finds those
edges automatically: it reads the titles of every note already in the vault,
then wikilinks the first mention of each in a freshly generated note.

The hard part is not finding matches, it is *not* linking things that only
look like prose: LaTeX (`$...$`), code, existing links, headings, and the
Gemini engine's invisible screenshot markers all have to come through
untouched. Everything protected gets masked behind a sentinel before matching
and restored afterward -- the same technique renderer.js uses to keep
`marked` away from math.
"""
import re
from pathlib import Path

# Below this, titles are too generic to link without turning notes into a mess
# of blue ("Set", "Map", "Proof" would match constantly and mean nothing).
MIN_TITLE_LENGTH = 4

_SENTINEL = "\x00LINKMASK{}\x00"

# Order matters: outermost/greediest first, so a fenced block containing a
# `$` is masked as code rather than half-masked as math.
_PROTECTED_PATTERNS = [
    re.compile(r"\A---\n.*?\n---\n", re.DOTALL),   # YAML frontmatter
    re.compile(r"```.*?```", re.DOTALL),            # fenced code
    re.compile(r"<!--.*?-->", re.DOTALL),           # screenshot markers, comments
    re.compile(r"\$\$.*?\$\$", re.DOTALL),          # display math
    re.compile(r"\$[^\n$]+?\$"),                    # inline math
    re.compile(r"`[^`\n]+?`"),                      # inline code
    re.compile(r"!?\[\[[^\]]*?\]\]"),               # existing wikilinks/embeds
    re.compile(r"!?\[[^\]]*?\]\([^)]*?\)"),         # markdown links/images
    re.compile(r"^#{1,6} .*$", re.MULTILINE),       # headings
]


def _mask_protected(text: str) -> tuple[str, list[str]]:
    stash: list[str] = []

    def stash_match(match: re.Match) -> str:
        stash.append(match.group(0))
        return _SENTINEL.format(len(stash) - 1)

    for pattern in _PROTECTED_PATTERNS:
        text = pattern.sub(stash_match, text)
    return text, stash


def _unmask(text: str, stash: list[str]) -> str:
    # Restore in reverse so a sentinel nested inside a later-stashed span
    # (e.g. inline math inside a heading) resolves correctly.
    for i in range(len(stash) - 1, -1, -1):
        text = text.replace(_SENTINEL.format(i), stash[i])
    return text


def collect_link_targets(
    vault_path: Path, exclude_filename: str | None = None
) -> list[tuple[str, str]]:
    """(phrase to match, note to link to) pairs, longest phrase first.

    Titles alone are not enough, and this is not a theoretical concern: a real
    vault of lecture notes is full of titles like "Lecture 4: Linear Algebra
    (cont.); Probability Theory". Nobody writes that phrase in prose, so
    matching on titles alone fires almost never. Obsidian already has the
    answer -- an `aliases:` list in frontmatter -- so every alias becomes its
    own match phrase pointing at the same note. Add `aliases: [linear algebra,
    linalg]` to a note and prose mentions start linking to it.

    Longest-first matters: with "linear algebra" and "algebra" both aliased,
    the longer, more specific phrase should win.
    """
    targets: dict[str, str] = {}
    for md_file in vault_path.rglob("*.md"):
        rel = md_file.relative_to(vault_path).as_posix()
        if exclude_filename and rel == exclude_filename:
            continue
        try:
            head = md_file.read_text()[:4000]
        except OSError:
            continue

        title_match = re.search(r"^title:\s*[\"\']?(.+?)[\"\']?\s*$", head, re.MULTILINE)
        title = title_match.group(1).strip() if title_match else md_file.stem.replace("-", " ")
        if not title:
            continue

        phrases = [title, *_parse_aliases(head)]
        for phrase in phrases:
            phrase = phrase.strip()
            # First writer wins, so a note does not get hijacked by a later
            # note claiming the same alias.
            if len(phrase) >= MIN_TITLE_LENGTH and phrase.casefold() not in {
                k.casefold() for k in targets
            }:
                targets[phrase] = title

    return sorted(targets.items(), key=lambda kv: len(kv[0]), reverse=True)


def _parse_aliases(frontmatter_text: str) -> list[str]:
    """Read Obsidian's `aliases:` field in either supported YAML shape:
    an inline `[a, b]` list, or an indented `- a` block."""
    inline = re.search(r"^aliases:\s*\[(.*?)\]\s*$", frontmatter_text, re.MULTILINE)
    if inline:
        return [a.strip().strip("\"'") for a in inline.group(1).split(",") if a.strip()]

    block = re.search(r"^aliases:\s*\n((?:\s*-\s*.+\n?)+)", frontmatter_text, re.MULTILINE)
    if block:
        return [
            line.strip().lstrip("-").strip().strip("\"'")
            for line in block.group(1).splitlines()
            if line.strip()
        ]
    return []


def collect_note_titles(vault_path: Path, exclude_filename: str | None = None) -> list[str]:
    """Back-compat shim: just the match phrases, no targets."""
    return [phrase for phrase, _target in collect_link_targets(vault_path, exclude_filename)]


def add_wikilinks(
    markdown: str,
    targets: list[tuple[str, str]] | list[str],
    max_links: int | None = None,
) -> str:
    """Wikilink the first mention of each phrase, once per note.

    Once per note, not once per paragraph: Obsidian's graph only needs one
    edge, and linking every occurrence is what makes auto-linked vaults
    unreadable.
    """
    if not targets:
        return markdown

    # Accept a plain list of phrases (phrase links to itself) as well as
    # (phrase, target) pairs, so callers with simple vaults stay simple.
    pairs = [t if isinstance(t, tuple) else (t, t) for t in targets]

    masked, stash = _mask_protected(markdown)
    linked = 0
    used_targets: set[str] = set()

    for phrase, target in pairs:
        if max_links is not None and linked >= max_links:
            break
        # One edge per destination note, even if several of its aliases match.
        if target in used_targets:
            continue
        # Whole-word, case-insensitive. re.escape so a phrase containing
        # regex metacharacters ("C++ (Part 1)") can't blow up the pattern.
        pattern = re.compile(rf"(?<![\w\[|]){re.escape(phrase)}(?![\w\]|])", re.IGNORECASE)
        match = pattern.search(masked)
        if not match:
            continue
        matched_text = match.group(0)
        # Preserve the sentence's own wording/casing with an alias rather than
        # rewriting the prose to match the note's title.
        replacement = (
            f"[[{target}]]" if matched_text == target else f"[[{target}|{matched_text}]]"
        )
        masked = masked[: match.start()] + replacement + masked[match.end() :]
        linked += 1
        used_targets.add(target)

    return _unmask(masked, stash)


def already_linked_titles(content: str) -> set[str]:
    """Titles this note already links, so a live session appending a section
    every 60 seconds does not re-link the same concept in every chunk."""
    return {m.split("|")[0].strip() for m in re.findall(r"\[\[([^\]]+)\]\]", content)}


def link_note_to_vault(
    markdown: str,
    vault_path: Path,
    exclude_filename: str | None = None,
    max_links: int | None = None,
    existing_content: str = "",
) -> str:
    targets = collect_link_targets(vault_path, exclude_filename=exclude_filename)
    if existing_content:
        seen = already_linked_titles(existing_content)
        targets = [(p, t) for p, t in targets if t not in seen]
    return add_wikilinks(markdown, targets, max_links=max_links)
