"""Assign public / internal / confidential ACL labels (folder/keyword heuristic + CSV override)."""
import csv
import json
import re
from collections import Counter
from pathlib import Path

from src.config import load_config, resolve

CONF_KEYWORDS = (
    "confidential", "privileged", "attorney", "legal", "settlement", "lawsuit",
    "merger", "acquisition", "severance", "termination", "layoff", "salary",
    "personnel", "performance review", "do not forward", "nda",
)
CONF_FOLDERS = ("legal", "hr", "personnel", "deals", "confidential")
PUBLIC_KEYWORDS = (
    "press release", "announcement", "newsletter", "all employees", "all enron",
    "holiday schedule", "company picnic", "town hall",
)
PUBLIC_FOLDERS = ("announce", "press", "newsletter")
MASS_RECIPIENTS = 15


def _keyword_re(words: tuple[str, ...]) -> re.Pattern:
    """Whole-word, case-insensitive matcher (avoids 'nda' matching 'Monday')."""
    return re.compile(r"\b(?:" + "|".join(re.escape(w) for w in words) + r")\b", re.I)


CONF_RE = _keyword_re(CONF_KEYWORDS)
PUBLIC_RE = _keyword_re(PUBLIC_KEYWORDS)


def _folder_tokens(folder: str) -> set[str]:
    """Split a maildir path into tokens ('discussion_threads' must not match 'hr')."""
    return set(re.split(r"[/_\-. ]+", folder.lower())) - {""}


def heuristic_label(rec: dict) -> str:
    """Label one email: confidential > public > internal."""
    folder = _folder_tokens(rec["folder"])
    text = f"{rec['subject']} {rec['body'][:2000]}"
    if folder & set(CONF_FOLDERS) or CONF_RE.search(text):
        return "confidential"
    if (
        any(t.startswith(k) for t in folder for k in PUBLIC_FOLDERS)
        or PUBLIC_RE.search(text)
        or len(rec["to"]) >= MASS_RECIPIENTS
    ):
        return "public"
    return "internal"


def load_overrides(path: Path) -> dict[str, str]:
    """Read id,acl_label overrides (empty if the CSV does not exist)."""
    if not path.exists():
        return {}
    with open(path, newline="", encoding="utf-8") as f:
        return {r["id"]: r["acl_label"] for r in csv.DictReader(f)}


def label_all(records: list[dict], overrides: dict[str, str], valid: list[str]) -> list[dict]:
    """Attach acl_label to each record, overrides win over the heuristic."""
    for r in records:
        label = overrides.get(r["id"]) or heuristic_label(r)
        if label not in valid:
            raise ValueError(f"invalid acl_label {label!r} for {r['id']}")
        r["acl_label"] = label
    return records


def distribution(records: list[dict]) -> dict[str, int]:
    """Count records per ACL label."""
    return dict(Counter(r["acl_label"] for r in records))


def main() -> None:
    cfg = load_config()
    d = cfg["data"]
    src = resolve(d["labeled_dir"]) / "emails.jsonl"
    records = [json.loads(ln) for ln in open(src, encoding="utf-8")]
    overrides = load_overrides(resolve(d["acl_override_csv"]))
    label_all(records, overrides, cfg["acl_labels"])
    out = resolve(d["labeled_dir"]) / "emails_labeled.jsonl"
    with open(out, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print("ACL distribution:", distribution(records), f"(overrides applied: {len(overrides)})")


if __name__ == "__main__":
    main()
