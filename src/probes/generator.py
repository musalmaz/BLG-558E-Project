"""Load and validate the paired probe/control message set (hand-authored, no injection)."""
import json
import re
import sys
from collections import Counter
from pathlib import Path

from src.config import load_config, resolve

INSTRUCTION_RE = re.compile(
    r"\b(ignore|disregard|previous instructions?|system prompt|reveal|print|override|"
    r"jailbreak|pretend|you must|act as)\b", re.IGNORECASE)


def load_probes(path: str | Path | None = None) -> dict:
    """Return {"topics": {tid: {"keywords": [...]}}, "items": [...]}."""
    cfg = load_config()
    p = Path(path) if path else resolve(cfg["probes"]["probes_file"])
    return json.loads(p.read_text(encoding="utf-8"))


def validate_probes(data: dict, m: int, tolerance: float) -> list[str]:
    """Return a list of problems (empty = valid)."""
    problems: list[str] = []
    items, topics = data["items"], data["topics"]
    all_kw = [k.lower() for t in topics.values() for k in t["keywords"]]
    by = {(i["topic_id"], i["kind"], i["variant"]): i["text"] for i in items}
    for tid, t in topics.items():
        for v in range(m):
            p, c = by.get((tid, "probe", v)), by.get((tid, "control", v))
            if p is None or c is None:
                problems.append(f"{tid} v{v}: missing probe or control")
                continue
            if not any(k.lower() in p.lower() for k in t["keywords"]):
                problems.append(f"{tid} v{v}: probe lacks topic keyword")
            if any(k in c.lower() for k in all_kw):
                problems.append(f"{tid} v{v}: control contains a canary keyword")
            if abs(len(p) - len(c)) / max(len(p), len(c)) > tolerance:
                problems.append(f"{tid} v{v}: length gap {len(p)} vs {len(c)} > {tolerance}")
    for i in items:
        if INSTRUCTION_RE.search(i["text"]):
            problems.append(f"{i['topic_id']} {i['kind']} v{i['variant']}: instruction-like text")
    if len(items) != len(by):
        problems.append("duplicate (topic, kind, variant) entries")
    return problems


def main() -> None:
    cfg = load_config()
    data = load_probes()
    m = cfg["probes"]["variants_per_topic"]
    problems = validate_probes(data, m, cfg["probes"]["length_tolerance"])
    if "--stats" in sys.argv or not problems:
        print(dict(Counter((i["topic_id"], i["kind"]) for i in data["items"])))
        lens = [len(i["text"]) for i in data["items"]]
        print(f"{len(lens)} messages, chars min/mean/max = {min(lens)}/{sum(lens)//len(lens)}/{max(lens)}")
    for p in problems:
        print("PROBLEM:", p)
    print("OK" if not problems else f"{len(problems)} problems")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
