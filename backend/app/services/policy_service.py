"""Serves the Markdown policy documents in docs/policies (single source for the help page and RAG)."""
from app.config import PROJECT_ROOT
from app.utils.errors import NotFoundError

POLICY_DIR = PROJECT_ROOT / "docs" / "policies"


def _title(text: str, fallback: str) -> str:
    return next((line[2:].strip() for line in text.splitlines() if line.startswith("# ")), fallback)


def list_policies() -> list[dict]:
    return [
        {"slug": path.stem, "title": _title(path.read_text(encoding="utf-8"), path.stem)}
        for path in sorted(POLICY_DIR.glob("*.md"))
        if path.stem != "README"
    ]


def get_policy(slug: str) -> dict:
    path = POLICY_DIR / f"{slug}.md"
    if not slug.replace("-", "").isalnum() or not path.is_file():
        raise NotFoundError(f"Policy {slug} not found.")
    text = path.read_text(encoding="utf-8")
    return {"slug": slug, "title": _title(text, slug), "content": text}
