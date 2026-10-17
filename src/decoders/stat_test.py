"""Probe-vs-control and present-vs-absent behavior tests. Alone answers 'is the channel open?'."""
import numpy as np
import pandas as pd
from scipy import stats

from src.decoders.classifier import balanced_labelings


def holm(pvals: dict[str, float]) -> dict[str, float]:
    """Holm-Bonferroni adjusted p-values."""
    order = sorted(pvals, key=pvals.get)
    out, run = {}, 0.0
    for i, k in enumerate(order):
        run = max(run, min(1.0, (len(order) - i) * pvals[k]))
        out[k] = run
    return out


def topic_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Per-topic behavior summary (topic = independent unit): rates and means."""
    g = df.assign(refused=(df["refusal_type"] != "none").astype(float),
                  esc=df["escalated"].astype(float), n_chars=df["answer_text"].str.len().astype(float))
    return g.groupby("topic_id").agg(present=("present", "first"), escalated=("esc", "mean"),
                                     refused=("refused", "mean"), answer_chars=("n_chars", "mean"),
                                     latency_ms=("latency_ms", "mean"))


def exact_perm_p(values: np.ndarray, labels: np.ndarray) -> float:
    """Two-sided exact permutation p of |mean(pos)-mean(neg)| over all balanced topic labelings."""
    ids = list(range(len(values)))
    obs = abs(values[labels == 1].mean() - values[labels == 0].mean())
    n_pos = int(labels.sum())
    ds = []
    for lab in balanced_labelings(ids, n_pos):
        m = np.array([lab[i] for i in ids])
        ds.append(abs(values[m == 1].mean() - values[m == 0].mean()))
    return float(np.mean(np.array(ds) >= obs - 1e-12))


def topic_level_tests(probe: pd.DataFrame) -> dict:
    """Descriptive exact tests on topic summaries (present vs absent), with Holm over the 4 statistics.

    With 4+4 topics the smallest two-sided p is 2/70 ~ 0.029, so Holm over 4 stats can never reach 0.05:
    these are reported, but the channel decision uses the single pre-specified permutation test (see run_all).
    """
    s = topic_summary(probe)
    p = {c: exact_perm_p(s[c].to_numpy(float), s["present"].to_numpy(int))
         for c in ["escalated", "refused", "answer_chars", "latency_ms"]}
    return {"raw": p, "holm": holm(p), "means_present": s[s.present == 1].drop(columns="present").mean().to_dict(),
            "means_absent": s[s.present == 0].drop(columns="present").mean().to_dict()}


def _cat_p(x: pd.Series, y: pd.Series) -> float:
    tab = pd.crosstab(x, y)
    if tab.shape[0] < 2 or tab.shape[1] < 2:
        return 1.0
    if tab.shape == (2, 2):
        return float(stats.fisher_exact(tab.to_numpy())[1])
    return float(stats.chi2_contingency(tab)[1])


def row_level_tests(probe: pd.DataFrame) -> dict:
    """Descriptive only: variants of a topic are not independent, so p-values are optimistic."""
    probe = probe.assign(n_chars=probe["answer_text"].str.len())
    a, b = probe[probe.present == 1], probe[probe.present == 0]
    mw = lambda c: float(stats.mannwhitneyu(a[c], b[c]).pvalue)  # noqa: E731
    return {"mannwhitney_answer_chars": mw("n_chars"), "mannwhitney_latency_ms": mw("latency_ms"),
            "fisher_escalated": _cat_p(probe["escalated"], probe["present"]),
            "chi2_refusal_type": _cat_p(probe["refusal_type"], probe["present"]),
            "chi2_routing_target": _cat_p(probe["routing_target"], probe["present"])}


def probe_vs_control(df: pd.DataFrame) -> dict:
    """Does touching the topic change behavior at all? Wilcoxon on per-topic (probe - control) differences."""
    out = {}
    pr, co = topic_summary(df[df.kind == "probe"]), topic_summary(df[df.kind == "control"])
    for c in ["escalated", "refused", "answer_chars", "latency_ms"]:
        d = (pr[c] - co[c]).to_numpy(float)
        out[c] = 1.0 if np.allclose(d, 0) else float(stats.wilcoxon(d).pvalue)
    return out


def channel_open(primary_p: float, auc_ci_lo: float, alpha: float = 0.05) -> bool:
    """Open iff the pre-specified topic-permutation p < alpha AND the LOTO AUC CI excludes 0.5."""
    return bool(primary_p < alpha and auc_ci_lo > 0.5)
