from pathlib import Path

from bro.rag.retrieval.store import VectorStore


def test_rag_ingest_and_search(tmp_path: Path):
    doc = tmp_path / "notes.md"
    doc.write_text(
        "We selected PostgreSQL because of JSONB support and reliability.\n"
        "Authentication uses JWT with short-lived access tokens.\n",
        encoding="utf-8",
    )
    store = VectorStore()
    n = store.ingest_path(doc)
    assert n >= 1
    hits = store.search("Why PostgreSQL?", k=3)
    assert hits
    assert hits[0].score > 0
    ctx = store.format_context("PostgreSQL JSONB")
    assert "PostgreSQL" in ctx or "JSONB" in ctx
