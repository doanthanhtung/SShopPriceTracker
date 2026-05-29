from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from src.domain.products.value_objects import ProductStatus, StoreProvider


@dataclass(frozen=True, slots=True)
class PriceSnapshot:
    provider: StoreProvider
    external_product_id: str
    captured_on: date
    price: Decimal
    status: ProductStatus

    def is_price_drop_from(self, previous_price: Decimal | None) -> bool:
        if previous_price is None:
            return False
        return self.price > 0 and self.price < previous_price

