"""Randomized controls: topic-level exact label permutation, row-level shuffle, placebo on control rows."""
import numpy as np

from src.decoders import metrics as M
from src.decoders.classifier import balanced_labelings, loto_scores


def topic_permutation_test(X, topics, true_y, emb_idx, cfg) -> dict:
    """Run the same LOTO decoder under every balanced topic relabeling (incl. the true one).

    p = share of labelings with AUC >= the true AUC (one-sided, min 1/70 for 4 of 8 topics);
    advantage = true AUC - mean null AUC (should be ~0 when there is no signal).
    """
    topics, true_y = np.asarray(topics), np.asarray(true_y)
    ids = sorted(set(topics))
    truth = {t: int(true_y[topics == t][0]) for t in ids}
    real = M.auc(true_y, loto_scores(X, true_y, topics, emb_idx, cfg))
    null = []
    for lab in balanced_labelings(ids, sum(truth.values())):
        if lab == truth:
            continue
        y = np.array([lab[t] for t in topics])
        null.append(M.auc(y, loto_scores(X, y, topics, emb_idx, cfg)))
    null = np.array(null)
    return {"real_auc": real, "null_mean": float(null.mean()), "null_sd": float(null.std()),
            "advantage": float(real - null.mean()),
            "p_topic_perm": float((1 + np.sum(null >= real)) / (1 + len(null))), "n_perm": len(null) + 1}


def row_shuffle_test(X, y, topics, emb_idx, cfg, seed: int) -> dict:
    """Shuffle row labels (classic randomized control) and re-run LOTO; AUC should hover near 0.5."""
    rng = np.random.default_rng(seed)
    y = np.asarray(y)
    aucs = []
    for _ in range(cfg["decoders"]["n_row_perm"]):
        ys = rng.permutation(y)
        aucs.append(M.auc(ys, loto_scores(X, ys, topics, emb_idx, cfg)))
    return {"row_shuffle_auc_mean": float(np.mean(aucs)), "row_shuffle_auc_sd": float(np.std(aucs)),
            "row_shuffle_advantage": float(np.mean(aucs) - 0.5)}


def placebo_auc(Xc, yc, topics_c, emb_idx, cfg) -> float:
    """Same decoder on CONTROL rows labeled with the topic's predicate; ~0.5 expected (controls are unrelated)."""
    return M.auc(yc, loto_scores(Xc, yc, topics_c, emb_idx, cfg))
