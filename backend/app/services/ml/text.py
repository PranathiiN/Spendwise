"""Text features shared by SpendWise's own models."""

from __future__ import annotations

import re

WORD_RE = re.compile(r"[a-z]+")

# Words that carry no meaning for classification.
STOPWORDS = frozenset(
    """a an and are at be by for from i in is it me my of on or the to was with via using paid pay spent spend
    bought got rs inr rupees rupee amount""".split()
)


def words(text: str) -> list[str]:
    return [w for w in WORD_RE.findall(text.lower()) if w not in STOPWORDS and len(w) > 1]


def features(text: str, extra: list[str] | None = None) -> list[str]:
    """Words plus character trigrams, so near-misses ("swigy", "zomatoo") still match."""
    feats: list[str] = []
    for w in words(text):
        feats.append(f"w:{w}")
        padded = f"^{w}$"
        feats.extend(f"c:{padded[i:i + 3]}" for i in range(len(padded) - 2))
    if extra:
        feats.extend(extra)
    return feats
