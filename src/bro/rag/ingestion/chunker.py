from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Chunk:
    id: str
    source: str
    text: str
    index: int


def chunk_text(source: str, text: str, size: int = 800, overlap: int = 120) -> list[Chunk]:
    text = text.strip()
    if not text:
        return []
    chunks: list[Chunk] = []
    i = 0
    idx = 0
    n = len(text)
    while i < n:
        end = min(n, i + size)
        # prefer break on newline
        if end < n:
            nl = text.rfind("\n", i + size // 2, end)
            if nl > i:
                end = nl
        piece = text[i:end].strip()
        if piece:
            chunks.append(Chunk(id=f"{source}::{idx}", source=source, text=piece, index=idx))
            idx += 1
        if end >= n:
            break
        i = max(end - overlap, i + 1)
    return chunks
