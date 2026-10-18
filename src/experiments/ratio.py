"""Ratio sweep: leakage vs. number of confidential canary docs per topic (M1_weak only)."""
import argparse

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from src.config import load_config, resolve  # noqa: E402

COLS = ["model", "group", "docs_per_topic", "auc", "auc_ci_lo", "auc_ci_hi", "tpr_at_fpr",
        "leaked_bits_model", "p_topic_perm", "row_shuffle_auc_mean"]


def ratio_table(frames: dict[int, pd.DataFrame]) -> pd.DataFrame:
    """Stack M1_weak decoder rows of each k (docs per topic) into one table."""
    parts = [f[f.acl_mode == "M1_weak"].assign(docs_per_topic=k) for k, f in sorted(frames.items())]
    return pd.concat(parts)[COLS].reset_index(drop=True)


def ratio_figure(tab: pd.DataFrame, path) -> None:
    """One panel per model: AUC vs k for each feature group; dashed line = chance."""
    models = sorted(tab.model.unique())
    fig, axes = plt.subplots(1, len(models), figsize=(5 * len(models), 4), sharey=True, squeeze=False)
    for ax, model in zip(axes[0], models):
        for g, c in tab[tab.model == model].groupby("group", sort=False):
            ax.errorbar(c.docs_per_topic, c.auc, yerr=[c.auc - c.auc_ci_lo, c.auc_ci_hi - c.auc],
                        marker="o", capsize=3, label=g)
        ax.axhline(0.5, ls="--", color="k", lw=0.8)
        ax.set_xticks(sorted(tab.docs_per_topic.unique()))
        ax.set_xlabel("confidential docs per topic")
        ax.set_title(f"{model} (M1_weak)")
        ax.set_ylim(0, 1)
    axes[0][0].set_ylabel("LOTO AUC")
    axes[0][0].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def to_markdown(tab: pd.DataFrame) -> str:
    out = ["# Gizli belge sayısı taraması (M1_weak)", "",
           "| Model | Grup | Belge/konu | AUC [%95 GA] | TPR@1%FPR | Sızan bit/mesaj | p (konu perm.) |",
           "|---|---|---|---|---|---|---|"]
    for _, r in tab.iterrows():
        out.append(f"| {r['model']} | {r['group']} | {int(r['docs_per_topic'])} | {r['auc']:.2f} "
                   f"[{r['auc_ci_lo']:.2f}–{r['auc_ci_hi']:.2f}] | {r['tpr_at_fpr']:.2f} | "
                   f"{r['leaked_bits_model']:.3f} | {r['p_topic_perm']:.3f} |")
    return "\n".join(out) + "\n"


def main() -> None:
    cfg = load_config()
    ap = argparse.ArgumentParser()
    ap.add_argument("--ks", nargs="+", type=int, default=[1, 2])
    ap.add_argument("--full-k", type=int, default=3, help="docs per topic of the full-matrix baseline")
    a = ap.parse_args()
    base = cfg["decoders"]["results_csv"]
    frames = {a.full_k: pd.read_csv(resolve(base))}
    for k in a.ks:
        frames[k] = pd.read_csv(resolve(base.replace(".csv", f"_k{k}.csv")))
    tab = ratio_table(frames)
    tab.to_csv(resolve("results/ratio_results.csv"), index=False)
    resolve("results/ratio_table.md").write_text(to_markdown(tab), encoding="utf-8")
    d = resolve("results/figures")
    d.mkdir(parents=True, exist_ok=True)
    ratio_figure(tab, d / "auc_vs_docs_per_topic.png")
    print(to_markdown(tab))


if __name__ == "__main__":
    main()
