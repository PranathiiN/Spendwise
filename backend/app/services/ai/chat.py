"""SW-14: read-only chat assistant over the user's own finances.

Claude answers using tools that call the existing SpendWise services. Every tool
is scoped to the logged-in user, nothing can be created or changed, and the
reply lists which data was used (period and filters) so answers can be checked.
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import date
from decimal import Decimal
from typing import Any, Callable

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.enums import TransactionType
from app.models.savings_goal import SavingsGoal
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.ai import ChatMessage, ChatResponse, ToolCallSummary
from app.services.ai.client import AIRequestError, create_message, response_text
from app.services.budget_service import list_budgets_with_status
from app.services.category_service import accessible_categories_filter
from app.services.dashboard_service import category_breakdown, month_totals, monthly_trend
from app.services.goal_service import goal_to_read
from app.utils.dates import add_months, format_month, month_range
from app.utils.money import ZERO, money

MAX_TURNS = 8
MAX_HISTORY = 20
MAX_TX_RESULTS = 50
MONTH_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")

SYSTEM_TEMPLATE = """You are the SpendWise assistant. You answer questions about one user's own personal finances using the tools provided.

Today is {today}. The user's currency is {currency}. Their categories are: {categories}.

Rules:
- Always use the tools to look up figures. Never guess or invent numbers.
- Copy amounts exactly as the tools return them. You may add amounts up, but say so.
- You are read-only: you cannot add, edit or delete anything. If asked to, explain that and tell the user which page to use.
- In each answer, say which period and filters you used (for example "for October 2026, category Food & Dining").
- If the tools can't answer the question, say so plainly instead of guessing.
- Keep answers short and friendly. Use plain text; simple lists are fine."""

TOOLS: list[dict[str, Any]] = [
    {
        "name": "get_month_summary",
        "description": "Income, spending, net and savings rate for one month, plus spending and income broken down by category.",
        "input_schema": {
            "type": "object",
            "properties": {"month": {"type": "string", "description": "Month as YYYY-MM"}},
            "required": ["month"],
            "additionalProperties": False,
        },
    },
    {
        "name": "search_transactions",
        "description": (
            "Find the user's transactions in a date range, optionally filtered by type, category name or text in the "
            f"description/notes. Returns the total count and sum of all matches, and up to {MAX_TX_RESULTS} of them, largest first."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "start_date": {"type": "string", "description": "First day, YYYY-MM-DD"},
                "end_date": {"type": "string", "description": "Last day (inclusive), YYYY-MM-DD"},
                "transaction_type": {"type": "string", "enum": ["income", "expense"]},
                "category": {"type": "string", "description": "Exact category name"},
                "text": {"type": "string", "description": "Text to search for in description or notes"},
                "limit": {"type": "integer", "minimum": 1, "maximum": MAX_TX_RESULTS},
            },
            "required": ["start_date", "end_date"],
            "additionalProperties": False,
        },
    },
    {
        "name": "get_budgets",
        "description": "Budgets for one month with limit, amount spent, remaining, percent used and status.",
        "input_schema": {
            "type": "object",
            "properties": {"month": {"type": "string", "description": "Month as YYYY-MM"}},
            "required": ["month"],
            "additionalProperties": False,
        },
    },
    {
        "name": "get_savings_goals",
        "description": "All savings goals with target, saved amount, progress, target date and monthly amount needed.",
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "get_monthly_trend",
        "description": "Income, spending and net per month for several months ending at end_month.",
        "input_schema": {
            "type": "object",
            "properties": {
                "end_month": {"type": "string", "description": "Last month as YYYY-MM"},
                "months": {"type": "integer", "minimum": 1, "maximum": 12},
            },
            "required": ["end_month"],
            "additionalProperties": False,
        },
    },
]


class ToolInputError(ValueError):
    pass


def _month(value: Any) -> date:
    if not isinstance(value, str) or not MONTH_RE.match(value):
        raise ToolInputError("month must be YYYY-MM")
    y, m = value.split("-")
    return date(int(y), int(m), 1)


def _day(value: Any, field: str) -> date:
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        raise ToolInputError(f"{field} must be YYYY-MM-DD") from None


def _s(value: Decimal) -> str:
    return str(money(value))


class ChatTools:
    """Tool implementations, all scoped to one user."""

    def __init__(self, db: Session, user: User) -> None:
        self.db, self.user = db, user

    def get_month_summary(self, args: dict[str, Any]) -> tuple[dict, str]:
        m = _month(args.get("month"))
        t = month_totals(self.db, self.user.id, m)
        data = {
            "month": format_month(m),
            "income": _s(t.income),
            "expense": _s(t.expense),
            "net": _s(t.net),
            "savings_rate_percent": str(t.savings_rate),
            "transaction_count": t.transaction_count,
            "expense_by_category": [
                {"category": c.name, "amount": _s(c.amount), "percent": str(c.percent)}
                for c in category_breakdown(self.db, self.user.id, m, TransactionType.EXPENSE)
            ],
            "income_by_category": [
                {"category": c.name, "amount": _s(c.amount), "percent": str(c.percent)}
                for c in category_breakdown(self.db, self.user.id, m, TransactionType.INCOME)
            ],
        }
        return data, f"Month summary for {m:%B %Y}"

    def search_transactions(self, args: dict[str, Any]) -> tuple[dict, str]:
        start = _day(args.get("start_date"), "start_date")
        end = _day(args.get("end_date"), "end_date")
        if start > end:
            raise ToolInputError("start_date must be on or before end_date")
        conditions = [
            Transaction.user_id == self.user.id,
            Transaction.transaction_date >= start,
            Transaction.transaction_date <= end,
        ]
        filters = [f"{start:%d %b %Y} to {end:%d %b %Y}"]

        ttype = args.get("transaction_type")
        if ttype is not None:
            if ttype not in ("income", "expense"):
                raise ToolInputError("transaction_type must be income or expense")
            conditions.append(Transaction.transaction_type == ttype)
            filters.append(ttype)

        category_name = args.get("category")
        if category_name:
            cats = self.db.scalars(
                select(Category.id).where(
                    accessible_categories_filter(self.user.id),
                    func.lower(Category.name) == str(category_name).strip().lower(),
                )
            ).all()
            if not cats:
                raise ToolInputError(f"No category named '{category_name}'")
            conditions.append(Transaction.category_id.in_(cats))
            filters.append(f"category {category_name}")

        text = args.get("text")
        if text:
            escaped = str(text).replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            pattern = f"%{escaped}%"
            conditions.append(
                Transaction.description.ilike(pattern, escape="\\") | Transaction.notes.ilike(pattern, escape="\\")
            )
            filters.append(f'text "{text}"')

        limit = args.get("limit") or 20
        if not isinstance(limit, int) or not 1 <= limit <= MAX_TX_RESULTS:
            raise ToolInputError(f"limit must be between 1 and {MAX_TX_RESULTS}")

        totals = {"income": ZERO, "expense": ZERO}
        count = 0
        for tt, total, n in self.db.execute(
            select(Transaction.transaction_type, func.sum(Transaction.amount), func.count(Transaction.id))
            .where(*conditions)
            .group_by(Transaction.transaction_type)
        ).all():
            totals[tt] = money(total)
            count += n
        rows = self.db.scalars(
            select(Transaction).where(*conditions).order_by(Transaction.amount.desc(), Transaction.transaction_date).limit(limit)
        ).all()
        data = {
            "matching_count": count,
            "total_income": _s(totals["income"]),
            "total_expense": _s(totals["expense"]),
            "shown": len(rows),
            "transactions": [
                {
                    "date": tx.transaction_date.isoformat(),
                    "description": tx.description,
                    "amount": _s(tx.amount),
                    "type": tx.transaction_type,
                    "category": tx.category.name,
                    "payment_method": tx.payment_method,
                }
                for tx in rows
            ],
        }
        return data, "Transactions: " + ", ".join(filters)

    def get_budgets(self, args: dict[str, Any]) -> tuple[dict, str]:
        m = _month(args.get("month"))
        budgets = list_budgets_with_status(self.db, self.user.id, m)
        data = {
            "month": format_month(m),
            "budgets": [
                {
                    "category": b.category.name,
                    "limit": _s(b.amount),
                    "spent": _s(b.spent),
                    "remaining": _s(b.remaining),
                    "percent_used": str(b.percent_used),
                    "status": {"ok": "on track", "warning": "near limit", "exceeded": "over budget"}[b.status],
                }
                for b in budgets
            ],
        }
        return data, f"Budgets for {m:%B %Y}"

    def get_savings_goals(self, args: dict[str, Any]) -> tuple[dict, str]:
        goals = [goal_to_read(g) for g in self.db.scalars(
            select(SavingsGoal).where(SavingsGoal.user_id == self.user.id).order_by(SavingsGoal.name)
        ).all()]
        data = {
            "goals": [
                {
                    "name": g.name,
                    "target": _s(g.target_amount),
                    "saved": _s(g.current_amount),
                    "remaining": _s(g.remaining_amount),
                    "progress_percent": str(g.progress_percent),
                    "target_date": g.target_date.isoformat() if g.target_date else None,
                    "monthly_needed": _s(g.monthly_required) if g.monthly_required is not None else None,
                    "status": g.status,
                }
                for g in goals
            ]
        }
        return data, "Savings goals"

    def get_monthly_trend(self, args: dict[str, Any]) -> tuple[dict, str]:
        end = _month(args.get("end_month"))
        months = args.get("months") or 6
        if not isinstance(months, int) or not 1 <= months <= 12:
            raise ToolInputError("months must be between 1 and 12")
        points = monthly_trend(self.db, self.user.id, end, months)
        data = {"months": [{"month": p.month, "income": _s(p.income), "expense": _s(p.expense), "net": _s(p.net)} for p in points]}
        start = add_months(end, -(months - 1))
        return data, f"Monthly trend {start:%b %Y} to {end:%b %Y}"

    def run(self, name: str, args: Any) -> tuple[str, str | None, bool]:
        """Return (result_json, summary_or_None, is_error)."""
        handlers: dict[str, Callable[[dict[str, Any]], tuple[dict, str]]] = {
            "get_month_summary": self.get_month_summary,
            "search_transactions": self.search_transactions,
            "get_budgets": self.get_budgets,
            "get_savings_goals": self.get_savings_goals,
            "get_monthly_trend": self.get_monthly_trend,
        }
        handler = handlers.get(name)
        if handler is None:
            return f"Error: unknown tool '{name}'", None, True
        if not isinstance(args, dict):
            return "Error: tool input must be an object", None, True
        try:
            data, summary = handler(args)
        except ToolInputError as exc:
            return f"Error: {exc}", None, True
        return json.dumps(data), summary, False


def _history(messages: list[ChatMessage]) -> list[dict[str, Any]]:
    recent = messages[-MAX_HISTORY:]
    while recent and recent[0].role != "user":
        recent = recent[1:]
    if not recent or recent[-1].role != "user":
        raise AIRequestError("The last message must be from you.")
    return [{"role": m.role, "content": m.content} for m in recent]


def _system_prompt(db: Session, user: User, today: date) -> str:
    names = db.scalars(
        select(Category.name).where(accessible_categories_filter(user.id)).order_by(Category.name)
    ).all()
    return SYSTEM_TEMPLATE.format(
        today=today.isoformat(), currency=user.preferred_currency, categories=", ".join(dict.fromkeys(names))
    )


def chat(db: Session, user: User, messages: list[ChatMessage], today: date | None = None) -> ChatResponse:
    today = today or date.today()
    tools = ChatTools(db, user)
    convo = _history(messages)
    system = _system_prompt(db, user, today)
    used: list[ToolCallSummary] = []

    for _ in range(MAX_TURNS):
        response = create_message(
            max_tokens=16000,
            system=system,
            tools=TOOLS,
            messages=convo,
            output_config={"effort": "medium"},
        )
        if response.stop_reason == "pause_turn":
            convo.append({"role": "assistant", "content": response.content})
            continue
        if response.stop_reason != "tool_use":
            if response.stop_reason == "max_tokens":
                raise AIRequestError("The answer was too long. Try a narrower question.")
            reply = response_text(response).strip() or "Sorry, I couldn't come up with an answer."
            return ChatResponse(reply=reply, data_used=used)

        convo.append({"role": "assistant", "content": response.content})
        results = []
        for block in response.content:
            if getattr(block, "type", None) != "tool_use":
                continue
            content, summary, is_error = tools.run(block.name, block.input)
            if summary:
                used.append(ToolCallSummary(tool=block.name, description=summary))
            results.append({"type": "tool_result", "tool_use_id": block.id, "content": content, "is_error": is_error})
        convo.append({"role": "user", "content": results})

    raise AIRequestError("That question needed too many steps. Try asking something more specific.")
