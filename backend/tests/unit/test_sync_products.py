from collections.abc import Sequence
from datetime import date
from decimal import Decimal

from src.application.products import SyncProductsUseCase
from src.domain.products import Product, ProductStatus, StoreProvider


class FakeProductSource:
    def __init__(self, products: Sequence[Product]) -> None:
        self._products = products

    async def fetch_products(self) -> Sequence[Product]:
        return self._products


class FakeProductRepository:
    def __init__(self) -> None:
        self.upserted: list[Product] = []
        self.snapshots: list[tuple[object, date, Decimal, str]] = []

    async def upsert_product(self, product: Product) -> object:
        self.upserted.append(product)
        return {"external_id": product.external_id}

    async def save_price_snapshot(
        self,
        product_model: object,
        captured_on: date,
        price: Decimal,
        status: str,
    ) -> object:
        self.snapshots.append((product_model, captured_on, price, status))
        return product_model


def make_product(current_price: Decimal | None) -> Product:
    return Product(
        provider=StoreProvider.SAMSUNG,
        external_id="SM-S928",
        name="Galaxy S24 Ultra",
        status=ProductStatus.IN_STOCK,
        current_price=current_price,
    )


async def test_sync_products_persists_products_and_daily_snapshots() -> None:
    product = make_product(Decimal("24000000"))
    repository = FakeProductRepository()
    use_case = SyncProductsUseCase(FakeProductSource([product]), repository)

    result = await use_case.execute(captured_on=date(2026, 5, 28))

    assert result.fetched_count == 1
    assert result.persisted_count == 1
    assert result.snapshot_count == 1
    assert repository.upserted == [product]
    assert repository.snapshots == [
        ({"external_id": "SM-S928"}, date(2026, 5, 28), Decimal("24000000"), "in_stock")
    ]


async def test_sync_products_skips_snapshot_when_current_price_is_missing() -> None:
    product = make_product(None)
    repository = FakeProductRepository()
    use_case = SyncProductsUseCase(FakeProductSource([product]), repository)

    result = await use_case.execute(captured_on=date(2026, 5, 28))

    assert result.fetched_count == 1
    assert result.persisted_count == 1
    assert result.snapshot_count == 0
    assert repository.snapshots == []

