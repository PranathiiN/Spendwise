from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.routes import auth, budgets, categories, dashboard, goals, reports, transactions
from app.core.config import settings
from app.core.dependencies import DbSession

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="SpendWise personal finance API (phase 1, no AI features).",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
    expose_headers=["Content-Disposition"],
)

API_PREFIX = "/api"
for module in (auth, categories, transactions, budgets, goals, dashboard, reports):
    app.include_router(module.router, prefix=API_PREFIX)


@app.get("/api/health", tags=["health"])
def health(db: DbSession) -> dict[str, str]:
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:  # pragma: no cover - depends on infrastructure
        raise HTTPException(status_code=503, detail="Database unavailable") from exc
    return {"status": "ok", "database": "ok"}
