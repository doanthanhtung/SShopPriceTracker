from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    provider: str
    external_id: str
    name: str
    status: str
    is_available: bool
    product_url: str | None
    category: str | None
    original_price: Decimal | None
    current_price: Decimal | None
    discount_percentage: Decimal


class SyncProductsResponse(BaseModel):
    fetched_count: int
    persisted_count: int
    snapshot_count: int


class PriceSnapshotResponse(BaseModel):
    captured_on: date
    price: Decimal
    status: str
