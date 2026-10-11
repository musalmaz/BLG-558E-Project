"""Offline tests for the Faz 1 data layer (no network, no LLM)."""
import json

import pytest

from src.data_layer import canaries
from src.data_layer.acl_labeler import distribution, heuristic_label, label_all, load_overrides
from src.data_layer.build_index import build_index, chunk_text
from src.data_layer.loader import clean_body, parse_email

RAW = b"""From: a@enron.com
To: b@enron.com, c@enron.com
Subject: Hello
Content-Type: text/plain

Please see the numbers.

Thanks,
Al
--
Al Smith
VP

-----Original Message-----
From: x@enron.com
Sent: today
secret old text
"""


def rec(i, subject="s", body="b", folder="inbox", to=None):
    return {"id": i, "subject": subject, "body": body, "folder": folder, "to": to or ["a"]}


def test_clean_body_strips_chain_and_signature():
    out = clean_body(RAW.decode().split("\n\n", 1)[1])
    assert "old text" not in out and "VP" not in out
    assert out.startswith("Please see the numbers.")


def test_parse_email_normalizes_fields():
    r = parse_email(RAW, "id1", "user/inbox")
    assert set(r) == {"id", "from", "to", "subject", "body", "folder"}
    assert r["to"] == ["b@enron.com", "c@enron.com"] and r["subject"] == "Hello"


def test_heuristic_and_override(tmp_path):
    assert heuristic_label(rec("1", subject="Settlement terms")) == "confidential"
    assert heuristic_label(rec("2", subject="Press release")) == "public"
    assert heuristic_label(rec("3")) == "internal"
    csv = tmp_path / "o.csv"
    csv.write_text("id,acl_label\n3,confidential\n")
    out = label_all([rec("3")], load_overrides(csv), ["public", "internal", "confidential"])
    assert out[0]["acl_label"] == "confidential"
    assert distribution(out) == {"confidential": 1}


def test_canary_build_with_stub_llm(monkeypatch):
    cfg = {"canaries": {"n_topics": 2, "n_absent_topics": 1, "docs_per_canary": 2,
                        "llm_model": "x", "api_base": None}}

    def fake(prompt, cfg, retries=3):
        if "DISTINCT" in prompt:
            return ["Project A", "Project B", "Project C"]
        return [{"from": "f", "to": ["t"], "subject": "s", "body": "Project text"}] * 2

    monkeypatch.setattr(canaries, "_llm_json", fake)
    res = canaries.build(cfg)
    present = [c for c in res["canaries"] if c["present"]]
    assert len(present) == 2 and all(c["doc_ids"] for c in present)
    assert all(d["acl_label"] == "confidential" for d in res["docs"])
    assert [c["present"] for c in res["canaries"]] == [1, 1, 0]


def test_chunking():
    chunks = chunk_text("word " * 400, 100)
    assert len(chunks) > 10 and all(len(c) <= 100 for c in chunks)


def test_index_returns_acl_metadata(tmp_path):
    pytest.importorskip("sentence_transformers")
    docs = [dict(rec("d1", body="gas pipeline maintenance"), acl_label="public"),
            dict(rec("d2", body="Project Falcon merger terms"), acl_label="confidential", is_canary=True)]
    col, n = build_index(docs, str(tmp_path / "chroma"), "sentence-transformers/all-MiniLM-L6-v2")
    from sentence_transformers import SentenceTransformer
    emb = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2").encode(
        ["Falcon merger"], normalize_embeddings=True).tolist()
    res = col.query(query_embeddings=emb, n_results=1)
    assert res["metadatas"][0][0]["acl_label"] == "confidential"


def test_keywords_match_whole_words_only():
    assert heuristic_label(rec("4", subject="Monday agenda")) == "internal"
    assert heuristic_label(rec("5", folder="kean-s/discussion_threads")) == "internal"
    assert heuristic_label(rec("6", folder="kean-s/hr")) == "confidential"
