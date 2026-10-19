"""Defense 2: the agent answering an external sender only sees public sources."""
from src.agent.retrieval import Retriever, RetrievedChunk


class ScopedRetriever(Retriever):
    """Retriever whose context is restricted to `public` chunks in every ACL mode."""

    def retrieve(self, message: str, mode: str) -> list[RetrievedChunk]:
        if mode not in self.modes:
            raise ValueError(f"unknown acl mode {mode!r}; expected one of {self.modes}")
        emb = self.embedder.encode([message], normalize_embeddings=True).tolist()
        res = self.col.query(query_embeddings=emb, n_results=self.top_k, where={"acl_label": "public"})
        return [
            RetrievedChunk(text=t, doc_id=m["doc_id"], acl_label=m["acl_label"],
                           is_canary=bool(m["is_canary"]), score=1.0 - d)
            for t, m, d in zip(res["documents"][0], res["metadatas"][0], res["distances"][0])
        ]
