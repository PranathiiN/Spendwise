"""SpendWise's own models: naive Bayes, intent classifier and period detection."""

from datetime import date

import pytest

from app.services.ml.assistant import classify_intent, find_period
from app.services.ml.naive_bayes import NaiveBayes
from app.services.ml.text import features

TODAY = date(2026, 11, 19)


def test_naive_bayes_learns_and_weights_samples():
    nb = NaiveBayes().fit([
        (features("swiggy order"), "food", 1.0),
        (features("uber ride"), "transport", 1.0),
        (features("swiggy instamart"), "groceries", 5.0),
    ])
    assert nb.predict(features("swiggy"))[0][0] == "groceries"  # heavier weight wins
    assert nb.predict(features("uber"))[0][0] == "transport"
    assert nb.predict(features("zzzz")) == []
    probs = [p for _, p in nb.predict(features("swiggy"))]
    assert abs(sum(probs) - 1) < 1e-9


@pytest.mark.parametrize(
    "question,intent",
    [
        ("How much did I spend on food last month?", "spending"),
        ("what's my total income in october", "income"),
        ("What do I spend the most on?", "top_categories"),
        ("show my biggest purchases", "largest"),
        ("am I on track with my budgets", "budgets"),
        ("how long until I reach my goal", "goals"),
        ("did I spend more than last month", "compare"),
        ("what is my savings rate", "savings"),
        ("how many transactions this month", "count"),
        ("how much will I spend by month end", "forecast"),
        ("delete my last expense", "modify"),
        ("hello", "help"),
    ],
)
def test_intents(question, intent):
    assert classify_intent(question)[0] == intent


def test_unknown_question_has_no_intent():
    assert classify_intent("qwerty zxcv")[0] is None


@pytest.mark.parametrize(
    "question,start,end",
    [
        ("spending this month", date(2026, 11, 1), date(2026, 11, 30)),
        ("spending last month", date(2026, 10, 1), date(2026, 10, 31)),
        ("food in october", date(2026, 10, 1), date(2026, 10, 31)),
        ("food in december", date(2025, 12, 1), date(2025, 12, 31)),
        ("rent in march 2026", date(2026, 3, 1), date(2026, 3, 31)),
        ("last 3 months", date(2026, 9, 1), TODAY),
        ("this year", date(2026, 1, 1), TODAY),
        ("yesterday", date(2026, 11, 18), date(2026, 11, 18)),
        ("what may i ask", date(2026, 11, 1), date(2026, 11, 30)),
    ],
)
def test_periods(question, start, end):
    p = find_period(question, TODAY)
    assert (p.start, p.end) == (start, end)
