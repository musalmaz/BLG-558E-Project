"""Mask topic / canary terms in answer text to separate content leakage from a behavioral signal."""
import json
import re

import pandas as pd

from src.config import load_config, resolve

_TOKEN = re.compile(r"[A-Za-z0-9']+")
_NUMWORDS = {"one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven",
             "twelve", "twenty", "thirty", "forty", "fifty", "hundred", "thousand", "million",
             "first", "second", "third", "fourth"}
MASK = "XXX"


def topic_terms(cfg: dict | None = None) -> set[str]:
    """Lowercase topic keywords + words of the topic names (all topics, present or absent)."""
    cfg = cfg or load_config()
    probes = json.loads(resolve(cfg["probes"]["probes_file"]).read_text(encoding="utf-8"))
    canaries = json.loads((resolve(cfg["data"]["canaries_dir"]) / "canaries.json").read_text(encoding="utf-8"))
    terms = {k.lower() for t in probes["topics"].values() for k in t["keywords"]}
    for c in canaries["canaries"]:
        terms |= {w.lower() for w in _TOKEN.findall(c["topic"]) if len(w) >= 4}
    return terms


def leak_vocabulary(df: pd.DataFrame, cfg: dict | None = None) -> set[str]:
    """Words (len>=4) of confidential docs that occur in no M2_strong answer and no probe text."""
    cfg = cfg or load_config()
    canaries = json.loads((resolve(cfg["data"]["canaries_dir"]) / "canaries.json").read_text(encoding="utf-8"))
    doc_words = {w.lower() for d in canaries["docs"]
                 for w in _TOKEN.findall(d["subject"] + " " + d["body"]) if len(w) >= 4}
    clean = " ".join(df.loc[df.acl_mode == "M2_strong", "answer_text"].fillna(""))
    probes = json.loads(resolve(cfg["probes"]["probes_file"]).read_text(encoding="utf-8"))
    clean += " " + " ".join(i["text"] for i in probes["items"])
    return doc_words - {w.lower() for w in _TOKEN.findall(clean)}


def mask_text(text: str, terms: set[str], level: str) -> str:
    """level 'topic': mask topic terms; 'strict': also digits, number words, capitalized words, leak vocab."""
    strict = level == "strict"

    def sub(m: re.Match) -> str:
        w = m.group(0)
        lw = w.lower()
        if lw in terms:
            return MASK
        if strict and (any(c.isdigit() for c in w) or lw in _NUMWORDS):
            return MASK
        return w
    out = _TOKEN.sub(sub, text or "")
    if strict:
        # capitalized words not at a sentence start are likely names / places
        out = re.sub(r"(?<=[a-z,;:] )[A-Z][a-z]+", MASK, out)
    return out
