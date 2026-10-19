"""Offline tests for the cross-user pilot (memory isolation, modes, prompt hook)."""
import chromadb

from src.agent.agent import SYSTEM_MODE, build_messages
from src.config import load_config
from src.multiuser.memory import UserMemory
from src.multiuser.retriever import MultiUserRetriever
from tests.test_agent import FakeEmbedder


def _retriever():
    cfg = load_config()
    cfg["index"]["top_k"] = 4
    emb = FakeEmbedder()
    col = chromadb.EphemeralClient().create_collection("t_mu" + str(id(object())))
    labels = ["public", "internal", "confidential", "internal"] * 3
    texts = [f"doc {i}" for i in range(12)]
    col.add(ids=[f"d{i}::0" for i in range(12)], documents=texts, embeddings=emb.encode(texts).tolist(),
            metadatas=[{"doc_id": f"d{i}", "acl_label": labels[i], "folder": "", "is_canary": False}
                       for i in range(12)])
    mem = UserMemory(emb)
    mem.write("A", "A's private fact one", "c00")
    mem.write("A", "A's private fact two", "c01")
    r = MultiUserRetriever(cfg, mem, {"m": "- A's notes"}, collection=col, embedder=emb)
    r.current_model = "m"
    return r


def test_x2_isolated_never_returns_other_users_memory():
    r = _retriever()
    assert not [c for c in r.retrieve("q", "X2_isolated") if c.acl_label == "user_memory"]
    r.memory.write("B", "B's own note", "")
    own = [c for c in r.retrieve("q", "X2_isolated") if c.acl_label == "user_memory"]
    assert own and all("B's own" in c.text for c in own)


def test_x1_shared_returns_other_users_memory_and_enterprise_has_no_confidential():
    r = _retriever()
    got = r.retrieve("q", "X1_shared_weak")
    assert [c for c in got if c.acl_label == "user_memory" and c.text.startswith("A's")]
    assert "confidential" not in {c.acl_label for c in got}


def test_x3_returns_shared_notes():
    r = _retriever()
    notes = [c for c in r.retrieve("q", "X3_shared_summary") if c.acl_label == "customer_notes"]
    assert len(notes) == 1 and notes[0].text == "- A's notes"


def test_prompt_hook_keeps_existing_modes_and_adds_xuser_rule():
    assert "confidential" in build_messages("hi", [], "M1_weak")[0]["content"]
    assert "confidential" not in build_messages("hi", [], "M2_strong")[0]["content"]
    for m in ("X1_shared_weak", "X3_shared_summary"):
        assert "other customers" in build_messages("hi", [], m)[0]["content"]
    assert "X2_isolated" not in SYSTEM_MODE
