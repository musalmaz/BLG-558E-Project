"""Retriever for the cross-user pilot: enterprise docs (M2-style, no canaries) + user memory / shared notes."""
from src.agent.retrieval import Retriever, RetrievedChunk
from src.multiuser.memory import UserMemory

MODES = ("X1_shared_weak", "X2_isolated", "X3_shared_summary")


class MultiUserRetriever(Retriever):
    """Context for user `current_user` (default B): enterprise top-k plus memory by mode.

    X1: memory search over ALL users' entries; X2: only the current user's entries;
    X3: the shared running notes (no per-user filtering possible).
    """

    def __init__(self, cfg: dict, memory: UserMemory, summaries: dict[str, str] | None = None,
                 current_user: str = "B", **kw):
        super().__init__(cfg, docs_per_topic=0, **kw)  # docs_per_topic=0 drops every canary doc
        self.memory, self.summaries = memory, summaries or {}
        self.current_user, self.current_model = current_user, ""
        self.mem_k = cfg["multiuser"]["memory_top_k"]

    def retrieve(self, message: str, mode: str) -> list[RetrievedChunk]:
        if mode not in MODES:
            raise ValueError(f"unknown multiuser mode {mode!r}; expected one of {MODES}")
        base = super().retrieve(message, "M2_strong")  # public+internal only, canaries excluded
        if mode == "X3_shared_summary":
            notes = self.summaries.get(self.current_model)
            extra = [RetrievedChunk(text=notes, doc_id="shared_notes", acl_label="customer_notes",
                                    is_canary=False, score=1.0)] if notes else []
        else:
            owner = None if mode == "X1_shared_weak" else self.current_user
            extra = [RetrievedChunk(text=e.text, doc_id=f"mem_{e.owner}_{e.topic_id}", acl_label="user_memory",
                                    is_canary=False, score=float(s))
                     for e, s in self.memory.search(message, self.mem_k, owner)]
        return base + extra
