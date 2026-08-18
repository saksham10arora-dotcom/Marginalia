import pytest
import re
import yaml
from datetime import date
from pathlib import Path
from sidecar.vault_writer import sanitize_filename, ensure_unique_filename, build_frontmatter, create_note, append_section, list_documents, search_documents

def test_sanitize_filename_strips_forbidden_chars():
    assert sanitize_filename('Lecture 2: Linear Algebra #1 [Draft]') == \
        "lecture-2-linear-algebra-1-draft"

def test_sanitize_filename_collapses_whitespace_and_dashes():
    assert sanitize_filename("  Overflow,  Precision   Errors  ") == \
        "overflow-precision-errors"

def test_sanitize_filename_falls_back_to_untitled_for_non_ascii_title():
    assert sanitize_filename("線形代数") == "untitled"

def test_ensure_unique_filename_returns_input_when_free(tmp_path):
    assert ensure_unique_filename(tmp_path, "lec2-linear-algebra.md") == \
        "lec2-linear-algebra.md"

def test_ensure_unique_filename_appends_counter_on_collision(tmp_path):
    (tmp_path / "lec2-linear-algebra.md").write_text("existing")
    assert ensure_unique_filename(tmp_path, "lec2-linear-algebra.md") == \
        "lec2-linear-algebra-1.md"

def test_ensure_unique_filename_increments_past_multiple_collisions(tmp_path):
    (tmp_path / "lec2-linear-algebra.md").write_text("existing")
    (tmp_path / "lec2-linear-algebra-1.md").write_text("existing")
    assert ensure_unique_filename(tmp_path, "lec2-linear-algebra.md") == \
        "lec2-linear-algebra-2.md"


SAMPLE_META = {
    "title": "Lecture 2: Linear Algebra",
    "source": "https://www.youtube.com/watch?v=0uimNNIuUyY",
    "author": "MIT OpenCourseWare",
    "duration_sec": 4876,
    "tags": ["mit-18642", "quant"],
}


def test_build_frontmatter_includes_required_fields():
    fm = build_frontmatter(SAMPLE_META)
    # Title should be present with proper quoting (YAML uses single quotes for safe strings)
    assert "title:" in fm and "Lecture 2: Linear Algebra" in fm
    assert "source: https://www.youtube.com/watch?v=0uimNNIuUyY" in fm
    assert "generated_by: marginalia" in fm
    assert "engine: claude-haiku-4-5-20251001" in fm
    assert f'created: "{date.today().isoformat()}"' in fm


def test_build_frontmatter_uses_provided_engine_over_default():
    meta = {**SAMPLE_META, "engine": "gemini-3.5-flash"}
    fm = build_frontmatter(meta)
    assert "engine: gemini-3.5-flash" in fm
    assert "claude-haiku-4-5-20251001" not in fm


def test_build_frontmatter_always_includes_base_tags_plus_extras():
    fm = build_frontmatter(SAMPLE_META)
    assert "- marginalia" in fm
    assert "- youtube" in fm
    assert "- mit-18642" in fm
    assert "- quant" in fm


def test_build_frontmatter_defaults_tags_to_empty_list():
    meta = {**SAMPLE_META, "tags": []}
    fm = build_frontmatter(meta)
    assert "- marginalia" in fm
    assert "- youtube" in fm


def test_build_frontmatter_escapes_title_with_embedded_quotes():
    """Regression test: titles containing double quotes must round-trip through YAML."""
    title_with_quotes = 'The "Best" Algorithm Explained'
    author_with_colon = "Smith: The Expert"
    meta = {
        "title": title_with_quotes,
        "source": "https://example.com",
        "author": author_with_colon,
        "duration_sec": 1200,
        "tags": [],
    }
    fm = build_frontmatter(meta)

    # Extract the YAML block (between --- delimiters)
    lines = fm.split('\n')
    assert lines[0] == '---'
    yaml_lines = []
    end_idx = None
    for i, line in enumerate(lines[1:], 1):
        if line == '---':
            end_idx = i
            break
        yaml_lines.append(line)

    # Rebuild YAML from the extracted lines and parse it
    yaml_content = '\n'.join(yaml_lines)
    parsed = yaml.safe_load(yaml_content)

    # Verify title and author round-trip correctly
    assert parsed["title"] == title_with_quotes
    assert parsed["author"] == author_with_colon


def test_create_note_writes_file_with_frontmatter_and_title_heading(tmp_path):
    note_path = create_note(tmp_path, SAMPLE_META)
    assert note_path == tmp_path / "lecture-2-linear-algebra.md"
    content = note_path.read_text()
    assert content.startswith("---\n")
    assert "# Lecture 2: Linear Algebra" in content


