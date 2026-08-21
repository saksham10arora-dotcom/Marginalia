from sidecar.vault_linker import add_wikilinks, collect_note_titles, link_note_to_vault


def _write(vault, name, title=None, body="body text"):
    path = vault / name
    path.parent.mkdir(parents=True, exist_ok=True)
    fm = f'---\ntitle: "{title}"\n---\n\n' if title else ""
    path.write_text(f"{fm}{body}\n")
    return path


def test_collect_note_titles_reads_frontmatter_title(tmp_path):
    _write(tmp_path, "lec1.md", title="Eigenvalues and Eigenvectors")
    assert collect_note_titles(tmp_path) == ["Eigenvalues and Eigenvectors"]


def test_collect_note_titles_falls_back_to_filename_when_no_frontmatter(tmp_path):
    _write(tmp_path, "linear-algebra.md")
    assert collect_note_titles(tmp_path) == ["linear algebra"]


def test_collect_note_titles_skips_titles_below_min_length(tmp_path):
    _write(tmp_path, "set.md", title="Set")
    assert collect_note_titles(tmp_path) == []


def test_collect_note_titles_excludes_the_note_being_written(tmp_path):
    _write(tmp_path, "lec1.md", title="Eigenvalues")
    _write(tmp_path, "sub/lec2.md", title="Determinants")
    titles = collect_note_titles(tmp_path, exclude_filename="sub/lec2.md")
    assert titles == ["Eigenvalues"]


def test_collect_note_titles_returns_longest_first(tmp_path):
    _write(tmp_path, "a.md", title="Algebra")
    _write(tmp_path, "b.md", title="Linear Algebra")
    assert collect_note_titles(tmp_path)[0] == "Linear Algebra"


def test_add_wikilinks_links_a_matching_title():
    out = add_wikilinks("We now discuss Eigenvalues at length.", ["Eigenvalues"])
    assert "[[Eigenvalues]]" in out


def test_add_wikilinks_links_only_the_first_occurrence():
    out = add_wikilinks("Eigenvalues matter. Eigenvalues again.", ["Eigenvalues"])
    assert out.count("[[Eigenvalues]]") == 1
    assert out.endswith("Eigenvalues again.")


def test_add_wikilinks_preserves_prose_casing_with_an_alias():
    out = add_wikilinks("the eigenvalues are real", ["Eigenvalues"])
    assert "[[Eigenvalues|eigenvalues]]" in out


def test_add_wikilinks_matches_whole_words_only():
    # "Vector" must not match inside "Vectorization".
    out = add_wikilinks("Vectorization is unrelated.", ["Vector"])
    assert "[[" not in out


def test_add_wikilinks_leaves_inline_math_untouched():
    out = add_wikilinks("Given $Eigenvalues > 0$ we proceed.", ["Eigenvalues"])
    assert "$Eigenvalues > 0$" in out
    assert "[[" not in out


def test_add_wikilinks_leaves_display_math_untouched():
    src = "Result:\n\n$$\\text{Eigenvalues} = \\lambda$$\n"
    assert add_wikilinks(src, ["Eigenvalues"]) == src


def test_add_wikilinks_leaves_fenced_code_untouched():
    src = "Example:\n\n```python\nEigenvalues = compute()\n```\n"
    assert add_wikilinks(src, ["Eigenvalues"]) == src


def test_add_wikilinks_leaves_inline_code_untouched():
    src = "Call `Eigenvalues()` directly."
    assert add_wikilinks(src, ["Eigenvalues"]) == src


def test_add_wikilinks_does_not_double_link_an_existing_wikilink():
    src = "See [[Eigenvalues]] for detail."
    assert add_wikilinks(src, ["Eigenvalues"]) == src


def test_add_wikilinks_leaves_markdown_link_text_untouched():
    src = "See [Eigenvalues](https://example.com) for detail."
    assert add_wikilinks(src, ["Eigenvalues"]) == src


def test_add_wikilinks_leaves_headings_untouched():
    src = "## Eigenvalues [00:01:00](url)\n\nSome body.\n"
    assert add_wikilinks(src, ["Eigenvalues"]) == src


def test_add_wikilinks_leaves_frontmatter_untouched():
    src = '---\ntitle: "Eigenvalues"\n---\n\nBody mentions nothing else.\n'
    assert add_wikilinks(src, ["Eigenvalues"]) == src


