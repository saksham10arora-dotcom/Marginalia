from sidecar.anki_export import (
    Flashcard,
    build_flashcard_prompt,
    cards_to_tsv,
    parse_flashcards,
    strip_note_chrome,
)


def test_strip_note_chrome_removes_frontmatter():
    src = '---\ntitle: "Lec 1"\nsource: url\n---\n\nReal content.\n'
    assert strip_note_chrome(src) == "Real content."


def test_strip_note_chrome_removes_screenshot_markers():
    src = "A fact. <!-- screenshot: 00:02:00 --> Another fact."
    assert "screenshot" not in strip_note_chrome(src)


def test_strip_note_chrome_removes_image_embeds():
    src = "Before ![diagram](images/a.jpg) after"
    out = strip_note_chrome(src)
    assert "![" not in out and "images/a.jpg" not in out


def test_build_flashcard_prompt_includes_notes_and_title():
    prompt = build_flashcard_prompt("- **Eigenvalue** is a scalar.", "Linear Algebra 1")
    assert "Linear Algebra 1" in prompt
    assert "Eigenvalue" in prompt
    assert "Q:" in prompt and "A:" in prompt  # states the output contract


def test_parse_flashcards_reads_multiple_cards():
    raw = "Q: What is an eigenvalue?\nA: A scalar $\\lambda$ where $Av = \\lambda v$.\n---\nQ: What is a scalar?\nA: A single number."
    cards = parse_flashcards(raw)
    assert len(cards) == 2
    assert cards[0].front == "What is an eigenvalue?"
    assert cards[0].back == "A scalar $\\lambda$ where $Av = \\lambda v$."
    assert cards[1].front == "What is a scalar?"


def test_parse_flashcards_tolerates_code_fences_and_preamble():
    raw = "Here are your cards:\n\n```\nQ: What is a vector?\nA: An ordered list of numbers.\n```"
    cards = parse_flashcards(raw)
    assert len(cards) == 1
    assert cards[0].front == "What is a vector?"


def test_parse_flashcards_keeps_multiline_answers():
    raw = "Q: Name the three views.\nA: Physics: arrows.\nCS: lists.\nMath: abstract."
    cards = parse_flashcards(raw)
    assert len(cards) == 1
    assert "CS: lists." in cards[0].back


def test_parse_flashcards_skips_blocks_missing_a_side():
    raw = "Q: Dangling question with no answer\n---\nQ: Real one?\nA: Real answer."
    cards = parse_flashcards(raw)
    assert len(cards) == 1
    assert cards[0].front == "Real one?"


def test_parse_flashcards_returns_empty_on_garbage():
    assert parse_flashcards("I could not generate any cards.") == []


def test_cards_to_tsv_emits_anki_import_headers():
    tsv = cards_to_tsv([Flashcard("Front?", "Back.")])
    assert tsv.startswith("#separator:tab\n#html:true\n#tags column:3\n")


def test_cards_to_tsv_writes_three_tab_separated_columns():
    tsv = cards_to_tsv([Flashcard("Front?", "Back.")], tags="stat110")
    row = tsv.strip().split("\n")[-1]
    assert row.split("\t") == ["Front?", "Back.", "stat110"]


def test_cards_to_tsv_converts_newlines_to_br_so_fields_survive_import():
    tsv = cards_to_tsv([Flashcard("Q?", "line one\nline two")])
    row = tsv.strip().split("\n")[-1]
    assert row.split("\t")[1] == "line one<br>line two"


def test_cards_to_tsv_strips_tabs_that_would_break_the_column_count():
    tsv = cards_to_tsv([Flashcard("a\tb", "c\td")])
    row = tsv.strip().split("\n")[-1]
    assert len(row.split("\t")) == 3


def test_cards_to_tsv_handles_an_empty_deck():
    tsv = cards_to_tsv([])
    assert tsv.startswith("#separator:tab")
    assert "\t" not in tsv.split("#tags column:3\n")[1]
