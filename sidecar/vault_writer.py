import re
import yaml
from pathlib import Path
from datetime import date


def sanitize_filename(title: str) -> str:
    """Obsidian-safe, URL-safe slug: lowercase, hyphen-separated, no `# | ^ [ ]`."""
    stripped = re.sub(r"[#|^\[\]]", "", title)
    slug = re.sub(r"[^a-z0-9]+", "-", stripped.lower()).strip("-")
    return slug or "untitled"


def ensure_unique_filename(vault_path: Path, filename: str) -> str:
    """If `filename` exists in vault_path, append -1, -2, ... until free."""
    candidate = vault_path / filename
    if not candidate.exists():
        return filename

    stem = candidate.stem
    suffix = candidate.suffix
    counter = 1
    while True:
        candidate = vault_path / f"{stem}-{counter}{suffix}"
        if not candidate.exists():
            return candidate.name
        counter += 1


BASE_TAGS = ["margin", "youtube"]


def build_frontmatter(meta: dict) -> str:
    """Build YAML frontmatter from metadata dict."""
    tags = BASE_TAGS + [t for t in meta.get("tags", []) if t not in BASE_TAGS]
    tag_lines = "\n".join(f"  - {t}" for t in tags)

    # Use yaml.safe_dump to properly escape title and author strings
    title_dumped = yaml.safe_dump({"title": meta["title"]}, default_flow_style=False).split(": ", 1)[1].rstrip("\n")
    author_dumped = yaml.safe_dump({"author": meta["author"]}, default_flow_style=False).split(": ", 1)[1].rstrip("\n")

    return (
        "---\n"
        f"title: {title_dumped}\n"
        f"source: {meta['source']}\n"
        f"author: {author_dumped}\n"
        f'created: "{date.today().isoformat()}"\n'
        f"duration_sec: {meta['duration_sec']}\n"
        "generated_by: margin\n"
        f"engine: {meta.get('engine', 'claude-haiku-4-5-20251001')}\n"
        f"tags:\n{tag_lines}\n"
        "---\n"
    )


def create_note(vault_path: Path, meta: dict) -> Path:
    """Create a new note file with frontmatter and title heading."""
    filename = ensure_unique_filename(vault_path, sanitize_filename(meta["title"]) + ".md")
    note_path = vault_path / filename
    frontmatter = build_frontmatter(meta)
    body = f'\n# {meta["title"]}\n'
    note_path.write_text(frontmatter + body)
    return note_path


def append_section(note_path: Path, section_markdown: str) -> None:
    """Append a section to an existing note with blank line separator."""
    existing = note_path.read_text()
    note_path.write_text(existing.rstrip("\n") + "\n\n" + section_markdown)


def parse_frontmatter(md_text: str) -> dict | None:
    if not md_text.startswith("---\n"):
        return None
    end = md_text.find("\n---", 4)
    if end == -1:
        return None
    try:
        return yaml.safe_load(md_text[4:end])
    except yaml.YAMLError:
        return None


def list_documents(vault_path: Path) -> list[dict]:
    docs = []
    for md_file in vault_path.rglob("*.md"):
        fm = parse_frontmatter(md_file.read_text())
        if not fm or "title" not in fm:
            continue
        docs.append({
            "filename": md_file.relative_to(vault_path).as_posix(),
            "title": fm.get("title", md_file.stem),
            "source": fm.get("source", ""),
            "created": fm.get("created", ""),
        })
    docs.sort(key=lambda d: str(d["created"]), reverse=True)
    return docs


def search_documents(vault_path: Path, query: str) -> list[dict]:
    docs = list_documents(vault_path)
    if not query:
        return docs
    query_lower = query.lower()
    return [d for d in docs if query_lower in d["title"].lower()]
