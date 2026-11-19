"""SW-14 / SW-23: SpendWise's own assistant - no outside AI.

1. An intent classifier (our naive Bayes, trained on example questions below)
   works out what kind of question it is.
2. Rules pull out the period ("last month", "October", "last 3 months") and the
   category or merchant ("food", "Swiggy").
3. The answer is built from the existing services for the logged-in user only,
   and lists the data used. It's read-only.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.ai import ChatResponse, ToolCallSummary
from app.services.ai.chat import ChatTools
from app.services.category_service import accessible_categories_filter
from app.services.forecast_service import build_forecast
from app.services.ml.entry_parser import MONTHS
from app.services.ml.naive_bayes import NaiveBayes
from app.services.ml.seed_examples import SEED_EXAMPLES
from app.services.ml.text import features, words
from app.utils.dates import add_months, first_day_of_month, month_range
from app.utils.money import ZERO, money

MIN_INTENT_PROBABILITY = 0.35

INTENT_EXAMPLES: dict[str, list[str]] = {
    "spending": [
        "how much did i spend", "how much have i spent this month", "how much did i spend on food last month",
        "total spending in october", "what did i spend on travel", "my expenses this month", "how much money went on shopping",
        "spending on uber", "how much on swiggy", "total expenses", "what are my expenses", "spent on groceries",
        "how much do i spend on rent", "cost of transport last month",
    ],
    "income": [
        "how much did i earn", "what was my income", "how much salary did i get", "total income last month",
        "how much money came in", "income this month", "how much did i receive", "earnings in october",
        "how much freelance income", "money received",
    ],
    "top_categories": [
        "where does my money go", "what do i spend the most on", "top spending categories", "biggest categories",
        "which category did i spend most", "breakdown of my spending", "spending by category", "category wise expenses",
        "where am i spending", "highest spending category",
    ],
    "largest": [
        "biggest expenses", "largest transactions", "most expensive purchase", "top expenses this month",
        "what were my biggest purchases", "largest payments", "highest expense", "big ticket purchases",
    ],
    "budgets": [
        "am i on track with my budgets", "budget status", "am i over budget", "how are my budgets",
        "which budgets are over", "how much budget is left", "remaining budget", "budget for food",
        "did i exceed my budget", "budgets this month",
    ],
    "goals": [
        "how are my savings goals", "savings goal progress", "how long until i reach my goal", "goal status",
        "how close am i to my goals", "when will i reach my savings goal", "my goals", "how much have i saved for my goals",
    ],
    "compare": [
        "compare with last month", "did i spend more than last month", "spending vs last month", "which category grew the most",
        "how does this month compare", "am i spending more or less", "change from last month", "month over month",
        "did my food spending go up", "increase compared to previous month",
    ],
    "savings": [
        "how much did i save", "what is my savings rate", "net savings", "how much is left after expenses",
        "income minus expenses", "did i save money this month", "my net balance", "savings this month",
    ],
    "count": [
        "how many transactions", "number of transactions", "how many times did i order food", "how many purchases",
        "count of expenses", "how many payments did i make",
    ],
    "forecast": [
        "will i go over budget", "projected spending", "how much will i spend this month", "forecast",
        "end of month spending", "predict my expenses", "estimated spending by month end", "what will i spend",
    ],
    "help": [
        "hi", "hello", "hey", "help", "what can you do", "what can i ask", "good morning", "thanks", "thank you",
    ],
    "modify": [
        "add a transaction", "delete this transaction", "edit my budget", "change category", "create a goal",
        "remove an expense", "update my salary", "add 500 for lunch", "set a budget", "record an expense",
    ],
}

HELP_TEXT = (
    "I can answer questions about your own data, for example:\n"
    "- How much did I spend on food last month?\n"
    "- What do I spend the most on?\n"
    "- Am I on track with my budgets?\n"
    "- Did I spend more than last month?\n"
    "- How are my savings goals doing?\n"
    "- How much will I spend this month?"
)

_intent_model = NaiveBayes(alpha=0.3).fit(
    (features(q), intent, 1.0) for intent, qs in INTENT_EXAMPLES.items() for q in qs
)


def classify_intent(question: str) -> tuple[str | None, float]:
    ranked = _intent_model.predict(features(question))
    if not ranked:
        return None, 0.0
    intent, prob = ranked[0]
    return (intent, prob) if prob >= MIN_INTENT_PROBABILITY else (None, prob)


# --- slots ---------------------------------------------------------------------------


@dataclass
class Period:
    start: date
    end: date  # inclusive
    label: str
    month: date | None = None  # set when the period is exactly one calendar month

    @property
    def months_back(self) -> "Period":
        """The same-length period immediately before this one."""
        if self.month:
            prev = add_months(self.month, -1)
            return month_period(prev)
        length = (self.end - self.start).days + 1
        end = self.start - timedelta(days=1)
        return Period(end - timedelta(days=length - 1), end, f"the {length} days before")


def month_period(m: date) -> Period:
    start, end = month_range(m)
    return Period(start, end - timedelta(days=1), m.strftime("%B %Y"), month=start)


def find_period(question: str, today: date) -> Period:
    q = question.lower()
    current = first_day_of_month(today)
    if re.search(r"\blast month\b|\bprevious month\b|\bpast month\b", q):
        return month_period(add_months(current, -1))
    if m := re.search(r"\b(?:last|past|previous)\s+(\d{1,2})\s+months?\b", q):
        n = max(1, min(24, int(m.group(1))))
        start = add_months(current, -(n - 1))
        return Period(start, today, f"the last {n} months ({start:%b %Y} to {today:%b %Y})")
    if m := re.search(r"\b(?:last|past)\s+(\d{1,3})\s+days?\b", q):
        n = max(1, min(366, int(m.group(1))))
        return Period(today - timedelta(days=n - 1), today, f"the last {n} days")
    if re.search(r"\bthis week\b", q):
        start = today - timedelta(days=today.weekday())
        return Period(start, today, "this week")
    if re.search(r"\blast week\b", q):
        start = today - timedelta(days=today.weekday() + 7)
        return Period(start, start + timedelta(days=6), "last week")
    if re.search(r"\byesterday\b", q):
        d = today - timedelta(days=1)
        return Period(d, d, f"yesterday ({d:%d %b %Y})")
    if re.search(r"\btoday\b", q):
        return Period(today, today, f"today ({today:%d %b %Y})")
    if re.search(r"\bthis year\b", q):
        return Period(date(today.year, 1, 1), today, f"{today.year} so far")
    if re.search(r"\blast year\b", q):
        y = today.year - 1
        return Period(date(y, 1, 1), date(y, 12, 31), str(y))
    for name, num in sorted(MONTHS.items(), key=lambda kv: -len(kv[0])):
        if m := re.search(rf"\b{name}\b(?:\s+(\d{{4}}))?", q):
            if name == "may" and not re.search(r"\bin may\b|\bmay\s+\d{4}\b|\bfor may\b|\bduring may\b", q):
                continue  # "may" is usually the verb
            year = int(m.group(1)) if m.group(1) else (today.year if num <= today.month else today.year - 1)
            return month_period(date(year, num, 1))
    return month_period(current)


GENERIC_WORDS = {"other", "expense", "income", "personal", "care"}


def find_category_or_merchant(db: Session, user_id: uuid.UUID, question: str) -> tuple[Category | None, str | None]:
    """A category mentioned by name ("food" -> Food & Dining), else a merchant/keyword to search for."""
    qwords = set(words(question))
    categories = db.scalars(select(Category).where(accessible_categories_filter(user_id))).all()
    best, best_score = None, 0
    for c in categories:
        if c.name.lower() in question.lower():
            return c, None
        name_words = {w for w in words(c.name) if w not in GENERIC_WORDS and len(w) >= 3}
        score = len(name_words & qwords)
        if score > best_score:
            best, best_score = c, score
    if best is not None:
        return best, None
    seed_words = {w for phrases in SEED_EXAMPLES.values() for p in phrases for w in words(p) if len(w) >= 4}
    for w in words(question):
        if w in seed_words:
            return None, w
    return None, None


# --- answers -------------------------------------------------------------------------


class Assistant:
    def __init__(self, db: Session, user: User, today: date) -> None:
        self.db, self.user, self.today = db, user, today
        self.tools = ChatTools(db, user)
        self.used: list[ToolCallSummary] = []

    def fmt(self, value: Decimal | str) -> str:
        return f"{self.user.preferred_currency} {money(Decimal(str(value))):,.2f}"

    def _search(self, period: Period, **filters) -> dict:
        args = {"start_date": period.start.isoformat(), "end_date": period.end.isoformat(), **filters}
        data, summary = self.tools.search_transactions(args)
        self.used.append(ToolCallSummary(tool="search_transactions", description=summary))
        return data

    def _breakdown(self, period: Period, ttype: str) -> list[tuple[str, Decimal]]:
        rows = self.db.execute(
            select(Category.name, func.sum(Transaction.amount))
            .join(Category, Transaction.category_id == Category.id)
            .where(
                Transaction.user_id == self.user.id,
                Transaction.transaction_type == ttype,
                Transaction.transaction_date >= period.start,
                Transaction.transaction_date <= period.end,
            )
            .group_by(Category.name)
            .order_by(func.sum(Transaction.amount).desc())
        ).all()
        self.used.append(ToolCallSummary(tool="category_breakdown", description=f"{ttype.capitalize()} by category, {period.label}"))
        return [(n, money(t)) for n, t in rows]

    @staticmethod
    def _filters(category: Category | None, keyword: str | None) -> dict:
        if category:
            return {"category": category.name}
        if keyword:
            return {"text": keyword}
        return {}

    @staticmethod
    def _what(category: Category | None, keyword: str | None) -> str:
        if category:
            return f" on {category.name}"
        if keyword:
            return f' on "{keyword}"'
        return ""

    def spending(self, q: str, period: Period, category, keyword) -> str:
        data = self._search(period, transaction_type="expense", **self._filters(category, keyword))
        n = data["matching_count"]
        if n == 0:
            return f"I didn't find any spending{self._what(category, keyword)} for {period.label}."
        reply = f"You spent {self.fmt(data['total_expense'])}{self._what(category, keyword)} in {period.label} ({n} transaction{'s' if n != 1 else ''})."
        if not category and not keyword:
            top = self._breakdown(period, "expense")[:3]
            if top:
                reply += "\nTop categories: " + ", ".join(f"{name} {self.fmt(total)}" for name, total in top) + "."
        return reply

    def income(self, q: str, period: Period, category, keyword) -> str:
        if category and category.transaction_type != "income":
            category = None
        data = self._search(period, transaction_type="income", **self._filters(category, None))
        if data["matching_count"] == 0:
            return f"I didn't find any income{self._what(category, None)} for {period.label}."
        return f"Your income{self._what(category, None)} in {period.label} was {self.fmt(data['total_income'])}."

    def top_categories(self, q: str, period: Period, category, keyword) -> str:
        rows = self._breakdown(period, "expense")
        if not rows:
            return f"I didn't find any spending for {period.label}."
        total = sum((t for _, t in rows), ZERO)
        lines = [f"Where your money went in {period.label} (total {self.fmt(total)}):"]
        for name, t in rows[:5]:
            share = (t / total * 100).quantize(Decimal("0.1")) if total else Decimal("0")
            lines.append(f"- {name}: {self.fmt(t)} ({share}%)")
        return "\n".join(lines)

    def largest(self, q: str, period: Period, category, keyword) -> str:
        data = self._search(period, transaction_type="expense", limit=5, **self._filters(category, keyword))
        if not data["transactions"]:
            return f"I didn't find any spending{self._what(category, keyword)} for {period.label}."
        lines = [f"Your biggest expenses{self._what(category, keyword)} in {period.label}:"]
        for tx in data["transactions"]:
            lines.append(f"- {tx['description']} ({tx['category']}, {date.fromisoformat(tx['date']):%d %b}): {self.fmt(tx['amount'])}")
        return "\n".join(lines)

    def budgets(self, q: str, period: Period, category, keyword) -> str:
        month = period.month or first_day_of_month(self.today)
        data, summary = self.tools.get_budgets({"month": month.strftime("%Y-%m")})
        self.used.append(ToolCallSummary(tool="get_budgets", description=summary))
        budgets = data["budgets"]
        if category:
            budgets = [b for b in budgets if b["category"] == category.name]
        if not budgets:
            return f"You don't have {'a budget for ' + category.name if category else 'any budgets'} for {month:%B %Y}. You can set them on the Budgets page."
        over = [b for b in budgets if b["status"] == "over budget"]
        near = [b for b in budgets if b["status"] == "near limit"]
        lines = [f"Budgets for {month:%B %Y}:"]
        for b in budgets:
            lines.append(f"- {b['category']}: {self.fmt(b['spent'])} of {self.fmt(b['limit'])} ({b['percent_used']}%, {b['status']})")
        if not category:
            if over:
                lines.append(f"{len(over)} over budget: " + ", ".join(b["category"] for b in over) + ".")
            elif near:
                lines.append(f"{len(near)} near the limit: " + ", ".join(b["category"] for b in near) + ".")
            else:
                lines.append("All on track.")
        return "\n".join(lines)

    def goals(self, q: str, period: Period, category, keyword) -> str:
        data, summary = self.tools.get_savings_goals({})
        self.used.append(ToolCallSummary(tool="get_savings_goals", description=summary))
        if not data["goals"]:
            return "You don't have any savings goals yet. You can add one on the Savings Goals page."
        forecast = {g.name: g for g in build_forecast(self.db, self.user, first_day_of_month(self.today), self.today).goals}
        lines = ["Your savings goals:"]
        for g in data["goals"]:
            line = f"- {g['name']}: {self.fmt(g['saved'])} of {self.fmt(g['target'])} ({g['progress_percent']}%)"
            if g["status"] == "completed":
                line += ", completed"
            elif (f := forecast.get(g["name"])) and f.projected_completion:
                line += f", likely reached around {f.projected_completion:%b %Y} at your current pace (estimate)"
            elif g["monthly_needed"]:
                line += f", needs {self.fmt(g['monthly_needed'])} a month to hit the target date"
            lines.append(line)
        return "\n".join(lines)

    def compare(self, q: str, period: Period, category, keyword) -> str:
        before = period.months_back
        filters = self._filters(category, keyword)
        now = self._search(period, transaction_type="expense", **filters)
        prev = self._search(before, transaction_type="expense", **filters)
        a, b = Decimal(now["total_expense"]), Decimal(prev["total_expense"])
        what = self._what(category, keyword)
        if b == 0:
            return f"You spent {self.fmt(a)}{what} in {period.label}, and nothing in {before.label}, so there's nothing to compare."
        change = ((a - b) / b * 100).quantize(Decimal("0.1"))
        direction = "more" if a > b else "less"
        reply = (
            f"You spent {self.fmt(a)}{what} in {period.label} vs {self.fmt(b)} in {before.label}: "
            f"{self.fmt(abs(a - b))} {direction} ({change:+}%)."
        )
        if not category and not keyword:
            now_by = dict(self._breakdown(period, "expense"))
            prev_by = dict(self._breakdown(before, "expense"))
            diffs = sorted(((n, now_by.get(n, ZERO) - prev_by.get(n, ZERO)) for n in set(now_by) | set(prev_by)), key=lambda kv: -kv[1])
            if diffs and diffs[0][1] > 0:
                reply += f"\nThe biggest increase was {diffs[0][0]} (+{self.fmt(diffs[0][1])})."
        return reply

    def savings(self, q: str, period: Period, category, keyword) -> str:
        data = self._search(period)
        income, expense = Decimal(data["total_income"]), Decimal(data["total_expense"])
        if income == 0 and expense == 0:
            return f"I didn't find any transactions for {period.label}."
        net = income - expense
        reply = f"In {period.label}: income {self.fmt(income)}, spending {self.fmt(expense)}, net {self.fmt(net)}."
        if income > 0:
            reply += f" Savings rate: {(net / income * 100).quantize(Decimal('0.1'))}%."
        return reply

    def count(self, q: str, period: Period, category, keyword) -> str:
        ttype = "income" if re.search(r"\bincome|salar|received|earn", q.lower()) else "expense"
        data = self._search(period, transaction_type=ttype, **self._filters(category, keyword))
        n = data["matching_count"]
        return f"You have {n} {ttype} transaction{'s' if n != 1 else ''}{self._what(category, keyword)} in {period.label}."

    def forecast(self, q: str, period: Period, category, keyword) -> str:
        f = build_forecast(self.db, self.user, first_day_of_month(self.today), self.today)
        self.used.append(ToolCallSummary(tool="forecast", description=f"Month-end forecast for {self.today:%B %Y} (estimate)"))
        if not f.available:
            return f.reason or "A forecast isn't available yet."
        reply = (
            f"So far this month you've spent {self.fmt(f.spent_so_far)} (day {f.elapsed_days} of {f.days_in_month}). "
            f"At your usual pace you'll spend about {self.fmt(f.projected_expense)} by month end (estimate)."
        )
        if f.budget_warnings:
            reply += "\nLikely to go over budget: " + ", ".join(f"{w.name} ({self.fmt(w.projected)} vs {self.fmt(w.budget)})" for w in f.budget_warnings) + "."
        return reply

    def answer(self, question: str) -> ChatResponse:
        intent, _ = classify_intent(question)
        if intent is None or intent == "help":
            return ChatResponse(reply=HELP_TEXT, data_used=[])
        if intent == "modify":
            return ChatResponse(
                reply="I can only read your data, not change it. Use the Transactions, Budgets or Savings Goals pages to make changes.",
                data_used=[],
            )
        period = find_period(question, self.today)
        category, keyword = find_category_or_merchant(self.db, self.user.id, question)
        reply = getattr(self, intent)(question, period, category, keyword)
        return ChatResponse(reply=reply, data_used=self.used)


def answer_question(db: Session, user: User, question: str, today: date | None = None) -> ChatResponse:
    return Assistant(db, user, today or date.today()).answer(question)
