import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

from app.models.enums import TransactionType
from app.schemas.common import HexColor, IconName

CategoryName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]


class CategoryCreate(BaseModel):
    name: CategoryName
    transaction_type: TransactionType
    color: HexColor = "#64748b"
    icon_name: IconName = "tag"


class CategoryUpdate(BaseModel):
    """The transaction type cannot be changed because existing transactions depend on it."""

    name: CategoryName | None = None
    color: HexColor | None = None
    icon_name: IconName | None = None


class CategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    transaction_type: TransactionType
    color: str
    icon_name: str
    is_system: bool
    created_at: datetime
