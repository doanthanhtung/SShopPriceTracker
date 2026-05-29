from datetime import date
from decimal import Decimal

from src.domain.price_history import PriceSnapshot
from src.domain.products import Product, ProductStatus, StoreProvider


def test_product_calculates_discount_percentage() -> None:
    product = Product(
        provider=StoreProvider.SAMSUNG,
        external_id="SM-S928",
        name="Galaxy S24 Ultra",
        status=ProductStatus.IN_STOCK,
        original_price=Decimal("30000000"),
        current_price=Decimal("24000000"),
    )

    assert product.discount_percentage() == Decimal("20.00")


def test_product_discount_is_zero_when_current_price_is_missing() -> None:
    product = Product(
        provider=StoreProvider.SAMSUNG,
        external_id="SM-S928",
        name="Galaxy S24 Ultra",
        status=ProductStatus.IN_STOCK,
        original_price=Decimal("30000000"),
        current_price=None,
    )

    assert product.discount_percentage() == Decimal("0")


def test_samsung_cta_type_maps_to_domain_status() -> None:
    assert ProductStatus.from_samsung_cta_type("whereToBuy") == ProductStatus.IN_STOCK
    assert ProductStatus.from_samsung_cta_type("preOrder") == ProductStatus.PRE_ORDER
    assert ProductStatus.from_samsung_cta_type("outOfStock") == ProductStatus.OUT_OF_STOCK
    assert ProductStatus.from_samsung_cta_type("unexpected") == ProductStatus.UNKNOWN


def test_pre_order_is_available() -> None:
    assert ProductStatus.PRE_ORDER.is_available is True
    assert ProductStatus.OUT_OF_STOCK.is_available is False


def test_price_snapshot_detects_price_drop() -> None:
    snapshot = PriceSnapshot(
        provider=StoreProvider.SAMSUNG,
        external_product_id="SM-S928",
        captured_on=date(2026, 5, 28),
        price=Decimal("24000000"),
        status=ProductStatus.IN_STOCK,
    )

    assert snapshot.is_price_drop_from(Decimal("25000000")) is True
    assert snapshot.is_price_drop_from(Decimal("24000000")) is False
    assert snapshot.is_price_drop_from(None) is False

