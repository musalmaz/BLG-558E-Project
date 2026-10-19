"""Defense 3: routing/escalation/answer-type and latency are independent of the retrieved context."""
import hashlib
import json
from pathlib import Path

from src.config import resolve

FALLBACK = {"escalated": False, "refusal_type": "none", "routing_target": "none"}


class NullRetriever:
    """Retriever stub returning no context (the context-free decision call)."""

    def retrieve(self, message: str, mode: str) -> list:
        return []


def _key(model: str, text: str) -> str:
    return hashlib.sha1(f"{model}|{text}".encode()).hexdigest()


def load_cache(cfg: dict) -> dict[str, dict]:
    p = resolve(cfg["defenses"]["ctxfree_cache"])
    if not p.exists():
        return {}
    rows = [json.loads(ln) for ln in open(p, encoding="utf-8") if ln.strip()]
    return {r["key"]: r["decision"] for r in rows}


def ctxfree_decision(agent, text: str, model: str, cfg: dict, cache: dict[str, dict]) -> dict:
    """Decision fields from the customer message alone; cached per (model, message)."""
    k = _key(model, text)
    if k in cache:
        return cache[k]
    dec, _ = agent.handle(text, "M2_strong", model, log=False)  # null retriever -> "(no context)"
    cache[k] = ({f: getattr(dec, f) for f in FALLBACK} if dec else dict(FALLBACK))
    p = resolve(cfg["defenses"]["ctxfree_cache"])
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8") as f:
        f.write(json.dumps({"key": k, "model": model, "decision": cache[k]}) + "\n")
    return cache[k]


def apply(row: dict, cache: dict[str, dict], cfg: dict) -> dict:
    """Copy of row with context-free decision fields and a constant externally visible latency."""
    out = dict(row)
    for f in ("escalated", "refusal_type", "routing_target"):
        out.setdefault(f"raw_{f}", out[f])
    dec = cache.get(_key(out["model"], out["message_text"]), FALLBACK)
    out.update(dec)
    out.setdefault("latency_raw_ms", out["latency_ms"])
    out["latency_ms"] = max(float(cfg["defenses"]["latency_pad_ms"]), float(out["latency_raw_ms"]))
    return out