def test_add_wikilinks_leaves_screenshot_markers_untouched():
    src = "Text <!-- screenshot: 00:02:00 --> more text."
    assert add_wikilinks(src, ["screenshot"]) == src


def test_add_wikilinks_prefers_the_longer_title_on_overlap():
    out = add_wikilinks("We study linear algebra today.", ["Linear Algebra", "Algebra"])
    assert "[[Linear Algebra|linear algebra]]" in out
    assert "[[Algebra" not in out


def test_add_wikilinks_respects_max_links():
    out = add_wikilinks("Eigenvalues and Determinants both.", ["Eigenvalues", "Determinants"], max_links=1)
    assert out.count("[[") == 1


def test_add_wikilinks_handles_regex_metacharacters_in_a_title():
    # A real vault has notes like "C++ (Part 1)" -- must not blow up the pattern.
    out = add_wikilinks("Today: C++ (Part 1) recap.", ["C++ (Part 1)"])
    assert "[[C++ (Part 1)]]" in out


def test_add_wikilinks_is_a_noop_with_no_titles():
    src = "Nothing to link here."
    assert add_wikilinks(src, []) == src


def test_link_note_to_vault_links_against_real_vault_files(tmp_path):
    _write(tmp_path, "eigen.md", title="Eigenvalues")
    out = link_note_to_vault("Today we cover eigenvalues.", tmp_path, exclude_filename="new.md")
    assert "[[Eigenvalues|eigenvalues]]" in out


def test_already_linked_titles_reads_plain_and_aliased_links():
    from sidecar.vault_linker import already_linked_titles
    content = "See [[Eigenvalues]] and [[Linear Algebra|linear algebra]] here."
    assert already_linked_titles(content) == {"Eigenvalues", "Linear Algebra"}


def test_link_note_to_vault_skips_titles_the_note_already_links(tmp_path):
    _write(tmp_path, "eigen.md", title="Eigenvalues")
    out = link_note_to_vault(
        "More on eigenvalues today.",
        tmp_path,
        existing_content="Earlier we saw [[Eigenvalues]].",
    )
    assert "[[" not in out


# --- aliases: the mechanism that makes linking actually fire on a real vault,
# where note titles are full lecture titles nobody writes in prose ---

def test_collect_link_targets_reads_block_style_aliases(tmp_path):
    from sidecar.vault_linker import collect_link_targets
    (tmp_path / "lec4.md").write_text(
        '---\ntitle: "Lecture 4: Linear Algebra (cont.)"\n'
        "aliases:\n  - linear algebra\n  - linalg\n---\n\nbody\n"
    )
    targets = dict(collect_link_targets(tmp_path))
    assert targets["linear algebra"] == "Lecture 4: Linear Algebra (cont.)"
    assert targets["linalg"] == "Lecture 4: Linear Algebra (cont.)"


def test_collect_link_targets_reads_inline_style_aliases(tmp_path):
    from sidecar.vault_linker import collect_link_targets
    (tmp_path / "lec4.md").write_text(
        '---\ntitle: "Lecture 4"\naliases: [eigenvalues, eigenvectors]\n---\n\nbody\n'
    )
    targets = dict(collect_link_targets(tmp_path))
    assert targets["eigenvalues"] == "Lecture 4"


def test_alias_match_links_to_the_real_note_title(tmp_path):
    (tmp_path / "lec4.md").write_text(
        '---\ntitle: "Lecture 4: Linear Algebra (cont.)"\naliases:\n  - linear algebra\n---\n\nbody\n'
    )
    out = link_note_to_vault("Today we cover linear algebra basics.", tmp_path)
    assert "[[Lecture 4: Linear Algebra (cont.)|linear algebra]]" in out


def test_only_one_edge_per_note_even_when_several_aliases_match(tmp_path):
    (tmp_path / "lec4.md").write_text(
        '---\ntitle: "Lecture 4"\naliases:\n  - linear algebra\n  - eigenvalues\n---\n\nbody\n'
    )
    out = link_note_to_vault("We study linear algebra and eigenvalues.", tmp_path)
    assert out.count("[[") == 1


def test_add_wikilinks_still_accepts_a_plain_phrase_list():
    out = add_wikilinks("We discuss Eigenvalues here.", ["Eigenvalues"])
    assert "[[Eigenvalues]]" in out
