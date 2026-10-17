"""Faz 4 driver: features + decoders + randomized controls + stat tests per (model, mode) cell."""
import argparse
import json

import numpy as np
import pandas as pd

from src.config import load_config, resolve
from src.decoders import metrics as M
from src.decoders import randomized_control as RC
from src.decoders import stat_test as ST
from src.decoders.classifier import GROUPS, assemble, evaluate_group
from src.features.behavioral import behavioral_features, latency_features
from src.features.dataset import load_log
from src.features.textual import embedding_block, stylo_block


def build_blocks(df: pd.DataFrame, cfg: dict, embedder=None) -> tuple[dict, dict]:
    """Feature blocks aligned with df rows, plus their column names."""
    beh, beh_n = behavioral_features(df, cfg)
    lat, lat_n = latency_features(df)
    sty, sty_n = stylo_block(df)
    emb = embedding_block(df, embedder, resolve(cfg["decoders"]["embeddings_cache"]),
                          cfg["index"]["embedding_model"])
    return ({"beh": beh, "lat": lat, "stylo": sty, "emb": emb},
            {"beh": beh_n, "lat": lat_n, "stylo": sty_n})


def run(df: pd.DataFrame, cfg: dict, embedder=None) -> tuple[pd.DataFrame, dict, pd.DataFrame]:
    """Return (results table, stat tests, feature table) for all cells in df."""
    d = cfg["decoders"]
    blocks, names = build_blocks(df, cfg, embedder)
    feat = pd.concat([df[["message_id", "topic_id", "kind", "acl_mode", "model", "present"]],
                      pd.DataFrame(np.hstack([blocks[k] for k in ("beh", "lat", "stylo")]),
                                   columns=names["beh"] + names["lat"] + names["stylo"])], axis=1)
    rows, stats_out = [], {}
    for (model, mode), cell in df.groupby(["model", "acl_mode"]):
        pi = cell.index[cell.kind == "probe"].to_numpy()
        ci = cell.index[cell.kind == "control"].to_numpy()
        y, topics = cell.loc[pi, "present"].to_numpy(), cell.loc[pi, "topic_id"].to_numpy()
        yc, tc = cell.loc[ci, "present"].to_numpy(), cell.loc[ci, "topic_id"].to_numpy()
        key = f"{model}|{mode}"
        stats_out[key] = {
            "topic_level": ST.topic_level_tests(cell.loc[pi]),
            "row_level_descriptive": ST.row_level_tests(cell.loc[pi]),
            "probe_vs_control": ST.probe_vs_control(cell),
            "behavior_tuple_mi_bits": M.mutual_info_bits(
                list(zip(cell.loc[pi, "escalated"], cell.loc[pi, "refusal_type"],
                         cell.loc[pi, "routing_target"])), y),
        }
        for g in d["groups"]:
            X, emb_idx = assemble({k: v[pi] for k, v in blocks.items()}, g)
            Xc, _ = assemble({k: v[ci] for k, v in blocks.items()}, g)
            ev = evaluate_group(X, y, topics, emb_idx, cfg, d["seed"])
            tp = RC.topic_permutation_test(X, topics, y, emb_idx, cfg)
            rs = RC.row_shuffle_test(X, y, topics, emb_idx, cfg, d["seed"])
            ev.pop("scores")
            rows.append({"model": model, "acl_mode": mode, "group": g, "n_probe_rows": len(pi), **ev,
                         "p_topic_perm": tp["p_topic_perm"], "advantage_topic_perm": tp["advantage"],
                         "null_auc_mean": tp["null_mean"], **rs,
                         "placebo_auc_control_rows": RC.placebo_auc(Xc, yc, tc, emb_idx, cfg),
                         "channel_open": ST.channel_open(tp["p_topic_perm"], ev["auc_ci_lo"])})
            print(f"[{key}|{g}] AUC={ev['auc']:.2f} p={tp['p_topic_perm']:.3f}", flush=True)
    return pd.DataFrame(rows), stats_out, feat


def main() -> None:
    cfg = load_config()
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", default=cfg["paths"]["agent_log"])
    a = ap.parse_args()
    df = load_log(resolve(a.log), cfg)
    res, stats_out, feat = run(df, cfg)
    d = cfg["decoders"]
    res.to_csv(resolve(d["results_csv"]), index=False)
    feat.to_csv(resolve(d["features_csv"]), index=False)
    resolve(d["stat_tests_json"]).write_text(json.dumps(stats_out, indent=2, default=float), encoding="utf-8")
    pd.set_option("display.width", 200)
    print(res[["model", "acl_mode", "group", "auc", "auc_ci_lo", "auc_ci_hi", "tpr_at_fpr",
               "messages_needed", "leaked_bits_model", "p_topic_perm", "advantage_topic_perm",
               "row_shuffle_auc_mean", "placebo_auc_control_rows", "channel_open"]].round(3).to_string())


if __name__ == "__main__":
    main()
