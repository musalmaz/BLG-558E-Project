"""Per-user conversation memory and a shared running summary (cross-user leakage pilot)."""
import json
from dataclasses import dataclass

import litellm
import numpy as np

from src.config import resolve

SUMMARY_PROMPT = (
    "You maintain internal customer notes for a support team. Current notes:\n{notes}\n\n"
    "A customer just wrote:\n{message}\n\n"
    "Rewrite the notes as a short bullet list (one bullet per customer message, at most 25 words per "
    "bullet) including this new message. Reply with the notes only."
)


@dataclass
class MemoryEntry:
    owner: str
    text: str
    topic_id: str
    vec: np.ndarray


class UserMemory:
    """Owner-tagged memory entries with cosine search over all users or one user."""

    def __init__(self, embedder):
        self.embedder = embedder
        self.entries: list[MemoryEntry] = []

    def write(self, owner: str, text: str, topic_id: str = "") -> None:
        v = self.embedder.encode([text], normalize_embeddings=True)[0]
        self.entries.append(MemoryEntry(owner, text, topic_id, np.asarray(v)))

    def search(self, query: str, k: int, owner: str | None = None) -> list[tuple[MemoryEntry, float]]:
        """Top-k entries by cosine similarity; `owner` restricts the search to that user's entries."""
        pool = [e for e in self.entries if owner is None or e.owner == owner]
        if not pool:
            return []
        q = np.asarray(self.embedder.encode([query], normalize_embeddings=True)[0])
        sc = np.array([float(e.vec @ q) for e in pool])
        return [(pool[i], sc[i]) for i in np.argsort(-sc)[:k]]


def build_summary(shares: list[dict], model_cfg: dict, cfg: dict, cache: dict) -> str:
    """Running summary: fold each shared message into the notes with one LLM call per message (cached)."""
    key = model_cfg["name"]
    if key in cache:
        return cache[key]
    notes = "(empty)"
    for sh in shares:
        kw = {"model": model_cfg["litellm_id"], "temperature": cfg["agent"]["temperature"],
              "messages": [{"role": "user", "content": SUMMARY_PROMPT.format(notes=notes, message=sh["text"])}]}
        if model_cfg.get("api_base"):
            kw["api_base"] = model_cfg["api_base"]
        notes = litellm.completion(**kw).choices[0].message.content.strip()
    cache[key] = notes
    p = resolve(cfg["multiuser"]["summary_cache"])
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(cache, indent=1), encoding="utf-8")
    return notes


def load_summary_cache(cfg: dict) -> dict:
    p = resolve(cfg["multiuser"]["summary_cache"])
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
