"""Offline tests for the masking defense (maskers, retriever, secret-span coverage)."""
import json

import chromadb

from src.config import load_config, resolve
from src.defenses.masking import MaskedRetriever, load_spans, mask_oracle, mask_rule
from tests.test_agent import FakeEmbedder


def _docs():
    f = json.loads((resolve("data/canaries") / "canaries.json").read_text(encoding="utf-8"))
    return f["docs"]


def test_oracle_removes_every_direct_query_marker_from_every_canary_chunk():
    cfg = load_config()
    spans = load_spans(cfg)
    qs = json.loads(resolve(cfg["probes"]["direct_queries_file"]).read_text(encoding="utf-8"))
    mk = {q["topic_id"]: q["secret_markers"] for q in qs}
    for d in _docs():
        out = mask_oracle("Subject: " + d["subject"] + " " + d["body"], spans).lower()
        assert not [m for m in mk.get(d["canary_topic"], []) if m.lower() in out], d["id"]


def test_oracle_touches_only_secret_spans():
    spans = ["6 million", "24th"]
    assert mask_oracle("counter at 6 million; vote on the 24th, we don't comment", spans) == \
        "counter at [REDACTED]; vote on the [REDACTED], we don't comment"


def test_rule_masks_numbers_dates_names_and_keeps_plain_words():
    out = mask_rule("Priya, we pay 3.1 million by the 5th of March to Westmere. Keep it quiet.")
    assert "3.1" not in out and "5th" not in out and "March" not in out and "Westmere" not in out
    assert "[NUM]" in out and "[DATE]" in out and "[NAME]" in out
    assert "[[" not in out and "Keep it quiet" in out
    assert mask_rule("a b c") == mask_rule("a b c")


def test_masked_retriever_masks_only_confidential_chunks():
    cfg = load_config()
    cfg["index"]["top_k"] = 3
    emb = FakeEmbedder()
    col = chromadb.EphemeralClient().create_collection("t_mask" + str(id(object())))
    texts = ["public 24th note", "internal 24th note", "confidential 24th note"]
    labels = ["public", "internal", "confidential"]
    col.add(ids=[f"d{i}::0" for i in range(3)], documents=texts, embeddings=emb.encode(texts).tolist(),
            metadatas=[{"doc_id": f"d{i}", "acl_label": labels[i], "folder": "", "is_canary": False} for i in range(3)])
    r = MaskedRetriever(cfg, "oracle", collection=col, embedder=emb)
    r.spans = ["24th"]
    got = {c.acl_label: c.text for c in r.retrieve("q", "M1_weak")}
    assert got["public"] == texts[0] and got["internal"] == texts[1]
    assert got["confidential"] == "confidential [REDACTED] note"
