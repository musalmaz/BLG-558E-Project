"""Ratio sweep sanity check: how many confidential docs reach the top-k context, per docs_per_topic."""
import pandas as pd

from src.config import load_config, resolve
from src.features.dataset import load_log

LOGS = {1: "results/runs/ratio_k1.jsonl", 2: "results/runs/ratio_k2.jsonl",
        3: "results/runs/probe_matrix_20topics_repeats1.jsonl"}


def retrieval_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Per (model, kind, present): mean #confidential in top-k, share with >=1, share retrieving own-topic canary."""
    d = df.copy()
    d["n_conf"] = d.retrieved_acl_labels.map(lambda x: sum(a == "confidential" for a in x))
    d["own_canary"] = [any(i.startswith(f"canary_{t}_") for i in ids)
                       for ids, t in zip(d.retrieved_doc_ids, d.topic_id)]
    g = d.groupby(["model", "kind", "present"])
    return g.agg(n=("n_conf", "size"), mean_conf=("n_conf", "mean"),
                 any_conf=("n_conf", lambda s: (s > 0).mean()), own_canary=("own_canary", "mean")).reset_index()


def main() -> None:
    cfg = load_config()
    parts = []
    for k, p in LOGS.items():
        df = load_log(p, cfg)
        parts.append(retrieval_stats(df[df.acl_mode == "M1_weak"]).assign(docs_per_topic=k))
    out = pd.concat(parts)[["docs_per_topic", "model", "kind", "present", "n", "mean_conf", "any_conf", "own_canary"]]
    out.to_csv(resolve("results/ratio_retrieval.csv"), index=False)
    print(out.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
