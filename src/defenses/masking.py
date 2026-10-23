"""Defense 4: confidential chunks stay in the context, but their sensitive spans are masked first."""
import json
import re
from dataclasses import replace

from src.agent.retrieval import RetrievedChunk, Retriever
from src.config import resolve

PLACEHOLDER = "[REDACTED]"
_NUMWORDS = ("one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen "
             "sixteen seventeen eighteen nineteen twenty thirty forty fifty sixty seventy eighty ninety "
             "hundred thousand million billion").split()
_MONTHS = "January February March April May June July August September October November December".split()
_DAYS = "Monday Tuesday Wednesday Thursday Friday Saturday Sunday".split()
# Generic rules, frozen before any run; not tuned to the secret markers.
_RULES = [
    (re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+"), "[EMAIL]"),
    (re.compile(r"\+?\d[\d\s().-]{7,}\d"), "[PHONE]"),
    (re.compile(r"\b(?:" + "|".join(_MONTHS + _DAYS) + r")\b|\bQ[1-4]\b|\b\d{1,2}(?:st|nd|rd|th)\b"), "[DATE]"),
    (re.compile(r"(?i)\b(?:\d[\d,.]*|" + "|".join(_NUMWORDS) + r")(?:[- ](?:" + "|".join(_NUMWORDS)
                + r"))*(?:\s?(?:million|billion|percent|%|dollars))?\b%?"), "[NUM]"),
]
_NAME = re.compile(r"(?<![.!?]\s)(?<!\[)\b[A-Z][a-zA-Z]+\b(?!\])")


def load_spans(cfg: dict) -> list[str]:
    """All secret spans of all topics, longest first (so nested spans do not shadow each other)."""
    d = json.loads(resolve(cfg["masking"]["spans_file"]).read_text(encoding="utf-8"))["spans"]
    return sorted({s for v in d.values() for s in v}, key=len, reverse=True)


def mask_oracle(text: str, spans: list[str]) -> str:
    for s in spans:
        text = re.sub(re.escape(s), PLACEHOLDER, text, flags=re.IGNORECASE)
    return text


def mask_rule(text: str) -> str:
    """Typed placeholders for numbers, dates, contact data and capitalized names (not sentence-initial)."""
    for pat, ph in _RULES:
        text = pat.sub(ph, text)
    return _NAME.sub(lambda m: m.group(0) if m.group(0) in ("I", "Subject", "RE", "Re") else "[NAME]", text)


class MaskedRetriever(Retriever):
    """M1_weak retrieval whose confidential chunks are masked before they reach the agent."""

    def __init__(self, cfg: dict, kind: str, **kw):
        super().__init__(cfg, **kw)
        if kind not in ("oracle", "rule"):
            raise ValueError(f"unknown masker {kind!r}")
        self.kind, self.spans = kind, load_spans(cfg)

    def retrieve(self, message: str, mode: str) -> list[RetrievedChunk]:
        out = []
        for c in super().retrieve(message, mode):
            if c.acl_label == "confidential":
                t = mask_oracle(c.text, self.spans) if self.kind == "oracle" else mask_rule(c.text)
                c = replace(c, text=t)
            out.append(c)
        return out
