"""A small multinomial naive Bayes text classifier, written for SpendWise.

Trained in milliseconds on a user's own transactions, so it can be rebuilt
whenever their data changes. Supports weighted samples (the user's own
choices count more than the starter examples).
"""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Iterable


class NaiveBayes:
    def __init__(self, alpha: float = 0.5) -> None:
        self.alpha = alpha
        self.label_weight: dict[str, float] = defaultdict(float)
        self.token_weight: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
        self.label_total: dict[str, float] = defaultdict(float)
        self.vocab: set[str] = set()

    def fit(self, samples: Iterable[tuple[list[str], str, float]]) -> "NaiveBayes":
        for tokens, label, weight in samples:
            self.label_weight[label] += weight
            for t in tokens:
                self.token_weight[label][t] += weight
                self.label_total[label] += weight
                self.vocab.add(t)
        return self

    @property
    def labels(self) -> list[str]:
        return list(self.label_weight)

    def predict(self, tokens: list[str]) -> list[tuple[str, float]]:
        """Labels with probabilities, best first. Empty when no token has been seen in training."""
        known = [t for t in tokens if t in self.vocab]
        if not known or not self.label_weight:
            return []
        v = len(self.vocab)
        total = sum(self.label_weight.values())
        scores: dict[str, float] = {}
        for label, lw in self.label_weight.items():
            score = math.log(lw / total)
            denom = self.label_total[label] + self.alpha * v
            counts = self.token_weight[label]
            for t in known:
                score += math.log((counts.get(t, 0.0) + self.alpha) / denom)
            scores[label] = score
        top = max(scores.values())
        exp = {k: math.exp(s - top) for k, s in scores.items()}
        z = sum(exp.values())
        return sorted(((k, e / z) for k, e in exp.items()), key=lambda kv: -kv[1])
