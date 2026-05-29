from collections.abc import Sequence
from datetime import date
from decimal import Decimal
from typing import Protocol, TypeVar

from src.domain.products import Product

ProductRecord = TypeVar("ProductRecord")


class ProductSource(Protocol):
    async def fetch_products(self) -> Sequence[Product]:
        """Fetch products from an external provider."""


class ProductRepository(Protocol[ProductRecord]):
    async def upsert_product(self, product: Product) -> ProductRecord:
        """Create or update a product and return its persistence record."""

    async def save_price_snapshot(
        self,
        product_model: ProductRecord,
        captured_on: date,
        price: Decimal,
        status: str,
    ) -> object:
        """Persist the product price/status snapshot for a day."""

