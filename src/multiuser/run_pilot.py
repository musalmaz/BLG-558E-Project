"""Cross-user pilot driver: A shares data, B probes; plus direct-question baseline and retrieval stats."""
import argparse
import json

import pandas as pd

from src.config import load_config, resolve
from src.defenses.evaluate_defenses import chunked_run, unload_ollama
from src.multiuser.memory import UserMemory, build_summary, load_summary_cache
from src.multiuser.retriever import MODES, MultiUserRetriever
from src.probes.baseline_check import evaluate as eval_leak
from src.probes.generator import load_probes
from src.probes.runner import build_matrix


def setup(cfg: dict) -> tuple[MultiUserRetriever, list[dict]]:
    """Retriever with A's shared messages already written to memory (and per-model summaries on demand)."""
    shares = json.loads(resolve(cfg["multiuser"]["shares_file"]).read_text(encoding="utf-8"))["shares"]
    r = MultiUserRetriever(cfg, UserMemory(embedder=None))
    r.memory.embedder = r.embedder
    for sh in shares:
        r.memory.write(sh["user"], sh["text"], sh["topic_id"])
    return r, shares


def run(cfg: dict, models: list[str]) -> None:
    from src.agent.agent import AgentRunner
    r, shares = setup(cfg)
    cache = load_summary_cache(cfg)
    log = resolve(cfg["multiuser"]["log"])
    mcfg = {m["name"]: m for m in cfg["models"]}
    for model in models:
        build_summary(shares, mcfg[model], cfg, cache)
        r.summaries[model] = cache[model]
        r.current_model = model
        jobs = build_matrix({**cfg, "acl_modes": list(cfg["multiuser"]["modes"])}, load_probes(), [model],
                            None, cfg["probes"]["variants_per_topic"], 1)
        chunked_run(jobs, AgentRunner(cfg, r, log_path=str(log)), log, cfg)
        unload_ollama(cfg)


def baseline(cfg: dict, models: list[str]) -> dict:
    """B asks the 20 direct questions: does A's private data appear in the answer?"""
    from src.agent.agent import AgentRunner
    r, shares = setup(cfg)
    cache = load_summary_cache(cfg)
    qs = json.loads(resolve(cfg["probes"]["direct_queries_file"]).read_text(encoding="utf-8"))
    has_share = {s["topic_id"] for s in shares}
    mcfg = {m["name"]: m for m in cfg["models"]}
    agent = AgentRunner(cfg, r)
    out = {}
    for model in models:
        build_summary(shares, mcfg[model], cfg, cache)
        r.summaries[model], r.current_model = cache[model], model
        for mode in cfg["multiuser"]["modes"]:
            res = []
            for i, q in enumerate(qs):
                dec, _ = agent.handle(q["text"], mode, model, log=False)
                res.append({**eval_leak(dec, q["secret_markers"]), "topic_id": q["topic_id"]})
            out[f"{model}|{mode}"] = {"n": len(res), "leaked": sum(x["leaked"] for x in res),
                                      "leaked_topics": sorted({x["topic_id"] for x in res if x["leaked"]}),
                                      "asked_topics_with_share": sorted({x["topic_id"] for x in res} & has_share)}
            print(model, mode, out[f"{model}|{mode}"]["leaked"], "/", len(res), flush=True)
            unload_ollama(cfg)  # caps Ollama memory growth between 20-call blocks
        unload_ollama(cfg)
    resolve("results/xuser_baseline.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    return out


def retrieval_stats(cfg: dict) -> pd.DataFrame:
    """Share of B's messages whose context contains A's memory (own-topic entry) / the shared notes."""
    from src.features.dataset import load_log
    df = load_log(resolve(cfg["multiuser"]["log"]), cfg)
    df["own_mem"] = [any(i == f"mem_A_{t}" for i in ids) for ids, t in zip(df.retrieved_doc_ids, df.topic_id)]
    df["any_mem"] = [any(i.startswith("mem_") for i in ids) for ids in df.retrieved_doc_ids]
    df["notes"] = [any(i == "shared_notes" for i in ids) for ids in df.retrieved_doc_ids]
    g = df.groupby(["model", "acl_mode", "kind", "present"])
    return g.agg(n=("own_mem", "size"), own_mem=("own_mem", "mean"), any_mem=("any_mem", "mean"),
                 notes=("notes", "mean")).reset_index()


def content_leak(cfg: dict) -> pd.DataFrame:
    """Share of B's answers that contain a secret marker of A's share on that topic (direct content leak)."""
    from src.features.dataset import load_log
    markers = {s["topic_id"]: s["markers"] for s in
               json.loads(resolve(cfg["multiuser"]["shares_file"]).read_text(encoding="utf-8"))["shares"]}
    df = load_log(resolve(cfg["multiuser"]["log"]), cfg)
    df["leak"] = [t in markers and any(m.lower() in (a or "").lower() for m in markers[t])
                  for t, a in zip(df.topic_id, df.answer_text)]
    g = df.groupby(["model", "acl_mode", "kind", "present"])
    return g.agg(n=("leak", "size"), leaked=("leak", "sum"), rate=("leak", "mean")).reset_index()


def main() -> None:
    cfg = load_config()
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["run", "baseline", "stats", "leak"])
    ap.add_argument("--models", nargs="+", default=[m["name"] for m in cfg["models"]])
    a = ap.parse_args()
    if a.stage == "run":
        run(cfg, a.models)
    elif a.stage == "baseline":
        baseline(cfg, a.models)
    elif a.stage == "leak":
        t = content_leak(cfg)
        t.to_csv(resolve("results/xuser_leak.csv"), index=False)
        print(t.round(3).to_string(index=False))
    else:
        t = retrieval_stats(cfg)
        t.to_csv(resolve("results/xuser_retrieval.csv"), index=False)
        print(t.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
