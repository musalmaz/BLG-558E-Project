"""Chunk + embed labeled emails and canary docs into ChromaDB with acl_label metadata."""
import json

import chromadb
from sentence_transformers import SentenceTransformer

from src.config import load_config, resolve
from src.data_layer.acl_labeler import distribution

COLLECTION = "emails"
CHUNK_CHARS = 500
BATCH = 256


def chunk_text(text: str, size: int = CHUNK_CHARS) -> list[str]:
    """Split text into chunks of ~size chars on whitespace boundaries."""
    chunks, cur = [], ""
    for word in text.split():
        if cur and len(cur) + 1 + len(word) > size:
            chunks.append(cur)
            cur = word
        else:
            cur = f"{cur} {word}".strip()
    if cur:
        chunks.append(cur)
    return chunks


def to_chunks(doc: dict) -> list[dict]:
    """Turn one document into chunk records with metadata."""
    text = f"Subject: {doc['subject']}\n{doc['body']}"
    return [
        {
            "id": f"{doc['id']}::{i}",
            "text": c,
            "meta": {
                "doc_id": doc["id"],
                "acl_label": doc["acl_label"],
                "folder": doc.get("folder", ""),
                "is_canary": bool(doc.get("is_canary", False)),
            },
        }
        for i, c in enumerate(chunk_text(text))
    ]


def build_index(docs: list[dict], persist_dir: str, model_name: str):
    """(Re)build the Chroma collection from docs; returns the collection."""
    client = chromadb.PersistentClient(path=persist_dir)
    try:
        client.delete_collection(COLLECTION)
    except Exception:  # noqa: BLE001
        pass
    col = client.create_collection(COLLECTION, metadata={"hnsw:space": "cosine"})
    chunks = [c for d in docs for c in to_chunks(d)]
    model = SentenceTransformer(model_name)
    for i in range(0, len(chunks), BATCH):
        b = chunks[i : i + BATCH]
        emb = model.encode([c["text"] for c in b], normalize_embeddings=True).tolist()
        col.add(ids=[c["id"] for c in b], documents=[c["text"] for c in b],
                embeddings=emb, metadatas=[c["meta"] for c in b])
    return col, len(chunks)


def main() -> None:
    cfg = load_config()
    labeled = resolve(cfg["data"]["labeled_dir"]) / "emails_labeled.jsonl"
    docs = [json.loads(ln) for ln in open(labeled, encoding="utf-8")]
    canary_file = json.loads((resolve(cfg["data"]["canaries_dir"]) / "canaries.json").read_text(encoding="utf-8"))
    canary_docs = canary_file["docs"]
    all_docs = docs + canary_docs
    col, n_chunks = build_index(all_docs, str(resolve(cfg["index"]["chroma_dir"])),
                                cfg["index"]["embedding_model"])
    summary = {
        "n_docs": len(all_docs),
        "n_enron_docs": len(docs),
        "n_canary_docs": len(canary_docs),
        "n_chunks": n_chunks,
        "acl_distribution": distribution(all_docs),
        "acl_distribution_enron_only": distribution(docs),
        "canaries_generated_by": canary_file.get("generated_by", "unknown"),
        "canaries": canary_file["canaries"],
    }
    out = resolve(cfg["paths"]["data_summary"])
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "canaries"}, indent=2))
    print(f"summary -> {out}")


if __name__ == "__main__":
    main()
