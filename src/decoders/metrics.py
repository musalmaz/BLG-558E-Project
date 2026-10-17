"""Pure metric functions: AUC (+topic bootstrap CI), TPR@FPR, messages needed, leaked bits."""
from collections import Counter

import numpy as np
from sklearn.metrics import roc_auc_score


def auc(y, s) -> float:
    """ROC AUC; 0.5 if only one class is present."""
    y = np.asarray(y)
    return float(roc_auc_score(y, s)) if len(set(y)) == 2 else 0.5


def bootstrap_auc_ci(y, s, topics, n_boot: int, seed: int) -> tuple[float, float]:
    """95% CI of AUC from resampling whole topics (rows of a topic are not independent)."""
    y, s, topics = map(np.asarray, (y, s, topics))
    rng = np.random.default_rng(seed)
    uniq = np.unique(topics)
    idx = {t: np.where(topics == t)[0] for t in uniq}
    vals = []
    for _ in range(n_boot):
        pick = np.concatenate([idx[t] for t in rng.choice(uniq, len(uniq))])
        vals.append(auc(y[pick], s[pick]))
    return float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))


def tpr_at_fpr(y, s, fpr: float = 0.01) -> float:
    """TPR at the strictest threshold whose FPR <= fpr (ties count as positives)."""
    y, s = np.asarray(y), np.asarray(s)
    neg, pos = s[y == 0], s[y == 1]
    if len(neg) == 0 or len(pos) == 0:
        return 0.0
    allowed = int(np.floor(fpr * len(neg)))
    thr = np.sort(neg)[::-1][allowed] if allowed < len(neg) else -np.inf
    return float(np.mean(pos > thr))


def topic_auc(y_topic: dict, scores_by_topic: dict, k: int, rng) -> float:
    """AUC over topics where each topic score is the mean of k randomly chosen message scores."""
    ts = sorted(scores_by_topic)
    sc = [np.mean(rng.choice(scores_by_topic[t], min(k, len(scores_by_topic[t])), replace=False)) for t in ts]
    return auc([y_topic[t] for t in ts], sc)


def messages_needed(y, s, topics, target: float, n_boot: int, seed: int, k_max: int = 5):
    """Smallest k (messages per topic, scores averaged) with mean topic-level AUC >= target; None if never."""
    y, s, topics = map(np.asarray, (y, s, topics))
    y_topic = {t: int(y[topics == t][0]) for t in np.unique(topics)}
    by_topic = {t: s[topics == t] for t in y_topic}
    rng = np.random.default_rng(seed)
    kmax = min(k_max, min(len(v) for v in by_topic.values()))
    for k in range(1, kmax + 1):
        if np.mean([topic_auc(y_topic, by_topic, k, rng) for _ in range(n_boot)]) >= target:
            return k
    return None


def _entropy_bits(p: float) -> float:
    return 0.0 if p in (0.0, 1.0) else float(-(p * np.log2(p) + (1 - p) * np.log2(1 - p)))


def leaked_bits_model(y, p) -> float:
    """H(Y) - cross-entropy of out-of-fold probabilities, bits/message, clipped at 0 (lower bound on I)."""
    y, p = np.asarray(y, float), np.clip(np.asarray(p, float), 1e-6, 1 - 1e-6)
    ce = float(-np.mean(y * np.log2(p) + (1 - y) * np.log2(1 - p)))
    return max(0.0, _entropy_bits(float(y.mean())) - ce)


def mutual_info_bits(x, y, miller_madow: bool = True) -> float:
    """Plug-in I(X;Y) in bits for discrete X (e.g. behavior tuple), optional Miller-Madow bias correction."""
    x, y = list(x), list(y)
    n = len(x)
    cxy, cx, cy = Counter(zip(x, y)), Counter(x), Counter(y)
    mi = sum(c / n * np.log2(c * n / (cx[a] * cy[b])) for (a, b), c in cxy.items())
    if miller_madow:
        mi -= (len(cx) - 1) * (len(cy) - 1) / (2 * n * np.log(2))
    return max(0.0, float(mi))
