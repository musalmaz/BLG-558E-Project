"""Load agent_log.jsonl into a labeled DataFrame (probe/control rows only)."""
import json
from pathlib import Path

import pandas as pd

from src.config import load_config, resolve
from src.probes.runner import parse_id


def present_map(cfg: dict | None = None) -> dict[str, int]:
    """topic_id -> predicate (1 = confidential docs exist for the topic)."""
    cfg = cfg or load_config()
    f = json.loads((resolve(cfg["data"]["canaries_dir"]) / "canaries.json").read_text(encoding="utf-8"))
    return {c["topic_id"]: int(c["present"]) for c in f["canaries"]}


def load_log(path: str | Path | None = None, cfg: dict | None = None) -> pd.DataFrame:
    """Rows with topic_id, kind, variant, rep, acl_mode, model, present; drops baseline and parse errors."""
    cfg = cfg or load_config()
    path = Path(path) if path else resolve(cfg["paths"]["agent_log"])
    pm = present_map(cfg)
    rows = []
    for ln in open(path, encoding="utf-8"):
        r = json.loads(ln)
        if r["message_id"].startswith("baseline") or r["parse_error"]:
            continue
        if len(r["message_id"].split("|")) != 6:
            continue
        r.update(parse_id(r["message_id"]))
        r["present"] = pm[r["topic_id"]]
        rows.append(r)
    df = pd.DataFrame(rows)
    return df.drop_duplicates("message_id", keep="last").reset_index(drop=True)
