from sidecar.markdown_assembly import dedupe_section, LINK_REMAINDER_RE

EXISTING = """# Lecture 2

## Vector Operations [00:00:20](url)

Scalar multiplication and dot products.
"""

def test_dedupe_section_returns_none_for_identical_heading_and_similar_body():
    new_section = "## Vector Operations [00:00:25](url)\n\nScalar multiplication, dot products."
    assert dedupe_section(EXISTING, new_section) is None


def test_dedupe_section_returns_section_when_genuinely_new():
    new_section = "## Eigenvalues [00:05:00](url)\n\nCharacteristic polynomial roots."
    assert dedupe_section(EXISTING, new_section) == new_section


def test_dedupe_section_same_heading_different_body_is_not_a_duplicate():
    # Same topic revisited later in the lecture with new content is legitimate.
    new_section = "## Vector Operations [00:32:00](url)\n\nRevisiting with a worked example on 500-asset portfolios."
    assert dedupe_section(EXISTING, new_section) == new_section


def test_dedupe_section_normalized_heading_with_case_and_punctuation_difference():
    # Heading case and trailing punctuation differences should still be detected as duplicates.
    # Existing: "Vector Operations", New: "vector operations:"
    existing_with_norm_heading = """# Lecture 2

## Vector Operations [00:00:20](url)

Scalar multiplication and dot products.
"""
    new_section = "## vector operations: [00:00:25](url)\n\nScalar multiplication and dot products."
    assert dedupe_section(existing_with_norm_heading, new_section) is None


def test_dedupe_section_url_with_internal_parentheses():
    # URLs with internal parentheses (like Wikipedia URLs) should not corrupt body extraction.
    existing_with_paren_url = """# Lecture 2

## Generics [00:01:15](https://en.wikipedia.org/wiki/Generics_(programming))

Parameterized types and type variables.
"""
    # New section with same heading and similar body, but different timestamp URL.
    # Should still be detected as duplicate even though URL has parens.
    new_section = "## Generics [00:01:30](https://example.com/generics)\n\nParameterized types and type variables."
    assert dedupe_section(existing_with_paren_url, new_section) is None


def test_dedupe_section_non_heading_section_returns_unchanged():
    # Non-`##` sections (e.g., TL;DR blocks) should pass through unchanged, never deduped.
    existing_with_markdown = """# Lecture 2

## Vector Operations [00:00:20](url)

Scalar multiplication and dot products.

> TL;DR: This is important
"""
    new_passthrough_section = "> TL;DR: This is also important"
    assert dedupe_section(existing_with_markdown, new_passthrough_section) == new_passthrough_section


def test_link_remainder_regex_simple_url():
    # Test that LINK_REMAINDER_RE correctly extracts body from simple timestamp+URL.
    input_text = "00:00:20](url)\n\nScalar multiplication and dot products."
    extracted = LINK_REMAINDER_RE.sub("", input_text, count=1).strip()
    assert extracted == "Scalar multiplication and dot products.", f"Got: {repr(extracted)}"


def test_link_remainder_regex_nested_parens_url():
    # Test that LINK_REMAINDER_RE correctly handles Wikipedia-style URLs with nested parens.
    input_text = "00:01:15](https://en.wikipedia.org/wiki/Generics_(programming))\n\nParameterized types and type variables."
    extracted = LINK_REMAINDER_RE.sub("", input_text, count=1).strip()
    assert extracted == "Parameterized types and type variables.", f"Got: {repr(extracted)}"


def test_dedupe_section_high_similarity_on_identical_content():
    # Verify that the similarity ratio for identical/near-identical sections is high (>= 0.95).
    # This prevents the bug where corruption happens to clear 0.8 threshold by luck.
    from difflib import SequenceMatcher

    existing_content = """# Lecture 2

## Vector Operations [00:00:20](url)

Scalar multiplication and dot products.
"""
    new_section = "## Vector Operations [00:00:25](url)\n\nScalar multiplication and dot products."

    # Should dedupe (return None), meaning similarity is >= BODY_SIMILARITY_THRESHOLD
    result = dedupe_section(existing_content, new_section)
    assert result is None, "Should detect as duplicate"

    # Verify the similarity is genuinely high (>= 0.95), not just barely clearing 0.8
    # by extracting bodies and computing similarity directly
    existing_body_raw = existing_content.split("\n", 2)[2].strip()  # Get body from existing
    # Simulate the extraction that happens inside dedupe_section
    existing_body_extracted = LINK_REMAINDER_RE.sub("", existing_body_raw, count=1).strip()

    new_body_raw = new_section.split("\n", 1)[1].strip()  # Get body from new section
    new_body_extracted = LINK_REMAINDER_RE.sub("", new_body_raw, count=1).strip() if "[" in new_section else new_body_raw

    similarity = SequenceMatcher(None, existing_body_extracted, new_body_extracted).ratio()
    assert similarity >= 0.95, f"Similarity should be >= 0.95, but got {similarity} (bodies: {repr(existing_body_extracted)} vs {repr(new_body_extracted)})"


def test_link_remainder_regex_documents_two_level_nesting_limitation():
    # This test documents the KNOWN LIMITATION of LINK_REMAINDER_RE: it correctly handles
    # zero or one level of nested parens (sufficient for YouTube URLs), but does NOT handle
    # two or more levels of nesting or unbalanced parens. This is a deliberate trade-off:
    # a general solution would require a balanced-paren scanner (overkill for this project).
    #
    # This test captures the CURRENT BEHAVIOR (not ideal, but non-crashing) for two-level nesting,
    # so if someone modifies the regex in the future, this test will catch unexpected behavior changes.

    input_text = "00:01:15](https://example.com/(a(b(c)d)e))\n\nBody text here."
    extracted = LINK_REMAINDER_RE.sub("", input_text, count=1).strip()

    # The regex cannot fully remove the URL because the two-level nesting overwhelms the pattern.
    # The actual behavior is that it leaves trailing garbage: "e))" + the body.
    # This is imperfect but acceptable given the project's real URL patterns (YouTube links).
    assert extracted == "e))\n\nBody text here.", f"Got: {repr(extracted)}"
