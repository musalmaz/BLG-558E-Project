"""Fictitious canary secret topics, LLM-generated confidential emails and ground-truth labels."""
import argparse
import json
import re

import litellm

from src.config import load_config, resolve

TOPIC_PROMPT = """Generate {n} DISTINCT, entirely FICTITIOUS confidential corporate project/event topics
for a synthetic email dataset (e.g. "Project Falcon merger", "closure of the Ankara office").
Use invented code names and places; no real companies, people or market-sensitive facts.
Return ONLY a JSON list of {n} short strings (3-8 words each)."""

DOC_PROMPT = """Write {n} DIFFERENT short internal corporate emails (60-150 words each) that all
discuss the entirely FICTITIOUS confidential topic: "{topic}".
They are internal and confidential: plausible staff names are fine but must be invented. Each email
must clearly mention the topic wording. No real companies, people or real market data.
Return ONLY a JSON list of {n} objects with keys "from", "to" (list of strings), "subject", "body"."""


def _llm_json(prompt: str, cfg: dict, retries: int = 3):
    """Call the LLM and parse the first JSON array in its reply (retry on failure)."""
    c = cfg["canaries"]
    last = None
    for _ in range(retries):
        resp = litellm.completion(
            model=c["llm_model"],
            api_base=c.get("api_base"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8,
        )
        text = resp.choices[0].message.content or ""
        m = re.search(r"\[.*\]", text, re.S)
        try:
            return json.loads(m.group(0))
        except Exception as e:  # noqa: BLE001
            last = e
    raise RuntimeError(f"LLM did not return valid JSON: {last}")


def generate_topics(cfg: dict) -> list[str]:
    """Produce present + absent fictitious topics (unique)."""
    c = cfg["canaries"]
    n = c["n_topics"] + c["n_absent_topics"]
    topics: list[str] = []
    while len(topics) < n:
        for t in _llm_json(TOPIC_PROMPT.format(n=n), cfg):
            if isinstance(t, str) and t.strip() and t.strip().lower() not in {x.lower() for x in topics}:
                topics.append(t.strip())
    return topics[:n]


def generate_docs(topic: str, topic_id: str, cfg: dict) -> list[dict]:
    """LLM-generate confidential emails about one canary topic."""
    n = cfg["canaries"]["docs_per_canary"]
    raw = _llm_json(DOC_PROMPT.format(n=n, topic=topic), cfg)
    docs = []
    for i, d in enumerate(raw[:n]):
        to = d.get("to", [])
        docs.append({
            "id": f"canary_{topic_id}_{i}",
            "from": str(d.get("from", "")),
            "to": to if isinstance(to, list) else [str(to)],
            "subject": str(d.get("subject", "")),
            "body": str(d.get("body", "")).strip(),
            "folder": "canary",
            "acl_label": "confidential",
            "is_canary": True,
            "canary_topic": topic_id,
        })
    if len(docs) < n:
        raise RuntimeError(f"only {len(docs)}/{n} docs generated for {topic!r}")
    return docs


def build(cfg: dict) -> dict:
    """Generate topics (present=1 with docs, present=0 without) and return the canary record."""
    topics = generate_topics(cfg)
    n_present = cfg["canaries"]["n_topics"]
    entries, docs = [], []
    for i, topic in enumerate(topics):
        tid = f"c{i:02d}"
        present = int(i < n_present)
        ids = []
        if present:
            d = generate_docs(topic, tid, cfg)
            docs += d
            ids = [x["id"] for x in d]
        entries.append({"topic_id": tid, "topic": topic, "present": present, "doc_ids": ids})
    return {"generated_by": cfg["canaries"]["llm_model"], "canaries": entries, "docs": docs}


def main() -> None:
    cfg = load_config()
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="regenerate even if output exists")
    args = ap.parse_args()
    out = resolve(cfg["data"]["canaries_dir"]) / "canaries.json"
    if out.exists() and not args.force:
        print(f"{out} exists; use --force to regenerate")
        return
    result = build(cfg)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {len(result['canaries'])} topics, {len(result['docs'])} docs -> {out}")


if __name__ == "__main__":
    main()
