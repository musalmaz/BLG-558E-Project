"""Predicate decoder: fixed logistic regression, leave-one-topic-out evaluation per feature group."""
from itertools import combinations
from math import comb

import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.decomposition import PCA
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from src.decoders import metrics as M

GROUPS = {
    "behavior_nolat": ["beh"],
    "behavior": ["beh", "lat"],
    "text": ["stylo", "emb"],
    "behavior+text": ["beh", "lat", "stylo", "emb"],
}


def assemble(blocks: dict[str, np.ndarray], group: str) -> tuple[np.ndarray, list[int] | None]:
    """Concatenate the group's blocks; return (X, embedding column indices or None)."""
    parts, emb_idx, col = [], None, 0
    for k in GROUPS[group]:
        a = blocks[k]
        if k == "emb":
            emb_idx = list(range(col, col + a.shape[1]))
        parts.append(a)
        col += a.shape[1]
    return np.hstack(parts), emb_idx


def make_model(n_cols: int, emb_idx: list[int] | None, cfg: dict):
    """Scaler (+ PCA on the embedding block) -> scaler -> L2 logistic regression with fixed C."""
    d = cfg["decoders"]
    emb = set(emb_idx or [])
    num_idx = [i for i in range(n_cols) if i not in emb]
    tr = []
    if num_idx:
        tr.append(("num", StandardScaler(), num_idx))
    if emb:
        tr.append(("emb", PCA(n_components=min(d["pca_components"], len(emb)), svd_solver="full"), sorted(emb)))
    return make_pipeline(ColumnTransformer(tr), StandardScaler(),
                         LogisticRegression(C=d["C"], max_iter=1000, class_weight="balanced"))


def _fit_predict(Xtr, ytr, Xte, emb_idx, cfg) -> np.ndarray:
    if len(set(ytr)) < 2:
        return np.full(len(Xte), 0.5)
    m = make_model(Xtr.shape[1], emb_idx, cfg)
    m.fit(Xtr, ytr)
    return m.predict_proba(Xte)[:, 1]


def loto_scores(X, y, topics, emb_idx, cfg) -> np.ndarray:
    """Out-of-fold P(present): each topic is scored by a model that never saw any variant of it."""
    y, topics = np.asarray(y), np.asarray(topics)
    out = np.zeros(len(y))
    for t in np.unique(topics):
        te = topics == t
        out[te] = _fit_predict(X[~te], y[~te], X[te], emb_idx, cfg)
    return out


def rowcv_scores(X, y, emb_idx, cfg, seed: int) -> np.ndarray:
    """Row-level stratified 5-fold (INFLATED reference: variants of one topic leak across folds)."""
    y = np.asarray(y)
    out = np.zeros(len(y))
    for tr, te in StratifiedKFold(5, shuffle=True, random_state=seed).split(X, y):
        out[te] = _fit_predict(X[tr], y[tr], X[te], emb_idx, cfg)
    return out


def balanced_labelings(topic_ids: list[str], n_pos: int):
    """All ways to label n_pos of the topics positive (70 for 4 of 8)."""
    for pos in combinations(topic_ids, n_pos):
        yield {t: int(t in pos) for t in topic_ids}


def labelings(topic_ids: list[str], n_pos: int, max_exact: int, n_mc: int, seed: int) -> tuple[list[dict], bool]:
    """Balanced topic relabelings: all of them if C(n, k) <= max_exact, else n_mc distinct random ones.

    Returns (labelings, exact). Monte-Carlo p-values should use (1 + #>=) / (1 + N).
    """
    if comb(len(topic_ids), n_pos) <= max_exact:
        return list(balanced_labelings(topic_ids, n_pos)), True
    rng = np.random.default_rng(seed)
    seen: set[tuple] = set()
    while len(seen) < n_mc:
        seen.add(tuple(sorted(rng.choice(len(topic_ids), n_pos, replace=False))))
    return [{t: int(i in pos) for i, t in enumerate(topic_ids)} for pos in sorted(seen)], False


def evaluate_group(X, y, topics, emb_idx, cfg, seed: int) -> dict:
    """LOTO metrics for one feature group on probe rows."""
    d = cfg["decoders"]
    s = loto_scores(X, y, topics, emb_idx, cfg)
    lo, hi = M.bootstrap_auc_ci(y, s, topics, d["n_boot"], seed)
    return {
        "auc": M.auc(y, s), "auc_ci_lo": lo, "auc_ci_hi": hi,
        "tpr_at_fpr": M.tpr_at_fpr(y, s, d["fpr"]),
        "messages_needed": M.messages_needed(y, s, topics, d["auc_target"], d["n_boot"], seed),
        "leaked_bits_model": M.leaked_bits_model(y, s),
        "auc_rowcv_inflated": M.auc(y, rowcv_scores(X, y, emb_idx, cfg, seed)),
        "scores": s,
    }
