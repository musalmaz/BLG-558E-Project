"""Masking defense driver: collect (LLM stages), evaluate security (decoders, marker leakage) vs utility."""
import argparse
import json
import random

import pandas as pd

from src.config import load_config, resolve
from src.defenses.evaluate_defenses import NONE_LOG, chunked_run, read_rows, runs
from src.defenses.masking import MaskedRetriever
from src.defenses.quality import load_utility, resolution_rate, routing_agreement
from src.defenses.scoped_context import ScopedRetriever
from src.features.dataset import load_log
from src.probes.baseline_check import evaluate as eval_leak
from src.probes.generator import load_probes
from src.probes.runner import build_matrix, make_id

MODE = "M1_weak"
BASELINES = ("none", "m2", "scoped")  # undefended, strong ACL, public-only context
CONDS = BASELINES + ("mask_oracle", "mask_rule")


def retriever(cfg: dict, name: str):
    from src.agent.retrieval import Retriever
    if name == "scoped":
        return ScopedRetriever(cfg)
    if name.startswith("mask_"):
        return MaskedRetriever(cfg, name.split("_", 1)[1])
    return Retriever(cfg)


def mode_of(name: str) -> str:
    return "M2_strong" if name == "m2" else MODE


def qa_jobs(items: list[dict], tag: str, mode: str, models: list[str], text_key: str = "text") -> list[dict]:
    """One job per (item, model), shuffled with the config seed, grouped by model."""
    jobs = [{"message_id": make_id(it["id"], tag, it.get("variant", 0), 0, mode, m), "text": it[text_key], "mode": mode, "model": m}
            for it in items for m in models]
    random.Random(42).shuffle(jobs)
    jobs.sort(key=lambda j: models.index(j["model"]))
    return jobs


def direct_items(cfg: dict) -> list[dict]:
    qs = json.loads(resolve(cfg["probes"]["direct_queries_file"]).read_text(encoding="utf-8"))
    seen: dict[str, int] = {}
    out = []
    for q in qs:  # two direct questions per topic: the variant index keeps message_ids unique
        v = seen[q["topic_id"]] = seen.get(q["topic_id"], -1) + 1
        out.append({"id": q["topic_id"], "variant": v, **q})
    return out


def conf_items(cfg: dict) -> list[dict]:
    return json.loads(resolve(cfg["masking"]["utility_conf_file"]).read_text(encoding="utf-8"))


def collect(cfg: dict, only: list[str] | None = None) -> None:
    """Run all LLM stages (resumable, chunked): masked probe matrices, utility, utility_conf, direct questions."""
    from src.agent.agent import AgentRunner
    models = [m["name"] for m in cfg["models"]]
    util = list(load_utility(cfg).values())
    for name in only or CONDS:
        agent = AgentRunner(cfg, retriever(cfg, name), log_path="")
        mode = mode_of(name)

        def go(jobs, fname):
            path = runs(cfg, fname)
            agent.log_path = str(path)
            chunked_run(jobs, agent, path, cfg)

        if name.startswith("mask_"):  # none/m2/scoped probe matrices and util23 already exist (Faz 6)
            go(build_matrix({**cfg, "acl_modes": [MODE]}, load_probes(), models, None,
                            cfg["probes"]["variants_per_topic"], 1), f"def_{name}_raw.jsonl")
            go(qa_jobs(util, "util", mode, models), f"util_{name}_raw.jsonl")
        go(qa_jobs(conf_items(cfg), "utilconf", mode, models), f"utilconf_{name}.jsonl")
        if name != "scoped":
            go(qa_jobs(direct_items(cfg), "direct", mode, models), f"direct_{name}.jsonl")


def recall(rows: list[dict], items: dict[str, dict]) -> float:
    """Mean fraction of an item's markers found in the answer."""
    vals = [sum(m.lower() in (r["answer_text"] or "").lower() for m in items[r["message_id"].split("|")[0]]["markers"])
            / len(items[r["message_id"].split("|")[0]]["markers"]) for r in rows]
    return float(sum(vals) / len(vals)) if vals else float("nan")


def leak_rate(rows: list[dict], markers: dict[str, list[str]]) -> float:
    """Share of answers on topics that have secret markers containing at least one marker."""
    hits = [any(m.lower() in (r["answer_text"] or "").lower() for m in markers[t])
            for r in rows if (t := r["message_id"].split("|")[0]) in markers]
    return float(sum(hits) / len(hits)) if hits else float("nan")


