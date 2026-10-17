"""Agent-level behavioral features: escalation, refusal type, routing (+ latency as a separate block)."""
import numpy as np
import pandas as pd

from src.config import load_config

REFUSALS = ["none", "no_info", "cannot_share", "deflect"]


def behavioral_features(df: pd.DataFrame, cfg: dict | None = None) -> tuple[np.ndarray, list[str]]:
    """escalated (0/1) + refusal_type one-hot + routing_target one-hot (fixed set + other)."""
    cfg = cfg or load_config()
    routes = list(cfg["agent"]["routing_targets"]) + ["other"]
    cols = {"escalated": df["escalated"].astype(float).to_numpy()}
    for r in REFUSALS:
        cols[f"refusal={r}"] = (df["refusal_type"] == r).astype(float).to_numpy()
    for t in routes:
        cols[f"route={t}"] = (df["routing_target"] == t).astype(float).to_numpy()
    return np.column_stack(list(cols.values())), list(cols)


def latency_features(df: pd.DataFrame) -> tuple[np.ndarray, list[str]]:
    """log1p(latency_ms): weak channel, kept as its own block."""
    return np.log1p(df["latency_ms"].astype(float).to_numpy())[:, None], ["log_latency_ms"]
