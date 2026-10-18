"""Figures: AUC (M1 vs M2) with CI and control line; leaked bits M1 vs M2."""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from src.config import resolve  # noqa: E402

COLORS = {"M1_weak": "#c0392b", "M2_strong": "#2471a3"}


def auc_figure(res: pd.DataFrame, path) -> None:
    """One panel per model: AUC with bootstrap CI for each feature group, M1 vs M2; dashed line = chance."""
    models = sorted(res.model.unique())
    groups = list(dict.fromkeys(res.group))
    fig, axes = plt.subplots(1, len(models), figsize=(5.5 * len(models), 4), sharey=True, squeeze=False)
    for ax, model in zip(axes[0], models):
        for j, mode in enumerate(("M1_weak", "M2_strong")):
            c = res[(res.model == model) & (res.acl_mode == mode)].set_index("group").reindex(groups)
            x = np.arange(len(groups)) + (j - 0.5) * 0.3
            ax.errorbar(x, c.auc, yerr=[c.auc - c.auc_ci_lo, c.auc_ci_hi - c.auc], fmt="o", capsize=3,
                        color=COLORS[mode], label=mode)
            ax.scatter(x, c.row_shuffle_auc_mean, marker="x", color="gray", zorder=3,
                       label="row-shuffle control" if j == 0 else None)
        ax.axhline(0.5, ls="--", color="k", lw=0.8)
        ax.set_xticks(range(len(groups)), groups, rotation=20)
        ax.set_title(model)
        ax.set_ylim(0, 1)
    axes[0][0].set_ylabel("LOTO AUC")
    axes[0][0].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def bits_figure(res: pd.DataFrame, path) -> None:
    """Model-based leaked bits per message, M1 vs M2, per (model, group)."""
    r = res.assign(cell=res.model + "\n" + res.group)
    cells = list(dict.fromkeys(r.cell))
    fig, ax = plt.subplots(figsize=(max(6, 0.9 * len(cells)), 4))
    for j, mode in enumerate(("M1_weak", "M2_strong")):
        c = r[r.acl_mode == mode].set_index("cell").reindex(cells)
        ax.bar(np.arange(len(cells)) + (j - 0.5) * 0.4, c.leaked_bits_model, 0.4, color=COLORS[mode], label=mode)
    ax.set_xticks(range(len(cells)), cells, fontsize=7)
    ax.set_ylabel("leaked bits / message (model-based)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def main() -> None:
    res = pd.read_csv(resolve("results/decoder_results.csv"))
    d = resolve("results/figures")
    d.mkdir(parents=True, exist_ok=True)
    auc_figure(res, d / "auc_m1_vs_m2.png")
    bits_figure(res, d / "leaked_bits_m1_vs_m2.png")
    print("saved", [p.name for p in d.glob("*.png")])


if __name__ == "__main__":
    main()
