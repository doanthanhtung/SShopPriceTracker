from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from src.domain.products.value_objects import ProductStatus, StoreProvider


@dataclass(frozen=True, slots=True)
class Product:
    provider: StoreProvider
    external_id: str
    name: str
    status: ProductStatus
    product_url: str | None = None
    category: str | None = None
    original_price: Decimal | None = None
    current_price: Decimal | None = None

    def discount_percentage(self) -> Decimal:
        if not self.original_price or not self.current_price:
            return Decimal("0")
        if self.original_price <= 0 or self.current_price <= 0:
            return Decimal("0")
        if self.current_price >= self.original_price:
            return Decimal("0")

        discount = (Decimal("1") - (self.current_price / self.original_price)) * Decimal("100")
        return discount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @property
    def is_available(self) -> bool:
        return self.status.is_available

