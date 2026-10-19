"""Faz 6 driver: collect (LLM stages), build defended logs, evaluate security (decoders) vs utility."""
import argparse
import json
import random
import urllib.request

import pandas as pd

from src.config import load_config, resolve
from src.defenses import behavior_norm, decision_hiding
from src.defenses.quality import (load_utility, resolution_rate, routing_agreement, utility_recall)
from src.defenses.scoped_context import ScopedRetriever
from src.features.dataset import load_log
from src.probes.generator import load_probes
from src.probes.runner import build_matrix, logged_ids, make_id, run as run_jobs

NONE_LOG = "results/runs/probe_matrix_20topics_repeats1.jsonl"
SCOPED = {"scoped_context", "all"}
NORM = {"behavior_norm", "all"}
HIDE = {"decision_hiding", "all"}
CHUNK = 40


def runs(cfg: dict, name: str):
    return resolve(cfg["defenses"]["runs_dir"]) / name


def unload_ollama(cfg: dict) -> None:
    """Ask Ollama to drop loaded models (caps memory between chunks)."""
    for m in cfg["models"]:
        tag = m["litellm_id"].split("/", 1)[1]
        req = urllib.request.Request(f"{m['api_base']}/api/generate", method="POST",
                                     data=json.dumps({"model": tag, "keep_alive": 0}).encode())
        try:
            urllib.request.urlopen(req, timeout=30).read()
        except Exception:  # noqa: BLE001 - best effort
            pass


def chunked_run(jobs, agent, log, cfg) -> None:
    done = logged_ids(log)
    todo = [j for j in jobs if j["message_id"] not in done]
    for i in range(0, len(todo), CHUNK):
        run_jobs(todo[i:i + CHUNK], agent, log, True)
        unload_ollama(cfg)


def utility_jobs(cfg: dict, mode: str) -> list[dict]:
    util, models = load_utility(cfg), [m["name"] for m in cfg["models"]]
    jobs = [{"message_id": make_id(u, "util", 0, 0, mode, m), "text": it["text"], "mode": mode, "model": m}
            for u, it in util.items() for m in models]
    random.Random(cfg["random_seed"]).shuffle(jobs)
    jobs.sort(key=lambda j: models.index(j["model"]))
    return jobs


def read_rows(path, probe_matrix: bool = False, mode: str = "M1_weak") -> list[dict]:
    rows = [json.loads(ln) for ln in open(path, encoding="utf-8") if ln.strip()]
    rows = [r for r in rows if not r["parse_error"] and len(r["message_id"].split("|")) == 6
            and not r["message_id"].startswith("baseline")]
    if probe_matrix:
        rows = [r for r in rows if r["acl_mode"] == mode]
    return rows


def collect(cfg: dict) -> None:
    """Run all LLM stages (resumable): scoped matrix, utility sets, context-free decisions."""
    from src.agent.agent import AgentRunner
    from src.agent.retrieval import Retriever
    models = [m["name"] for m in cfg["models"]]
    mode = cfg["defenses"]["mode"]
    m1cfg = {**cfg, "acl_modes": [mode]}
    scoped = ScopedRetriever(cfg)
    plain = Retriever(cfg)
    chunked_run(build_matrix(m1cfg, load_probes(), models, None, cfg["probes"]["variants_per_topic"], 1),
                AgentRunner(cfg, scoped, log_path=str(runs(cfg, "def_scoped_raw.jsonl"))),
                runs(cfg, "def_scoped_raw.jsonl"), cfg)
    for fname, retr, m in (("util_none_raw.jsonl", plain, mode), ("util_m2_raw.jsonl", plain, "M2_strong"),
                           ("util_scoped_raw.jsonl", scoped, mode)):
        chunked_run(utility_jobs(cfg, m), AgentRunner(cfg, retr, log_path=str(runs(cfg, fname))),
                    runs(cfg, fname), cfg)
    # context-free decisions for every distinct (model, message) of the none and scoped matrices
    agent = AgentRunner(cfg, decision_hiding.NullRetriever())
    cache = decision_hiding.load_cache(cfg)
    pairs = {(r["model"], r["message_text"]) for p in (resolve(NONE_LOG), runs(cfg, "def_scoped_raw.jsonl"))
             for r in read_rows(p, probe_matrix=True)}
    todo = sorted(p for p in pairs if decision_hiding._key(*p) not in cache)
    todo.sort(key=lambda p: models.index(p[0]))
    print(f"context-free decisions to run: {len(todo)}", flush=True)
    for i, (model, text) in enumerate(todo, 1):
        decision_hiding.ctxfree_decision(agent, text, model, cfg, cache)
        if i % CHUNK == 0:
            print(f"[ctxfree {i}/{len(todo)}]", flush=True)
            unload_ollama(cfg)


def derive(rows: list[dict], name: str, cfg: dict, cache: dict) -> list[dict]:
    """Apply the defense pipeline for `name` to raw agent rows (norm first, then hiding)."""
    out = []
    for r in rows:
        r = {**r, "raw_escalated": r["escalated"], "raw_refusal_type": r["refusal_type"],
             "raw_routing_target": r["routing_target"], "latency_raw_ms": r["latency_ms"]}
        if name in NORM:
            r = behavior_norm.normalize(r, cfg)
        if name in HIDE:
            r = decision_hiding.apply(r, cache, cfg)
        out.append(r)
    return out


