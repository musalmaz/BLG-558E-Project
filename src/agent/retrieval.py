"""ChromaDB retrieval with two ACL modes (M1_weak, M2_strong)."""
from dataclasses import dataclass

import chromadb
from sentence_transformers import SentenceTransformer

from src.config import load_config, resolve
from src.data_layer.build_index import COLLECTION

ALLOWED_M2 = ["public", "internal"]


@dataclass
class RetrievedChunk:
    """One retrieved chunk with its ACL metadata."""
    text: str
    doc_id: str
    acl_label: str
    is_canary: bool
    score: float


class Retriever:
    """Loads the collection and embedder once; retrieves per ACL mode."""

    def __init__(self, cfg: dict | None = None, collection=None, embedder=None):
        self.cfg = cfg or load_config()
        self.top_k = self.cfg["index"]["top_k"]
        self.modes = self.cfg["acl_modes"]
        if collection is None:
            client = chromadb.PersistentClient(path=str(resolve(self.cfg["index"]["chroma_dir"])))
            collection = client.get_collection(COLLECTION)
        self.col = collection
        self.embedder = embedder or SentenceTransformer(self.cfg["index"]["embedding_model"])

    def retrieve(self, message: str, mode: str) -> list[RetrievedChunk]:
        """Top-k chunks; M2_strong filters confidential at retrieval time."""
        if mode not in self.modes:
            raise ValueError(f"unknown acl mode {mode!r}; expected one of {self.modes}")
        where = {"acl_label": {"$in": ALLOWED_M2}} if mode == "M2_strong" else None
        emb = self.embedder.encode([message], normalize_embeddings=True).tolist()
        res = self.col.query(query_embeddings=emb, n_results=self.top_k, where=where)
        return [
            RetrievedChunk(text=t, doc_id=m["doc_id"], acl_label=m["acl_label"],
                           is_canary=bool(m["is_canary"]), score=1.0 - d)
            for t, m, d in zip(res["documents"][0], res["metadatas"][0], res["distances"][0])
        ]
