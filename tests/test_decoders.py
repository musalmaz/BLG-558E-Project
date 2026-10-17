"""Offline tests for Faz 4 (features, metrics, decoders, controls) on synthetic data."""
import numpy as np
import pandas as pd
import pytest

from src.config import load_config
from src.decoders import metrics as M
from src.decoders import randomized_control as RC
from src.decoders import stat_test as ST
from src.decoders.classifier import assemble, balanced_labelings, loto_scores
from src.decoders.run_all import run
from src.features.behavioral import behavioral_features
from src.features.textual import STYLO_NAMES, embedding_block, stylometry

TOPICS = [f"c0{i}" for i in range(8)]
ROUTES = ["billing", "legal", "operations", "sales"]


def synth(signal: bool, seed: int = 0) -> pd.DataFrame:
    """One (model, mode) cell: 8 topics x {probe, control} x 5 variants."""
    rng = np.random.default_rng(seed)
    rows = []
    for ti, t in enumerate(TOPICS):
        present = int(ti < 4)
        for kind in ("probe", "control"):
            for v in range(5):
                p_esc = 0.9 if (signal and kind == "probe" and present) else 0.1
                rows.append({
                    "message_id": f"{t}|{kind}|v{v}|r0|M1_weak|m", "topic_id": t, "kind": kind,
                    "variant": v, "rep": 0, "acl_mode": "M1_weak", "model": "m", "present": present,
                    "escalated": bool(rng.random() < p_esc),
                    "refusal_type": "cannot_share" if rng.random() < p_esc else "none",
                    "routing_target": ROUTES[int(rng.integers(0, 4))] if not signal else
                    ("legal" if rng.random() < p_esc else ROUTES[int(rng.integers(0, 4))]),
                    "answer_text": f"Sorry, I cannot help with that. Reference {int(rng.integers(0, 99))}.",
                    "latency_ms": float(rng.normal(6000, 500)),
                })
    return pd.DataFrame(rows)


def fake_embed(texts):
    return np.array([np.random.default_rng(abs(hash(t)) % 2**32).normal(size=8) for t in texts])


@pytest.fixture
def cfg():
    c = load_config()
    c["decoders"].update(n_row_perm=10, n_boot=20)
    return c


def test_behavioral_shape(cfg):
    X, names = behavioral_features(synth(True), cfg)
    assert X.shape == (80, len(names)) and names[0] == "escalated"
    assert set(np.unique(X)) <= {0.0, 1.0}


def test_stylometry_22():
    assert len(STYLO_NAMES) == 22 == len(stylometry("Sorry, we cannot share that. Call 713-345-4727!"))
    assert len(stylometry("")) == 22


def test_embedding_cache(tmp_path):
    df = pd.DataFrame({"answer_text": ["a b", "c d", "a b"]})
    calls = []
    emb = lambda ts: (calls.append(len(ts)), np.ones((len(ts), 4)))[1]  # noqa: E731
    embedding_block(df, emb, tmp_path / "c.npz")
    embedding_block(df, emb, tmp_path / "c.npz")
    assert calls == [2]


def test_metrics_known_values():
    y = np.array([0, 0, 0, 0, 1, 1, 1, 1])
    assert M.auc(y, np.arange(8)) == 1.0
    assert M.tpr_at_fpr(y, np.arange(8.0), 0.01) == 1.0
    assert M.tpr_at_fpr(y, np.array([0, 0, 0, 5, 1, 2, 3, 4.0]), 0.01) == 0.0
    x = [0] * 50 + [1] * 50
    assert M.mutual_info_bits(x, x, miller_madow=False) == pytest.approx(1.0)
    assert M.mutual_info_bits([0, 1] * 50, [0] * 50 + [1] * 50) < 0.05
    assert M.leaked_bits_model(y, np.full(8, 0.5)) == 0.0
    assert M.leaked_bits_model(y, np.where(y == 1, 0.999, 0.001)) > 0.95


def test_messages_needed_monotone():
    y = np.repeat([0, 1], 20)
    topics = np.repeat(np.arange(8), 5)
    rng = np.random.default_rng(0)
    s = np.where(y == 1, 0.65, 0.35) + rng.normal(0, 0.2, 40)
    s_clean = np.where(y == 1, 0.9, 0.1)
    assert M.messages_needed(y, s_clean, topics, 0.9, 20, 0) == 1
    assert M.messages_needed(y, rng.random(40), topics, 0.9, 20, 0) is None
    k = M.messages_needed(y, s, topics, 0.9, 50, 0)
    assert k is None or 1 <= k <= 5


