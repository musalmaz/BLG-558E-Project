"""Offline tests for Faz 2 (retrieval, agent, logger)."""
import json
from types import SimpleNamespace

import chromadb
import numpy as np
import pytest

from src.agent import agent as agent_mod
from src.agent.agent import AgentRunner
from src.agent.logger import FIELDS, log_call
from src.agent.retrieval import Retriever
from src.config import load_config


class FakeEmbedder:
    """Deterministic 8-dim embedder (no model download)."""

    def encode(self, texts, normalize_embeddings=True):
        out = []
        for t in texts:
            v = np.random.default_rng(abs(hash(t)) % 2**32).random(8) + 0.1
            out.append(v / np.linalg.norm(v))
        return np.array(out)


@pytest.fixture
def retriever():
    col = chromadb.EphemeralClient().create_collection("t_" + str(id(object())))
    emb = FakeEmbedder()
    labels = ["public", "internal", "confidential"] * 4
    texts = [f"doc {i}" for i in range(12)]
    col.add(ids=[f"d{i}::0" for i in range(12)], documents=texts,
            embeddings=emb.encode(texts).tolist(),
            metadatas=[{"doc_id": f"d{i}", "acl_label": labels[i], "folder": "",
                        "is_canary": False} for i in range(12)])
    cfg = load_config()
    cfg["index"]["top_k"] = 12
    return Retriever(cfg, collection=col, embedder=emb)


def test_m2_never_confidential(retriever):
    assert "confidential" in {c.acl_label for c in retriever.retrieve("q", "M1_weak")}
    assert "confidential" not in {c.acl_label for c in retriever.retrieve("q", "M2_strong")}


def test_bad_mode(retriever):
    with pytest.raises(ValueError):
        retriever.retrieve("q", "M3")


def _resp(content):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
                           usage=SimpleNamespace(prompt_tokens=3, completion_tokens=2))


def _runner(retriever, tmp_path):
    cfg = load_config()
    return AgentRunner(cfg, retriever=retriever, log_path=str(tmp_path / "log.jsonl"))


GOOD = {"escalated": True, "refusal_type": "deflect", "routing_target": "legal", "answer_text": "hi"}


def test_valid_json(retriever, tmp_path, monkeypatch):
    monkeypatch.setattr(agent_mod.litellm, "completion", lambda **k: _resp(json.dumps(GOOD)))
    dec, meta = _runner(retriever, tmp_path).handle("hello", "M1_weak", "gemma3")
    assert dec.escalated and dec.routing_target == "legal" and not meta["parse_error"]


def test_unknown_routing_maps_other(retriever, tmp_path, monkeypatch):
    bad = {**GOOD, "routing_target": "hr_dept"}
    monkeypatch.setattr(agent_mod.litellm, "completion", lambda **k: _resp(json.dumps(bad)))
    dec, _ = _runner(retriever, tmp_path).handle("hello", "M2_strong", "gemma3")
    assert dec.routing_target == "other"


def test_retry_then_parse_error(retriever, tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(agent_mod.litellm, "completion",
                        lambda **k: calls.append(1) or _resp("not json"))
    dec, meta = _runner(retriever, tmp_path).handle("hello", "M1_weak", "gemma3")
    assert dec is None and meta["parse_error"] and len(calls) == 3
    row = json.loads((tmp_path / "log.jsonl").read_text().splitlines()[0])
    assert row["parse_error"] is True


def test_log_row_fields(retriever, tmp_path, monkeypatch):
    monkeypatch.setattr(agent_mod.litellm, "completion", lambda **k: _resp(json.dumps(GOOD)))
    _runner(retriever, tmp_path).handle("hello", "M1_weak", "gemma3", message_id="p1")
    row = json.loads((tmp_path / "log.jsonl").read_text().splitlines()[0])
    assert set(row) == set(FIELDS) and row["message_id"] == "p1"


def test_logger_missing_field(tmp_path):
    with pytest.raises(ValueError):
        log_call({"acl_mode": "M1_weak"}, tmp_path / "x.jsonl")