def test_create_note_avoids_filename_collision(tmp_path):
    (tmp_path / "lecture-2-linear-algebra.md").write_text("existing note")
    note_path = create_note(tmp_path, SAMPLE_META)
    assert note_path == tmp_path / "lecture-2-linear-algebra-1.md"


def test_append_section_adds_content_with_blank_line_separator(tmp_path):
    note_path = tmp_path / "note.md"
    note_path.write_text("# Title\n\nExisting content.")
    append_section(note_path, "## New Section\n\nNew content.")
    result = note_path.read_text()
    assert result == "# Title\n\nExisting content.\n\n## New Section\n\nNew content."


def _write_note(vault_path, filename, title, source, created):
    (vault_path / filename).write_text(
        f'---\ntitle: "{title}"\nsource: {source}\ncreated: "{created}"\n---\n\n# {title}\n'
    )


def test_list_documents_returns_all_md_files_with_parsed_frontmatter(tmp_path):
    _write_note(tmp_path, "lec1.md", "Lecture 1", "https://youtube.com/watch?v=a", "2026-07-27")
    _write_note(tmp_path, "lec2.md", "Lecture 2", "https://youtube.com/watch?v=b", "2026-07-15")
    docs = list_documents(tmp_path)
    assert len(docs) == 2
    assert {"filename": "lec1.md", "title": "Lecture 1",
            "source": "https://youtube.com/watch?v=a", "created": "2026-07-27"} in docs


def test_list_documents_sorted_newest_first(tmp_path):
    _write_note(tmp_path, "old.md", "Old", "https://youtube.com/watch?v=a", "2026-06-01")
    _write_note(tmp_path, "new.md", "New", "https://youtube.com/watch?v=b", "2026-08-01")
    docs = list_documents(tmp_path)
    assert [d["filename"] for d in docs] == ["new.md", "old.md"]


def test_list_documents_skips_files_without_frontmatter(tmp_path):
    (tmp_path / "no-frontmatter.md").write_text("just some text, no frontmatter block")
    _write_note(tmp_path, "lec1.md", "Lecture 1", "https://youtube.com/watch?v=a", "2026-07-27")
    docs = list_documents(tmp_path)
    assert len(docs) == 1
    assert docs[0]["filename"] == "lec1.md"


def test_search_documents_matches_title_case_insensitive(tmp_path):
    _write_note(tmp_path, "lec1.md", "Linear Algebra", "https://youtube.com/watch?v=a", "2026-07-27")
    _write_note(tmp_path, "lec2.md", "Bond Mathematics", "https://youtube.com/watch?v=b", "2026-07-15")
    results = search_documents(tmp_path, "linear")
    assert len(results) == 1
    assert results[0]["title"] == "Linear Algebra"


def test_search_documents_empty_query_returns_all(tmp_path):
    _write_note(tmp_path, "lec1.md", "Linear Algebra", "https://youtube.com/watch?v=a", "2026-07-27")
    assert len(search_documents(tmp_path, "")) == 1


def test_list_documents_returns_vault_relative_path_for_subdirectory_note(tmp_path):
    """Regression test: a note nested in a vault subdirectory must come back
    with a filename that, joined onto vault_path, resolves to a real file
    (a bare basename silently drops the subdirectory and breaks downstream
    `vault_path / filename` lookups in main.py's note_chunk)."""
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    _write_note(subdir, "note.md", "Nested Note", "https://youtube.com/watch?v=nested", "2026-08-01")

    docs = list_documents(tmp_path)

    assert len(docs) == 1
    result = docs[0]
    assert (tmp_path / result["filename"]).exists()
    assert result["filename"] == "subdir/note.md"


def test_list_documents_robust_to_mixed_str_and_date_created_values(tmp_path):
    """Regression test: list_documents must not crash when frontmatter has unquoted ISO dates (parsed as datetime.date) mixed with quoted dates (str)."""
    # Write note with unquoted date (YAML parses as datetime.date object)
    (tmp_path / "unquoted-date.md").write_text(
        "---\ntitle: \"Unquoted Date Note\"\nsource: https://example.com\ncreated: 2026-07-27\n---\n\n# Unquoted Date Note\n"
    )
    # Write note with quoted date (YAML parses as str)
    (tmp_path / "quoted-date.md").write_text(
        '---\ntitle: "Quoted Date Note"\nsource: https://example.com\ncreated: "2026-06-01"\n---\n\n# Quoted Date Note\n'
    )

    # This should not raise TypeError when sorting mixed str/date values
    docs = list_documents(tmp_path)

    # Verify both notes are returned
    assert len(docs) == 2
    titles = {d["title"] for d in docs}
    assert titles == {"Unquoted Date Note", "Quoted Date Note"}

    # Verify correct sort order (newest first)
    # "2026-07-27" > "2026-06-01", so unquoted date note should be first
    assert docs[0]["title"] == "Unquoted Date Note"
    assert docs[1]["title"] == "Quoted Date Note"
