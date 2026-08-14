from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from bro.rag.embeddings.simple import HashingEmbedder, cosine
from bro.rag.ingestion.chunker import Chunk, chunk_text
from bro.rag.ingestion.loader import iter_documents


@dataclass
class RetrievedChunk:
    source: str
    text: str
    score: float


@dataclass
class VectorStore:
    embedder: HashingEmbedder = field(default_factory=HashingEmbedder)
    chunks: list[Chunk] = field(default_factory=list)
    vectors: list[list[float]] = field(default_factory=list)

    def clear(self) -> None:
        self.chunks.clear()
        self.vectors.clear()

    def ingest_path(self, path: str | Path) -> int:
        docs = iter_documents(Path(path))
        added = 0
        for source, text in docs:
            for ch in chunk_text(source, text):
                self.chunks.append(ch)
                self.vectors.append(self.embedder.embed(ch.text))
                added += 1
        return added

    def search(self, query: str, k: int = 5) -> list[RetrievedChunk]:
        if not self.chunks:
            return []
        qv = self.embedder.embed(query)
        scored: list[tuple[float, int]] = []
        for i, vec in enumerate(self.vectors):
            scored.append((cosine(qv, vec), i))
        scored.sort(reverse=True, key=lambda x: x[0])
        out: list[RetrievedChunk] = []
        for score, i in scored[:k]:
            if score <= 0:
                continue
            ch = self.chunks[i]
            out.append(RetrievedChunk(source=ch.source, text=ch.text, score=score))
        return out

    def format_context(self, query: str, k: int = 5, max_chars: int = 3500) -> str:
        hits = self.search(query, k=k)
        if not hits:
            return ""
        parts: list[str] = []
        total = 0
        for h in hits:
            block = f"[source: {h.source} · score={h.score:.3f}]\n{h.text}"
            if total + len(block) > max_chars:
                break
            parts.append(block)
            total += len(block)
        return "\n\n".join(parts)

    def __len__(self) -> int:
        return len(self.chunks)
