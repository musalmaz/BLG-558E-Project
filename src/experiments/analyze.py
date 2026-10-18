"""Main results table (+ randomized-control rows) and M1 vs M2 comparison from decoder_results.csv."""
import argparse

import numpy as np
import pandas as pd

from src.config import load_config, resolve

METRICS = ["auc", "auc_ci_lo", "auc_ci_hi", "tpr_at_fpr", "messages_needed", "leaked_bits_model",
           "p_topic_perm", "channel_open"]


def main_results(res: pd.DataFrame) -> pd.DataFrame:
    """Long table: one decoder row plus three randomized-control rows per (model, mode, group)."""
    rows = []
    for _, r in res.iterrows():
        key = {"model": r["model"], "acl_mode": r["acl_mode"], "group": r["group"]}
        rows.append({**key, "row_type": "decoder", **{m: r[m] for m in METRICS}})
        for name, auc in (("control_row_shuffle", r["row_shuffle_auc_mean"]),
                          ("control_topic_perm_null", r["null_auc_mean"]),
                          ("control_placebo_control_rows", r["placebo_auc_control_rows"])):
            rows.append({**key, "row_type": name, "auc": auc})
    return pd.DataFrame(rows)


def m1_vs_m2(res: pd.DataFrame) -> pd.DataFrame:
    """Per (model, group): AUC, leaked bits and permutation p under M1 vs M2 and their differences."""
    a = res[res.acl_mode == "M1_weak"].set_index(["model", "group"])
    b = res[res.acl_mode == "M2_strong"].set_index(["model", "group"])
    out = pd.DataFrame({
        "auc_M1": a["auc"], "auc_M2": b["auc"], "delta_auc": a["auc"] - b["auc"],
        "bits_M1": a["leaked_bits_model"], "bits_M2": b["leaked_bits_model"],
        "delta_bits": a["leaked_bits_model"] - b["leaked_bits_model"],
        "p_M1": a["p_topic_perm"], "p_M2": b["p_topic_perm"]})
    return out.reset_index()


def _f(x, nd=2) -> str:
    return "–" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x:.{nd}f}"


def to_markdown(long: pd.DataFrame, cmp: pd.DataFrame) -> str:
    """Readable main table; control rows in italics, then the M1 vs M2 table."""
    out = ["# Ana tablo (LOTO decoder, konu düzeyi permütasyon p)", "",
           "| Model | ACL | Grup | AUC [%95 GA] | TPR@1%FPR | Mesaj | Sızan bit/mesaj | p (konu perm.) | Kanal açık |",
           "|---|---|---|---|---|---|---|---|---|"]
    for _, r in long.iterrows():
        if r["row_type"] == "decoder":
            mn = r["messages_needed"]
            out.append(f"| {r['model']} | {r['acl_mode']} | {r['group']} | {_f(r['auc'])} "
                       f"[{_f(r['auc_ci_lo'])}–{_f(r['auc_ci_hi'])}] | {_f(r['tpr_at_fpr'])} | "
                       f"{'>5' if pd.isna(mn) else int(mn)} | {_f(r['leaked_bits_model'], 3)} | "
                       f"{_f(r['p_topic_perm'], 3)} | {'evet' if r['channel_open'] else 'hayır'} |")
        else:
            label = r["row_type"].replace("control_", "").replace("_", " ")
            out.append(f"| *{r['model']}* | *{r['acl_mode']}* | *{r['group']}* | *{label}: AUC {_f(r['auc'])}* | | | | | |")
    out += ["", "# M1 vs M2", "",
            "| Model | Grup | AUC M1 | AUC M2 | ΔAUC | bit M1 | bit M2 | Δbit | p M1 | p M2 |",
            "|---|---|---|---|---|---|---|---|---|---|"]
    for _, r in cmp.iterrows():
        out.append(f"| {r['model']} | {r['group']} | {_f(r['auc_M1'])} | {_f(r['auc_M2'])} | {_f(r['delta_auc'])} | "
                   f"{_f(r['bits_M1'], 3)} | {_f(r['bits_M2'], 3)} | {_f(r['delta_bits'], 3)} | "
                   f"{_f(r['p_M1'], 3)} | {_f(r['p_M2'], 3)} |")
    return "\n".join(out) + "\n"


def main() -> None:
    cfg = load_config()
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default=cfg["decoders"]["results_csv"])
    a = ap.parse_args()
    res = pd.read_csv(resolve(a.results))
    long, cmp = main_results(res), m1_vs_m2(res)
    long.to_csv(resolve("results/main_results.csv"), index=False)
    cmp.to_csv(resolve("results/m1_vs_m2.csv"), index=False)
    resolve("results/main_table.md").write_text(to_markdown(long, cmp), encoding="utf-8")
    print(to_markdown(long, cmp))


if __name__ == "__main__":
    main()
