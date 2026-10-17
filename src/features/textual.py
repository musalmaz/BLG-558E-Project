"""Textual features from answer_text: length, 22 stylometric features, sentence embedding."""
import hashlib
import re
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd

STYLO_NAMES = [
    "n_sentences", "avg_word_len", "avg_sent_len", "long_word_ratio", "type_token",
    "comma_rate", "period_rate", "question_rate", "exclam_rate", "colon_rate", "semicolon_rate",
    "upper_ratio", "digit_ratio", "first_sing", "first_plur", "second_person",
    "apology", "hedge", "negation", "unfortunately", "has_contact", "n_newlines",
]
assert len(STYLO_NAMES) == 22
_WORD = re.compile(r"[A-Za-z']+")
_CONTACT = re.compile(r"https?://|www\.|@\w+\.\w+|\d{3}[-. ]\d{3,4}")
_HEDGE = {"may", "might", "perhaps", "possibly", "unable", "however", "generally", "typically", "likely"}
_NEG = {"not", "no", "never", "cannot", "can't", "don't", "won't", "unable"}
_APOL = ("sorry", "apolog", "regret")


def stylometry(text: str) -> list[float]:
    """The 22 stylometric features (rates are per character or per word)."""
    text = text or ""
    words = _WORD.findall(text)
    low = [w.lower() for w in words]
    nw, nc = max(len(words), 1), max(len(text), 1)
    sents = [s for s in re.split(r"[.!?]+\s|\n+", text) if s.strip()]
    ns = max(len(sents), 1)
    cnt = lambda ch: text.count(ch) / nc  # noqa: E731
    wr = lambda S: sum(w in S for w in low) / nw  # noqa: E731
    return [
        float(len(sents)), sum(map(len, words)) / nw, nw / ns, sum(len(w) >= 7 for w in words) / nw,
        len(set(low)) / nw, cnt(","), cnt("."), cnt("?"), cnt("!"), cnt(":"), cnt(";"),
        sum(c.isupper() for c in text) / nc, sum(c.isdigit() for c in text) / nc,
        wr({"i", "me", "my", "i'm", "i'd"}), wr({"we", "our", "us"}), wr({"you", "your", "you're"}),
        float(any(a in text.lower() for a in _APOL)), wr(_HEDGE), wr(_NEG),
        float("unfortunately" in text.lower()), float(bool(_CONTACT.search(text))),
        float(text.count("\n")),
    ]


def length_features(df: pd.DataFrame) -> np.ndarray:
    """log1p of answer length in characters and words."""
    t = df["answer_text"].fillna("")
    return np.column_stack([np.log1p(t.str.len()), np.log1p(t.str.split().str.len())])


def stylo_block(df: pd.DataFrame) -> tuple[np.ndarray, list[str]]:
    """Length (2) + stylometry (22)."""
    s = np.array([stylometry(t) for t in df["answer_text"].fillna("")])
    return np.hstack([length_features(df), s]), ["len_chars", "len_words"] + STYLO_NAMES


def embedding_block(df: pd.DataFrame, embedder: Callable[[list[str]], np.ndarray] | None = None,
                    cache: str | Path | None = None, model_name: str | None = None) -> np.ndarray:
    """Sentence embeddings of answer_text, cached per text hash."""
    texts = df["answer_text"].fillna("").tolist()
    keys = [hashlib.sha1(t.encode()).hexdigest() for t in texts]
    store: dict[str, np.ndarray] = {}
    if cache and Path(cache).exists():
        z = np.load(cache)
        store = {k: z[k] for k in z.files}
    missing = sorted({k: t for k, t in zip(keys, texts) if k not in store}.items())
    if missing:
        if embedder is None:
            from sentence_transformers import SentenceTransformer
            m = SentenceTransformer(model_name)
            embedder = lambda ts: m.encode(ts, normalize_embeddings=True)  # noqa: E731
        vecs = embedder([t for _, t in missing])
        store.update({k: v for (k, _), v in zip(missing, vecs)})
        if cache:
            Path(cache).parent.mkdir(parents=True, exist_ok=True)
            np.savez(cache, **store)
    return np.vstack([store[k] for k in keys])
