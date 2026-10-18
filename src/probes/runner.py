"""Run the probe/control matrix through the agent; every call is logged by AgentRunner."""
import argparse
import json
import random
import time
from pathlib import Path

from src.config import load_config, resolve
from src.probes.generator import load_probes


def make_id(topic_id: str, kind: str, variant: int, rep: int, mode: str, model: str) -> str:
    """Deterministic message_id; Faz 4 parses topic/kind from it."""
    return f"{topic_id}|{kind}|v{variant}|r{rep}|{mode}|{model}"


def parse_id(message_id: str) -> dict:
    """Inverse of make_id."""
    t, kind, v, r, mode, model = message_id.split("|")
    return {"topic_id": t, "kind": kind, "variant": int(v[1:]), "rep": int(r[1:]),
            "acl_mode": mode, "model": model}


def build_matrix(cfg: dict, data: dict, models: list[str], topics: list[str] | None,
                 variants: int, repeats: int) -> list[dict]:
    """All (topic, mode, model, kind, variant, rep) jobs, shuffled with the config seed, then grouped by model."""
    jobs = []
    for it in data["items"]:
        if it["variant"] >= variants or (topics and it["topic_id"] not in topics):
            continue
        for mode in cfg["acl_modes"]:
            for model in models:
                for rep in range(repeats):
                    jobs.append({"message_id": make_id(it["topic_id"], it["kind"], it["variant"],
                                                       rep, mode, model),
                                 "text": it["text"], "mode": mode, "model": model})
    random.Random(cfg["random_seed"]).shuffle(jobs)
    # Group by model (stable sort): avoids Ollama reloading models on every call, which would add
    # large random latency noise. Order inside each model block stays shuffled.
    order = {m: i for i, m in enumerate(models)}
    jobs.sort(key=lambda j: order[j["model"]])
    return jobs


def logged_ids(log_path: Path) -> set[str]:
    """message_ids already present in the log (for --resume)."""
    if not log_path.exists():
        return set()
    return {json.loads(ln)["message_id"] for ln in open(log_path, encoding="utf-8") if ln.strip()}


def run(jobs: list[dict], agent, log_path: Path, resume: bool = True) -> dict:
    """Execute jobs sequentially; return a summary with tokens, latency, parse errors."""
    done = logged_ids(log_path) if resume else set()
    todo = [j for j in jobs if j["message_id"] not in done]
    if todo:  # unlogged warm-up call: the first call after an Ollama (re)load is a latency outlier
        agent.handle("Hello, I have a question about my account.", todo[0]["mode"], todo[0]["model"], log=False)
    s = {"total": len(jobs), "skipped_resume": len(jobs) - len(todo), "run": 0,
         "prompt_tokens": 0, "completion_tokens": 0, "parse_errors": 0, "latency_ms_sum": 0.0}
    t0 = time.time()
    for n, j in enumerate(todo, 1):
        _, meta = agent.handle(j["text"], j["mode"], j["model"], message_id=j["message_id"])
        s["run"] += 1
        s["prompt_tokens"] += meta["prompt_tokens"]
        s["completion_tokens"] += meta["completion_tokens"]
        s["parse_errors"] += int(meta["parse_error"])
        s["latency_ms_sum"] += meta["latency_ms"]
        eta = (time.time() - t0) / n * (len(todo) - n)
        print(f"[{n}/{len(todo)}] {j['message_id']} {meta['latency_ms']:.0f}ms eta {eta/60:.1f}min",
              flush=True)
    s["latency_ms_mean"] = s["latency_ms_sum"] / s["run"] if s["run"] else 0.0
    return s


def decision_agreement(log_path: Path) -> float | None:
    """Share of repeated (same id minus rep) calls whose (escalated, refusal, routing) agree."""
    groups: dict[str, set] = {}
    counts: dict[str, int] = {}
    for ln in open(log_path, encoding="utf-8"):
        r = json.loads(ln)
        parts = r["message_id"].split("|")
        if len(parts) != 6 or r["parse_error"]:
            continue
        key = "|".join(parts[:3] + parts[4:])
        groups.setdefault(key, set()).add((r["escalated"], r["refusal_type"], r["routing_target"]))
        counts[key] = counts.get(key, 0) + 1
    rep = [k for k, c in counts.items() if c > 1]
    return sum(len(groups[k]) == 1 for k in rep) / len(rep) if rep else None


def main() -> None:
    from src.agent.agent import AgentRunner
    from src.agent.retrieval import Retriever
    cfg = load_config()
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", default=[m["name"] for m in cfg["models"]])
    ap.add_argument("--topics", nargs="+")
    ap.add_argument("--variants", type=int, default=cfg["probes"]["variants_per_topic"])
    ap.add_argument("--repeats", type=int, default=cfg["probes"]["repeats"])
    ap.add_argument("--limit", type=int)
    ap.add_argument("--smoke", action="store_true", help="use probes.smoke config")
    ap.add_argument("--log", default=cfg["paths"]["agent_log"])
    ap.add_argument("--no-resume", action="store_true")
    ap.add_argument("--modes", nargs="+", help="restrict ACL modes (default: all in config)")
    ap.add_argument("--docs-per-topic", type=int, help="keep only the first k confidential docs per topic")
    a = ap.parse_args()
    if a.smoke:
        sm = cfg["probes"]["smoke"]
        a.topics, a.variants, a.repeats = sm["topics"], sm["variants"], sm["repeats"]
    if a.modes:
        cfg["acl_modes"] = a.modes
    log_path = resolve(a.log)
    jobs = build_matrix(cfg, load_probes(), a.models, a.topics, a.variants, a.repeats)
    if a.limit:
        jobs = jobs[: a.limit]
    summary = run(jobs, AgentRunner(cfg, Retriever(cfg, docs_per_topic=a.docs_per_topic), log_path=str(log_path)), log_path, not a.no_resume)
    summary["decision_agreement_across_repeats"] = (
        decision_agreement(log_path) if log_path.exists() else None)
    out = resolve(cfg["paths"]["probe_run_summary"])
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