def probe_df(cfg: dict, name: str) -> pd.DataFrame:
    if name == "none":
        return load_log(runs(cfg, "def_none.jsonl"), cfg)
    if name == "m2":
        df = load_log(resolve(NONE_LOG), cfg)
        return df[df.acl_mode == "M2_strong"].reset_index(drop=True)
    if name == "scoped":
        return load_log(runs(cfg, "def_scoped_context.jsonl"), cfg)
    return load_log(runs(cfg, f"def_{name}_raw.jsonl"), cfg)


def util_path(cfg: dict, name: str, tag: str):
    if tag == "utilconf":
        return runs(cfg, f"utilconf_{name}.jsonl")
    return runs(cfg, {"none": "util_none_raw.jsonl", "m2": "util_m2_raw.jsonl",
                      "scoped": "util_scoped_raw.jsonl"}.get(name, f"util_{name}_raw.jsonl"))


def evaluate(cfg: dict, force: bool = False) -> pd.DataFrame:
    from src.decoders.run_all import run as run_decoders
    ddir = resolve("results/defenses")
    ddir.mkdir(parents=True, exist_ok=True)
    util, conf = load_utility(cfg), {it["id"]: it for it in conf_items(cfg)}
    markers = {q["topic_id"]: q["secret_markers"] for q in direct_items(cfg)}
    none_df = probe_df(cfg, "none")
    parts = []
    for name in CONDS:
        df = probe_df(cfg, name)
        # decoder cache: reuse Faz 6 outputs for the existing conditions
        f = ddir / ({"none": "decoder_none.csv", "m2": "decoder_M2_reference.csv",
                     "scoped": "decoder_scoped_context.csv"}.get(name, f"decoder_{name}.csv"))
        if f.exists() and not force:
            res = pd.read_csv(f)
        else:
            res, stats, _ = run_decoders(df, cfg)
            res.to_csv(f, index=False)
            (ddir / f"stat_tests_{name}.json").write_text(json.dumps(stats, indent=2, default=float), encoding="utf-8")
        for model, cell in df.groupby("model"):
            probe_rows = [{"message_id": r["message_id"], "answer_text": r["answer_text"]}
                          for r in cell.to_dict("records") if r["kind"] == "probe"]
            q = {"leak_probe": leak_rate(probe_rows, markers),
                 "resolution": resolution_rate(cell),
                 "routing_agreement": routing_agreement(cell, none_df[none_df.model == model]),
                 "recall_util23": recall([r for r in read_rows(util_path(cfg, name, "util"))
                                         if r["model"] == model], util),
                 "recall_conf": recall([r for r in read_rows(util_path(cfg, name, "utilconf"))
                                        if r["model"] == model], conf)}
            dpath = runs(cfg, f"direct_{name}.jsonl")
            drows = [r for r in read_rows(dpath) if r["model"] == model] if dpath.exists() else []
            q["leak_direct"] = leak_rate(drows, markers)
            r = res[res.model == model].copy()
            for k, v in q.items():
                r[k] = v
            parts.append(r.assign(condition=name))
    out = pd.concat(parts, ignore_index=True)
    out.to_csv(resolve(cfg["masking"]["results_csv"]), index=False)
    return out


def to_markdown(out: pd.DataFrame) -> str:
    f = lambda x, n=2: "–" if pd.isna(x) else f"{x:.{n}f}"  # noqa: E731
    L = ["# Maskeleme savunması (M1_weak; none = savunmasız, m2 = güçlü ACL, scoped = public-only)", "",
         "| Model | Koşul | Grup | AUC [%95 GA] | p | işaretçi sızıntısı (probe) | doğrudan soru sızıntısı | Çözüm | recall util23 | recall onaylı-cümle |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for _, r in out[out.group.isin(["text", "behavior+text"])].iterrows():
        L.append(f"| {r['model']} | {r['condition']} | {r['group']} | {f(r['auc'])} [{f(r['auc_ci_lo'])}–{f(r['auc_ci_hi'])}] | "
                 f"{f(r['p_topic_perm'], 3)} | {f(r['leak_probe'])} | {f(r['leak_direct'])} | {f(r['resolution'])} | "
                 f"{f(r['recall_util23'])} | {f(r['recall_conf'])} |")
    return "\n".join(L) + "\n"


def main() -> None:
    cfg = load_config()
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["collect", "evaluate"])
    ap.add_argument("--only", nargs="+", choices=list(CONDS))
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    if a.stage == "collect":
        collect(cfg, a.only)
    else:
        out = evaluate(cfg, a.force)
        resolve("results/mask_table.md").write_text(to_markdown(out), encoding="utf-8")
        print(to_markdown(out))


if __name__ == "__main__":
    main()