def test_loto_has_no_topic_leak(cfg):
    df = synth(True)
    pr = df[df.kind == "probe"]
    X = np.random.default_rng(0).normal(size=(40, 3))
    seen = []
    import src.decoders.classifier as C
    orig = C._fit_predict
    C._fit_predict = lambda Xtr, ytr, Xte, e, c: (seen.append(len(Xtr)), orig(Xtr, ytr, Xte, e, c))[1]
    try:
        loto_scores(X, pr.present.to_numpy(), pr.topic_id.to_numpy(), None, cfg)
    finally:
        C._fit_predict = orig
    assert seen == [35] * 8


def test_balanced_labelings_70():
    assert len(list(balanced_labelings(TOPICS, 4))) == 70


def _xy(df, cfg):
    pr = df[df.kind == "probe"].reset_index(drop=True)
    from src.features.behavioral import latency_features
    beh, _ = behavioral_features(pr, cfg)
    X, _ = assemble({"beh": beh, "lat": latency_features(pr)[0]}, "behavior_nolat")
    return X, pr.present.to_numpy(), pr.topic_id.to_numpy()


def test_planted_signal_detected(cfg):
    X, y, t = _xy(synth(True), cfg)
    assert M.auc(y, loto_scores(X, y, t, None, cfg)) > 0.9
    r = RC.topic_permutation_test(X, t, y, None, cfg)
    assert r["p_topic_perm"] < 0.05 and r["advantage"] > 0.2 and r["n_perm"] == 70


def test_no_signal_no_advantage(cfg):
    advs = []
    for seed in range(3):
        X, y, t = _xy(synth(False, seed), cfg)
        advs.append(RC.topic_permutation_test(X, t, y, None, cfg)["advantage"])
        rs = RC.row_shuffle_test(X, y, t, None, cfg, 0)
        assert abs(rs["row_shuffle_advantage"]) < 0.15
    assert abs(np.mean(advs)) < 0.15


def test_stat_tests(cfg):
    pr = synth(True)
    out = ST.topic_level_tests(pr[pr.kind == "probe"])
    assert out["raw"]["escalated"] < 0.05 and set(out["holm"]) == set(out["raw"])
    assert ST.holm({"a": 0.01, "b": 0.04})["a"] == pytest.approx(0.02)
    assert ST.channel_open(0.01, 0.6) and not ST.channel_open(0.01, 0.45) and not ST.channel_open(0.2, 0.9)
    assert set(ST.probe_vs_control(pr)) == {"escalated", "refused", "answer_chars", "latency_ms"}
    assert all(0 <= v <= 1 for v in ST.row_level_tests(pr[pr.kind == "probe"]).values())


def test_run_all_end_to_end(cfg, tmp_path):
    cfg["decoders"]["embeddings_cache"] = str(tmp_path / "e.npz")
    cfg["decoders"]["groups"] = ["behavior_nolat", "text"]
    res, stats_out, feat = run(synth(True), cfg, embedder=fake_embed)
    assert len(res) == 2 and {"auc", "p_topic_perm", "placebo_auc_control_rows", "channel_open"} <= set(res)
    assert res.loc[res.group == "behavior_nolat", "auc"].iloc[0] > 0.9
    assert "m|M1_weak" in stats_out and len(feat) == 80


def test_loto_intercept_artifact_removed(cfg):
    """Regression: with 4/4 topics, an unbalanced LR gave AUC 0.0 on constant features (prior anticorrelation)."""
    topics = np.repeat(np.arange(8), 5)
    y = (topics < 4).astype(int)
    assert M.auc(y, loto_scores(np.zeros((40, 1)), y, topics, None, cfg)) == 0.5
    noise = [M.auc(y, loto_scores(np.random.default_rng(s).normal(size=(40, 5)), y, topics, None, cfg))
             for s in range(10)]
    assert 0.3 < np.mean(noise) < 0.55  # residual LOTO bias exists; the permutation null accounts for it
