"""Security-utility trade-off figure: leakage (AUC) vs. utility loss per defense."""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

MARK = {"none": "o", "behavior_norm": "s", "scoped_context": "^", "decision_hiding": "D", "all": "*",
        "M2_reference": "X"}


def security_utility_figure(out: pd.DataFrame, path, group: str = "behavior+text") -> None:
    """One panel per model; x = utility recall loss vs. undefended, y = LOTO AUC of `group`; dashed = chance."""
    models = sorted(out.model.unique())
    fig, axes = plt.subplots(1, len(models), figsize=(5.2 * len(models), 4.2), sharey=True, squeeze=False)
    for ax, model in zip(axes[0], models):
        d = out[(out.model == model) & (out.group == group)]
        for _, r in d.iterrows():
            ax.errorbar(r.recall_loss, r.auc, yerr=[[r.auc - r.auc_ci_lo], [r.auc_ci_hi - r.auc]],
                        fmt=MARK[r.defense], ms=9, capsize=3, label=r.defense)
        ax.axhline(0.5, ls="--", color="k", lw=0.8)
        ax.axvline(0, color="gray", lw=0.5)
        ax.set_title(f"{model} — {group}")
        ax.set_xlabel("utility loss (recall drop vs. no defense)")
        ax.set_ylim(0, 1)
    axes[0][0].set_ylabel("LOTO AUC (lower = safer)")
    axes[0][0].legend(fontsize=7, loc="lower left", ncol=2)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
