from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any

from src.application.products.ports import ProductRepository, ProductSource


@dataclass(frozen=True, slots=True)
class SyncProductsResult:
    fetched_count: int
    persisted_count: int
    snapshot_count: int


class SyncProductsUseCase:
    def __init__(
        self,
        product_source: ProductSource,
        product_repository: ProductRepository[Any],
    ) -> None:
        self._product_source = product_source
        self._product_repository = product_repository

    async def execute(self, captured_on: date | None = None) -> SyncProductsResult:
        products = await self._product_source.fetch_products()
        snapshot_date = captured_on or datetime.now(UTC).date()
        persisted_count = 0
        snapshot_count = 0

        for product in products:
            product_record = await self._product_repository.upsert_product(product)
            persisted_count += 1

            if product.current_price is None:
                continue

            await self._product_repository.save_price_snapshot(
                product_model=product_record,
                captured_on=snapshot_date,
                price=product.current_price,
                status=product.status.value,
            )
            snapshot_count += 1

        return SyncProductsResult(
            fetched_count=len(products),
            persisted_count=persisted_count,
            snapshot_count=snapshot_count,
        )
