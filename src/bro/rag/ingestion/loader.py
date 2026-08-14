from __future__ import annotations

from pathlib import Path


SUPPORTED = {".txt", ".md", ".markdown", ".py", ".json", ".csv", ".log", ".rst"}


def load_text_file(path: Path) -> str:
    data = path.read_bytes()
    for enc in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def iter_documents(root: Path) -> list[tuple[str, str]]:
    """Return list of (source_id, text)."""
    root = root.expanduser().resolve()
    docs: list[tuple[str, str]] = []
    if root.is_file():
        if root.suffix.lower() in SUPPORTED or root.suffix == "":
            docs.append((str(root), load_text_file(root)))
        return docs
    if not root.is_dir():
        return docs
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        if p.suffix.lower() not in SUPPORTED:
            continue
        if any(part.startswith(".") for part in p.parts):
            continue
        try:
            docs.append((str(p), load_text_file(p)))
        except OSError:
            continue
    return docs
