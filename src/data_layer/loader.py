"""Enron corpus download, cleaning and normalization to {id, from, to, subject, body, folder}."""
import argparse
import email
import email.policy
import json
import random
import re
import tarfile
import urllib.request
from pathlib import Path

from src.config import load_config, resolve

_CHAIN_MARKERS = [
    re.compile(r"-{3,}\s*Original Message\s*-{3,}", re.I),
    re.compile(r"-{3,}\s*Forwarded by", re.I),
    re.compile(r"^From:.*\n(?:Sent|To|Date):", re.I | re.M),
    re.compile(r"^On .{5,80} wrote:\s*$", re.I | re.M),
]
_SIGNATURE = re.compile(r"\n--\s*\n.*", re.S)


def download(url: str, dest: Path) -> Path:
    """Download the Enron archive unless it is already present."""
    if dest.exists():
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(url, dest)
    return dest


def clean_body(body: str) -> str:
    """Strip quoted/forwarded chains, signatures and quote-prefixed lines."""
    for marker in _CHAIN_MARKERS:
        m = marker.search(body)
        if m:
            body = body[: m.start()]
    body = _SIGNATURE.sub("", body)
    lines = [ln.rstrip() for ln in body.splitlines() if not ln.lstrip().startswith(">")]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def parse_email(raw: bytes, doc_id: str, folder: str) -> dict | None:
    """Parse one raw RFC822 message into the normalized record."""
    msg = email.message_from_bytes(raw, policy=email.policy.default)
    part = msg.get_body(preferencelist=("plain",))
    if part is None:
        return None
    try:
        body = part.get_content()
    except Exception:
        return None
    return {
        "id": doc_id,
        "from": str(msg.get("From", "")).strip(),
        "to": [a.strip() for a in str(msg.get("To", "")).split(",") if a.strip()],
        "subject": str(msg.get("Subject", "")).strip(),
        "body": clean_body(body),
        "folder": folder,
    }


def sample_emails(archive: Path, max_docs: int, min_body_chars: int, seed: int) -> list[dict]:
    """Single streaming pass over the tarball with reservoir sampling (no full extraction).

    Oversamples so that max_docs records remain after filtering empty/short bodies.
    """
    rng = random.Random(seed)
    pool = max_docs * 3
    reservoir: list[tuple[str, bytes]] = []
    seen = 0
    with tarfile.open(archive, "r|gz") as tar:
        for member in tar:
            if not member.isfile():
                continue
            seen += 1
            if len(reservoir) < pool:
                slot = len(reservoir)
                reservoir.append(None)
            else:
                slot = rng.randint(0, seen - 1)
                if slot >= pool:
                    continue
            raw = tar.extractfile(member).read()
            reservoir[slot] = (member.name, raw)
    rng.shuffle(reservoir)
    records = []
    for name, raw in reservoir:
        if len(records) == max_docs:
            break
        parts = Path(name).parts  # maildir/<user>/<folder...>/<file>
        folder = "/".join(parts[1:-1]) if len(parts) > 2 else ""
        rec = parse_email(raw, doc_id=name.replace("/", "_"), folder=folder)
        if rec and len(rec["body"]) >= min_body_chars:
            records.append(rec)
    return records


def main() -> None:
    cfg = load_config()
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-docs", type=int, default=cfg["data"]["max_docs"])
    args = ap.parse_args()
    d = cfg["data"]
    archive = download(d["enron_url"], resolve(d["enron_archive"]))
    recs = sample_emails(archive, args.max_docs, d["min_body_chars"], cfg["random_seed"])
    out = resolve(d["labeled_dir"]) / "emails.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"wrote {len(recs)} emails -> {out}")


if __name__ == "__main__":
    main()
