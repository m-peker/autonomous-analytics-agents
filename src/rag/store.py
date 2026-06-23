"""ChromaDB-backed knowledge base with semantic search and RAG Q&A."""
from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings

from config.settings import settings

logger = logging.getLogger(__name__)


class KnowledgeBase:
    """Vector store for documents and web-scraped content.

    Uses sentence-transformers for embeddings and ChromaDB for persistence.
    OpenAI embeddings are used when available (text-embedding-3-small).
    """

    def __init__(self) -> None:
        persist_dir = str(settings.chroma_persist_dir)
        Path(persist_dir).mkdir(parents=True, exist_ok=True)

        self._client = chromadb.PersistentClient(
            path=persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name="research_docs",
            metadata={"hnsw:space": "cosine"},
        )
        self._embed_fn = self._get_embedding_fn()

    def _get_embedding_fn(self):
        """Return an embedding function: OpenAI if configured, else SentenceTransformers."""
        if settings.openai_api_key:
            from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
            return OpenAIEmbeddingFunction(
                api_key=settings.openai_api_key,
                model_name=settings.embedding_model,
            )
        from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
        return SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")

    # ── Indexing ─────────────────────────────────────────────────────────

    def index_text(self, text: str, source: str = "", metadata: dict | None = None) -> int:
        """Chunk and index a text document. Returns number of chunks."""
        chunks = self._chunk_text(text)
        if not chunks:
            return 0

        ids = [str(uuid.uuid4()) for _ in chunks]
        metadatas = [{"source": source, "chunk_idx": i, **(metadata or {})}
                     for i in range(len(chunks))]

        self._collection.add(documents=chunks, ids=ids, metadatas=metadatas)
        logger.info("Indexed %d chunks from %r", len(chunks), source)
        return len(chunks)

    def index_dataframe(self, df, source: str = "") -> int:
        """Convert DataFrame rows to text and index."""
        import io
        buf = io.StringIO()
        df.head(200).to_string(buf, index=False)
        return self.index_text(buf.getvalue(), source=source)

    # ── Search ───────────────────────────────────────────────────────────

    def search(self, query: str, top_k: int | None = None) -> list[dict[str, Any]]:
        k = top_k or settings.top_k_retrieval
        try:
            results = self._collection.query(query_texts=[query], n_results=k)
            return [
                {"source": m.get("source", ""), "text": d, "relevance": round(1 - dist, 4)
                 if dist is not None else None}
                for d, m, dist in zip(results["documents"][0],
                                      results["metadatas"][0],
                                      results.get("distances", [[]])[0])
            ]
        except Exception as exc:
            logger.warning("Search error: %s", exc)
            return []

    # ── RAG Q&A ──────────────────────────────────────────────────────────

    def ask(self, question: str, model: str | None = None) -> dict[str, Any]:
        """Answer a question using RAG over indexed documents."""
        sources = self.search(question)

        if not sources:
            return {"answer": "No relevant documents found in the knowledge base. "
                              "Run an analysis first to populate it.", "sources": []}

        context = "\n\n---\n\n".join(s["text"][:1500] for s in sources[:3])

        from src.llm.factory import llm
        prompt = (
            "You are a precise research analyst. Answer the question using ONLY the "
            "provided context. If the context doesn't contain the answer, say so.\n\n"
            f"CONTEXT:\n{context}\n\n"
            f"QUESTION: {question}\n\n"
            "ANSWER (concise, cite sources if possible):"
        )

        resp = llm.generate(prompt, system="You are an expert research analyst. "
                             "Answer based solely on the provided context.")
        return {"answer": resp.content, "sources": sources, "model_used": resp.model}

    # ── Helpers ──────────────────────────────────────────────────────────

    def _chunk_text(self, text: str) -> list[str]:
        """Split text into overlapping chunks."""
        chunk_size = settings.chunk_size
        overlap = settings.chunk_overlap

        if len(text) <= chunk_size:
            return [text]

        chunks = []
        start = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunks.append(text[start:end])
            start += chunk_size - overlap
        return chunks

    def count(self) -> int:
        return self._collection.count()

    def clear(self) -> None:
        self._client.delete_collection("research_docs")
        self._collection = self._client.get_or_create_collection(
            name="research_docs",
            metadata={"hnsw:space": "cosine"},
        )
