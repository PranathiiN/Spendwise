import uuid
from datetime import date
from typing import Annotated

from fastapi import Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User
from app.utils.dates import parse_month

bearer_scheme = HTTPBearer(auto_error=False, description="Paste the access_token from /api/auth/login")

DbSession = Annotated[Session, Depends(get_db)]


def _unauthorized(detail: str = "Not authenticated") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _unauthorized()
    subject = decode_access_token(credentials.credentials)
    if subject is None:
        raise _unauthorized("Invalid or expired token")
    try:
        user_id = uuid.UUID(subject)
    except ValueError:
        raise _unauthorized("Invalid or expired token")
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise _unauthorized("Invalid or expired token")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def month_query(
    month: Annotated[
        str | None,
        Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$", description="Month as YYYY-MM (defaults to current month)"),
    ] = None,
) -> date:
    return parse_month(month)


MonthParam = Annotated[date, Depends(month_query)]
