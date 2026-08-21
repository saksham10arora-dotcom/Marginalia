"""Turn a finished lecture note into Anki flashcards.

Notes you never reopen are worth roughly nothing; the point of watching a
lecture is to still know it in a month. Anki solves the remembering, but only
if the cards exist, and writing cards by hand is exactly the chore that stops
people. The note is already structured (bold-term bullets, a key-terms
glossary), which is unusually good raw material for cards.

Output is TSV because Anki imports it natively with no plugin, no .apkg
tooling, and no schema to keep in sync with Anki's version.
"""
import re
from dataclasses import dataclass

MAX_CARDS = 25

FLASHCARD_INSTRUCTIONS = """You write Anki flashcards from a set of lecture notes.

Rules:
- One fact per card. If a card needs "and" to be true, split it into two cards.
- Questions must stand alone: a card saying "What is this?" is useless six weeks
  later with no context. Name the subject in the question.
- Test understanding, not trivia. Prefer "Why does X imply Y?" over "In what year...".
- Keep answers short: one sentence, or one formula, or a short list.
- Write formulas in LaTeX between $ delimiters, exactly as they appear in the notes.
- Do not write cards about the video itself, the lecturer, or course logistics.
- Skip anything you are not confident the notes actually support.

Output format, exactly, with no preamble and no closing commentary:

Q: <question>
A: <answer>
---
Q: <question>
A: <answer>

Produce at most {max_cards} cards, fewer if the notes do not support that many."""


@dataclass(frozen=True)
class Flashcard:
    front: str
    back: str


def strip_note_chrome(markdown: str) -> str:
    """Drop frontmatter, screenshot markers, and image embeds.

    None of it is card material, and the frontmatter in particular invites the
    model to make cards about the video's own metadata.
    """
    markdown = re.sub(r"\A---\n.*?\n---\n", "", markdown, flags=re.DOTALL)
    markdown = re.sub(r"<!--.*?-->", "", markdown, flags=re.DOTALL)
    markdown = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", markdown)
    return markdown.strip()


def build_flashcard_prompt(note_markdown: str, video_title: str) -> str:
    return (
        FLASHCARD_INSTRUCTIONS.format(max_cards=MAX_CARDS)
        + f'\n\nNotes from "{video_title}":\n\n{strip_note_chrome(note_markdown)}'
    )


def parse_flashcards(raw: str) -> list[Flashcard]:
    """Parse the Q:/A: block format, tolerantly.

    Models wrap output in ``` fences, add a "Here are your cards:" preamble,
    or drift on separator length. None of that should cost the user their whole
    deck, so anything that yields a Q and an A is accepted and everything else
    is skipped silently.
    """
    raw = re.sub(r"^\s*```[a-zA-Z]*\s*$", "", raw, flags=re.MULTILINE)
    cards: list[Flashcard] = []

    for block in re.split(r"\n-{3,}\n", raw):
        q_match = re.search(r"^\s*Q:\s*(.+?)\s*$", block, re.MULTILINE)
        a_match = re.search(r"^\s*A:\s*(.*?)(?=\n\s*Q:|\Z)", block, re.DOTALL | re.MULTILINE)
        if not q_match or not a_match:
            continue
        front = q_match.group(1).strip()
        back = a_match.group(1).strip()
        if front and back:
            cards.append(Flashcard(front=front, back=back))

    return cards[:MAX_CARDS]


def _tsv_field(text: str) -> str:
    """Anki's TSV import splits on tabs and newlines, so neither can survive
    inside a field. Newlines become <br> because Anki renders fields as HTML."""
    text = text.replace("\t", " ").strip()
    return re.sub(r"\n+", "<br>", text)


def cards_to_tsv(cards: list[Flashcard], tags: str = "marginalia") -> str:
    """Three columns: Front, Back, Tags -- Anki's default note type.

    The `#` header lines are Anki import directives, not comments: they let the
    file import with the right separator and HTML handling without the user
    touching the import dialog's settings.
    """
    header = "#separator:tab\n#html:true\n#tags column:3\n"
    rows = "\n".join(
        f"{_tsv_field(c.front)}\t{_tsv_field(c.back)}\t{tags}" for c in cards
    )
    return header + rows + ("\n" if rows else "")
