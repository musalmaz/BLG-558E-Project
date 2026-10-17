"""Append-only JSONL logger for agent calls."""
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from src.config import load_config, resolve

FIELDS = [
    "message_id", "acl_mode", "model", "retrieved_acl_labels", "escalated",
    "refusal_type", "routing_target", "answer_text", "latency_ms", "timestamp",
    "retrieved_doc_ids", "prompt_tokens", "completion_tokens", "parse_error", "message_text",
]


def log_call(record: dict, path: str | Path | None = None) -> dict:
    """Fill defaults (message_id, timestamp), validate fields, append one JSONL row."""
    rec = dict(record)
    rec.setdefault("message_id", None)
    rec["message_id"] = rec["message_id"] or str(uuid.uuid4())
    rec.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
    missing = [f for f in FIELDS if f not in rec]
    if missing:
        raise ValueError(f"log record missing fields: {missing}")
    out = Path(path) if path else resolve(load_config()["paths"]["agent_log"])
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "a", encoding="utf-8") as f:
        f.write(json.dumps({k: rec[k] for k in FIELDS}, ensure_ascii=False) + "\n")
    return rec