def write_rows(rows: list[dict], path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def build(cfg: dict) -> None:
    """Write defended logs (def_<name>.jsonl) and defended utility logs (util_<name>.jsonl)."""
    cache = decision_hiding.load_cache(cfg)
    base = {False: read_rows(resolve(NONE_LOG), probe_matrix=True),
            True: read_rows(runs(cfg, "def_scoped_raw.jsonl"))}
    ubase = {False: read_rows(runs(cfg, "util_none_raw.jsonl")), True: read_rows(runs(cfg, "util_scoped_raw.jsonl"))}
    for name in cfg["defenses"]["names"]:
        sc = name in SCOPED
        rows = derive(base[sc], name, cfg, cache)
        if name in HIDE and sum(decision_hiding._key(r["model"], r["message_text"]) not in cache for r in rows):
            raise RuntimeError(f"context-free cache incomplete for {name}; run collect first")
        write_rows(rows, runs(cfg, f"def_{name}.jsonl"))
        write_rows(derive(ubase[sc], "behavior_norm" if name in NORM else "none", cfg, cache), runs(cfg, f"util_{name}.jsonl"))
        print(f"{name}: {len(rows)} rows, max latency {max(r['latency_ms'] for r in rows):.0f} ms")
        over = [r for r in rows if name in HIDE and r["latency_raw_ms"] > cfg["defenses"]["latency_pad_ms"]]
        if over:
            print(f"  WARNING: {len(over)} rows exceed latency_pad_ms (not constant)")


def evaluate(cfg: dict, force: bool = False) -> pd.DataFrame:
    """Decoders on every defended log + quality proxies -> defense_results.csv."""
    from src.decoders.run_all import run as run_decoders
    util = load_utility(cfg)
    ddir = resolve("results/defenses")
    ddir.mkdir(parents=True, exist_ok=True)
    none_df = load_log(runs(cfg, "def_none.jsonl"), cfg)
    parts = []
    names = list(cfg["defenses"]["names"]) + ["M2_reference"]
    for name in names:
        if name == "M2_reference":
            df = load_log(resolve(NONE_LOG), cfg)
            df = df[df.acl_mode == "M2_strong"].reset_index(drop=True)
            urows = read_rows(runs(cfg, "util_m2_raw.jsonl"))
        else:
            df = load_log(runs(cfg, f"def_{name}.jsonl"), cfg)
            urows = read_rows(runs(cfg, f"util_{name}.jsonl"))
        f = ddir / f"decoder_{name}.csv"
        if f.exists() and not force:
            res = pd.read_csv(f)
        else:
            res, stats, _ = run_decoders(df, cfg)
            res.to_csv(f, index=False)
            (ddir / f"stat_tests_{name}.json").write_text(json.dumps(stats, indent=2, default=float), encoding="utf-8")
        for model, cell in df.groupby("model"):
            q = {"resolution": resolution_rate(cell),
                 "routing_agreement": routing_agreement(cell, none_df[none_df.model == model]),
                 **utility_recall([r for r in urows if r["model"] == model], util)}
            r = res[res.model == model].copy()
            for k, v in q.items():
                r[k] = v
            parts.append(r.assign(defense=name))
    out = pd.concat(parts, ignore_index=True)
    base = out[out.defense == "none"].set_index(["model", "group"])
    key = list(zip(out.model, out.group))
    out["delta_auc"] = [base.loc[k, "auc"] for k in key] - out["auc"]
    out["recall_loss"] = [base.loc[k, "recall"] for k in key] - out["recall"]
    out["resolution_loss"] = [base.loc[k, "resolution"] for k in key] - out["resolution"]
    out.to_csv(resolve(cfg["defenses"]["results_csv"]), index=False)
    return out


def to_markdown(out: pd.DataFrame) -> str:
    f = lambda x, n=2: "–" if pd.isna(x) else f"{x:.{n}f}"  # noqa: E731
    L = ["# Savunma değerlendirmesi (M1_weak; M2_reference = güçlü ACL referansı)", "",
         "| Model | Savunma | Grup | AUC [%95 GA] | ΔAUC | bit | p | Çözüm | Yönl. uyum | Recall (pub/int) | Recall kaybı |",
         "|---|---|---|---|---|---|---|---|---|---|---|"]
    for _, r in out.iterrows():
        L.append(f"| {r['model']} | {r['defense']} | {r['group']} | {f(r['auc'])} [{f(r['auc_ci_lo'])}–{f(r['auc_ci_hi'])}] | "
                 f"{f(r['delta_auc'])} | {f(r['leaked_bits_model'], 3)} | {f(r['p_topic_perm'], 3)} | {f(r['resolution'])} | "
                 f"{f(r['routing_agreement'])} | {f(r['recall'])} ({f(r['recall_public'])}/{f(r['recall_internal'])}) | "
                 f"{f(r['recall_loss'])} |")
    return "\n".join(L) + "\n"


def main() -> None:
    cfg = load_config()
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["collect", "build", "evaluate"])
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    if a.stage == "collect":
        collect(cfg)
    elif a.stage == "build":
        build(cfg)
    else:
        from src.defenses.figures import security_utility_figure
        out = evaluate(cfg, a.force)
        resolve("results/defense_table.md").write_text(to_markdown(out), encoding="utf-8")
        d = resolve("results/figures")
        d.mkdir(parents=True, exist_ok=True)
        security_utility_figure(out, d / "security_utility.png")
        print(to_markdown(out))


if __name__ == "__main__":
    main()
