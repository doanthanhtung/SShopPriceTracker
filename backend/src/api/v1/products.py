from typing import Annotated

from fastapi import APIRouter, Depends

from src.api.deps import get_product_repository
from src.api.v1.schemas import PriceSnapshotResponse, ProductResponse
from src.domain.products import Product, StoreProvider
from src.infrastructure.database.repositories import ProductRepository

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=list[ProductResponse])
async def list_products(
    repository: Annotated[ProductRepository, Depends(get_product_repository)],
    provider: StoreProvider | None = None,
) -> list[ProductResponse]:
    products = await repository.list_products(provider=provider)
    return [_to_response(product) for product in products]


@router.get(
    "/{provider}/{external_product_id}/price-history",
    response_model=list[PriceSnapshotResponse],
)
async def list_price_history(
    provider: StoreProvider,
    external_product_id: str,
    repository: Annotated[ProductRepository, Depends(get_product_repository)],
) -> list[PriceSnapshotResponse]:
    snapshots = await repository.list_price_history(
        provider=provider,
        external_product_id=external_product_id,
    )
    return [
        PriceSnapshotResponse(
            captured_on=snapshot.captured_on,
            price=snapshot.price,
            status=snapshot.status.value,
        )
        for snapshot in snapshots
    ]


def _to_response(product: Product) -> ProductResponse:
    return ProductResponse(
        provider=product.provider.value,
        external_id=product.external_id,
        name=product.name,
        status=product.status.value,
        is_available=product.is_available,
        product_url=product.product_url,
        category=product.category,
        original_price=product.original_price,
        current_price=product.current_price,
        discount_percentage=product.discount_percentage(),
    )
