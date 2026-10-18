"""ChromaDB retrieval with two ACL modes (M1_weak, M2_strong)."""
import json
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


def excluded_canary_ids(cfg: dict, docs_per_topic: int | None) -> list[str]:
    """Canary doc ids beyond the first `docs_per_topic` of each topic (ratio sweep); [] if None."""
    if docs_per_topic is None:
        return []
    f = json.loads((resolve(cfg["data"]["canaries_dir"]) / "canaries.json").read_text(encoding="utf-8"))
    return [d for c in f["canaries"] for d in c["doc_ids"][docs_per_topic:]]


class Retriever:
    """Loads the collection and embedder once; retrieves per ACL mode."""

    def __init__(self, cfg: dict | None = None, collection=None, embedder=None,
                 docs_per_topic: int | None = None):
        self.cfg = cfg or load_config()
        self.exclude_ids = excluded_canary_ids(self.cfg, docs_per_topic)
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
        conds = []
        if mode == "M2_strong":
            conds.append({"acl_label": {"$in": ALLOWED_M2}})
        if self.exclude_ids:
            conds.append({"doc_id": {"$nin": self.exclude_ids}})
        where = None if not conds else conds[0] if len(conds) == 1 else {"$and": conds}
        emb = self.embedder.encode([message], normalize_embeddings=True).tolist()
        res = self.col.query(query_embeddings=emb, n_results=self.top_k, where=where)
        return [
            RetrievedChunk(text=t, doc_id=m["doc_id"], acl_label=m["acl_label"],
                           is_canary=bool(m["is_canary"]), score=1.0 - d)
            for t, m, d in zip(res["documents"][0], res["metadatas"][0], res["distances"][0])
        ]
