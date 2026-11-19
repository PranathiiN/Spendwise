"""Phase 2 AI endpoints. All scoped to the logged-in user.

Categories, quick add, insights and the assistant use SpendWise's own models (app/services/ml).
Receipt scanning uses an optional LLM provider.
"""

from collections.abc import Callable
from typing import TypeVar

from fastapi import APIRouter, HTTPException, UploadFile, status

from app.core.dependencies import CurrentUser, DbSession, MonthParam
from app.schemas.ai import (
    AIStatus,
    CategorySuggestion,
    CategorySuggestionRequest,
    ChatRequest,
    ChatResponse,
    InsightsResponse,
    ParsedTransaction,
    ParseRequest,
    ReceiptScan,
)
from app.schemas.category import CategoryRead
from app.services.ai.categorize import suggest_category
from app.services.ai.chat import chat
from app.services.ai.client import AIRequestError, AIUnavailableError, provider_status
from app.services.ai.insights import generate_insights
from app.services.ai.parse_entry import parse_transaction
from app.services.ai.receipts import MAX_BYTES, InvalidReceiptError, scan_receipt

router = APIRouter(prefix="/ai", tags=["ai"])

T = TypeVar("T")


def _run(fn: Callable[[], T]) -> T:
    """Map AI failures to clear HTTP errors."""
    try:
        return fn()
    except AIUnavailableError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc
    except AIRequestError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc


@router.get("/status", response_model=AIStatus)
def ai_status(current_user: CurrentUser) -> AIStatus:
    name, st = provider_status()
    message = st.message
    if name == "off":
        message = "Receipt scanning needs a vision model. Set AI_PROVIDER=ollama (free, local) in backend/.env to turn it on."
    return AIStatus(
        enabled=True, receipt_scanning=st.ready, provider=name, model=st.model, message=None if st.ready else message  # type: ignore[arg-type]
    )


@router.post("/parse", response_model=ParsedTransaction)
def parse(payload: ParseRequest, current_user: CurrentUser, db: DbSession) -> ParsedTransaction:
    """SW-22: turn a sentence into a pre-filled transaction. Nothing is saved."""
    return parse_transaction(db, current_user, payload.text)


@router.post("/categorize", response_model=CategorySuggestion)
def categorize(payload: CategorySuggestionRequest, current_user: CurrentUser, db: DbSession) -> CategorySuggestion:
    category, source, confidence = suggest_category(
        db,
        current_user.id,
        description=payload.description,
        transaction_type=payload.transaction_type.value,
        amount=payload.amount,
        payment_method=payload.payment_method.value if payload.payment_method else None,
    )
    return CategorySuggestion(
        category=CategoryRead.model_validate(category) if category else None,
        source=source,
        confidence=confidence,
    )


@router.get("/insights", response_model=InsightsResponse)
def insights(month: MonthParam, current_user: CurrentUser, db: DbSession) -> InsightsResponse:
    return generate_insights(db, current_user, month)


@router.post("/chat", response_model=ChatResponse)
def chat_endpoint(payload: ChatRequest, current_user: CurrentUser, db: DbSession) -> ChatResponse:
    try:
        return chat(db, current_user, payload.messages)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc


@router.post("/receipt", response_model=ReceiptScan)
def receipt(file: UploadFile, current_user: CurrentUser, db: DbSession) -> ReceiptScan:
    data = file.file.read(MAX_BYTES + 1)
    try:
        return _run(lambda: scan_receipt(db, current_user, data))
    except InvalidReceiptError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
