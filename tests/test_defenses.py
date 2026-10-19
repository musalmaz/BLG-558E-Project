"""Offline tests for Faz 6 defenses."""
import chromadb
import pandas as pd

from src.config import load_config
from src.defenses import behavior_norm, decision_hiding
from src.defenses.evaluate_defenses import derive
from src.defenses.quality import resolution_rate, routing_agreement, utility_recall
from src.defenses.scoped_context import ScopedRetriever
from tests.test_agent import FakeEmbedder


def _row(ref="none", esc=False, route="sales", ans="Our price is 5.", lat=1000.0, text="hi", mid="c00|control|v0|r0|M1_weak|m"):
    return {"message_id": mid, "model": "m", "message_text": text, "escalated": esc, "refusal_type": ref,
            "routing_target": route, "answer_text": ans, "latency_ms": lat}


def test_behavior_norm_refusal_types_indistinguishable():
    cfg = load_config()
    outs = [behavior_norm.normalize(_row(ref=r, ans=f"text for {r}"), cfg)
            for r in ("no_info", "cannot_share", "deflect")]
    assert len({(o["answer_text"], o["refusal_type"]) for o in outs}) == 1
    assert outs[0]["answer_text"] == cfg["defenses"]["refusal_template"]
    ok = behavior_norm.normalize(_row(), cfg)
    assert ok["answer_text"] == "Our price is 5." and ok["refusal_type"] == "none"


def test_scoped_retriever_public_only():
    cfg = load_config()
    cfg["index"]["top_k"] = 12
    emb = FakeEmbedder()
    col = chromadb.EphemeralClient().create_collection("t_scoped")
    labels = ["public", "internal", "confidential"] * 4
    texts = [f"doc {i}" for i in range(12)]
    col.add(ids=[f"d{i}::0" for i in range(12)], documents=texts, embeddings=emb.encode(texts).tolist(),
            metadatas=[{"doc_id": f"d{i}", "acl_label": labels[i], "folder": "", "is_canary": False}
                       for i in range(12)])
    r = ScopedRetriever(cfg, collection=col, embedder=emb)
    got = r.retrieve("q", "M1_weak")
    assert got and {c.acl_label for c in got} == {"public"}


def test_decision_hiding_context_independent_and_constant_latency():
    cfg = load_config()
    key = decision_hiding._key("m", "hi")
    cache = {key: {"escalated": False, "refusal_type": "none", "routing_target": "sales"}}
    a = decision_hiding.apply(_row(ref="cannot_share", route="legal", lat=1500.0), cache, cfg)
    b = decision_hiding.apply(_row(ref="none", route="billing", lat=9000.0), cache, cfg)
    for f in ("escalated", "refusal_type", "routing_target", "latency_ms"):
        assert a[f] == b[f]
    assert a["raw_routing_target"] == "legal" and b["latency_raw_ms"] == 9000.0


def test_derive_all_templates_by_raw_decision():
    cfg = load_config()
    cache = {decision_hiding._key("m", "hi"): {"escalated": False, "refusal_type": "none", "routing_target": "sales"}}
    out = derive([_row(ref="cannot_share")], "all", cfg, cache)[0]
    assert out["answer_text"] == cfg["defenses"]["refusal_template"] and out["refusal_type"] == "none"
    assert out["raw_refusal_type"] == "cannot_share"


def test_quality_proxies():
    df = pd.DataFrame([{"kind": "control", "refusal_type": "none", "escalated": False, "message_id": "a", "routing_target": "x"},
                       {"kind": "control", "refusal_type": "deflect", "escalated": False, "message_id": "b", "routing_target": "y"}])
    assert resolution_rate(df) == 0.5
    ref = df.assign(routing_target=["x", "z"])
    assert routing_agreement(df, ref) == 0.5
    util = {"u00": {"acl_label": "public", "markers": ["2:30"]}, "u01": {"acl_label": "internal", "markers": ["a", "b"]}}
    rows = [{"message_id": "u00|util|v0|r0|M1_weak|m", "answer_text": "At 2:30 pm"},
            {"message_id": "u01|util|v0|r0|M1_weak|m", "answer_text": "only a"}]
    r = utility_recall(rows, util)
    assert r["recall_public"] == 1.0 and r["recall_internal"] == 0.5 and r["recall"] == 0.75
