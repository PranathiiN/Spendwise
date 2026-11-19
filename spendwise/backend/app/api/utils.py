from collections.abc import Iterable
from typing import Any

from fastapi import HTTPException, status


def reject_nulls(data: dict[str, Any], required_fields: Iterable[str]) -> None:
    """For PATCH bodies: a required column may be omitted, but not explicitly set to null."""
    for field in required_fields:
        if field in data and data[field] is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"'{field}' cannot be null",
            )


def not_found(resource: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{resource} not found")
