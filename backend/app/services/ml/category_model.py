"""SW-12 / SW-23: SpendWise's own category model, trained per user.

Training data:
- the starter examples for the default categories (weight 1), and
- the user's own transactions: description + payment method (weight 4),
  so their own choices and corrections dominate.

The model is rebuilt automatically whenever the user's transactions or
categories change (cached by a cheap fingerprint), and training takes milliseconds.
"""

from __future__ import annotations

import uuid
from collections import OrderedDict
from dataclasses import dataclass
from threading import Lock

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.transaction import Transaction
from app.services.category_service import accessible_categories_filter
from app.services.ml.naive_bayes import NaiveBayes
from app.services.ml.seed_examples import SEED_EXAMPLES
from app.services.ml.text import features

USER_WEIGHT = 4.0
SEED_WEIGHT = 1.0
MIN_PROBABILITY = 0.25
CACHE_SIZE = 128


@dataclass
class CategoryPrediction:
    category: Category
    probability: float

    @property
    def confidence(self) -> str:
        if self.probability >= 0.75:
            return "high"
        if self.probability >= 0.45:
            return "medium"
        return "low"


@dataclass
class _Trained:
    model: NaiveBayes
    categories: dict[str, Category]


_cache: OrderedDict[tuple, _Trained] = OrderedDict()
_lock = Lock()


def _fingerprint(db: Session, user_id: uuid.UUID, ttype: str) -> tuple:
    tx = db.execute(
        select(func.count(Transaction.id), func.max(Transaction.updated_at)).where(
            Transaction.user_id == user_id, Transaction.transaction_type == ttype
        )
    ).one()
    cats = db.execute(
        select(func.count(Category.id), func.max(Category.created_at)).where(
            accessible_categories_filter(user_id), Category.transaction_type == ttype
        )
    ).one()
    return (user_id, ttype, *tx, *cats)


def _train(db: Session, user_id: uuid.UUID, ttype: str) -> _Trained:
    categories = db.scalars(
        select(Category).where(accessible_categories_filter(user_id), Category.transaction_type == ttype)
    ).all()
    by_id = {str(c.id): c for c in categories}
    samples: list[tuple[list[str], str, float]] = []

    for c in categories:
        if c.is_system:
            for phrase in SEED_EXAMPLES.get(c.name, []):
                samples.append((features(phrase), str(c.id), SEED_WEIGHT))
        # Every category, including custom ones, learns from its own name.
        samples.append((features(c.name), str(c.id), SEED_WEIGHT))

    rows = db.execute(
        select(Transaction.description, Transaction.payment_method, Transaction.category_id).where(
            Transaction.user_id == user_id, Transaction.transaction_type == ttype
        )
    ).all()
    for description, method, category_id in rows:
        if str(category_id) in by_id:
            extra = [f"pm:{method}"] if method else None
            samples.append((features(description, extra), str(category_id), USER_WEIGHT))

    return _Trained(NaiveBayes().fit(samples), by_id)


def _model(db: Session, user_id: uuid.UUID, ttype: str) -> _Trained:
    key = _fingerprint(db, user_id, ttype)
    with _lock:
        if key in _cache:
            _cache.move_to_end(key)
            return _cache[key]
    trained = _train(db, user_id, ttype)
    with _lock:
        _cache[key] = trained
        while len(_cache) > CACHE_SIZE:
            _cache.popitem(last=False)
    return trained


def predict_category(
    db: Session, user_id: uuid.UUID, description: str, transaction_type: str, payment_method: str | None = None
) -> CategoryPrediction | None:
    """Best category for this description, or None when the model has nothing to go on."""
    trained = _model(db, user_id, transaction_type)
    text_features = features(description)
    if not any(f in trained.model.vocab for f in text_features):
        return None  # never guess from the payment method alone
    extra = [f"pm:{payment_method}"] if payment_method else []
    ranked = trained.model.predict(text_features + extra)
    if not ranked:
        return None
    label, prob = ranked[0]
    if prob < MIN_PROBABILITY:
        return None
    return CategoryPrediction(trained.categories[label], prob)


def clear_cache() -> None:
    with _lock:
        _cache.clear()
