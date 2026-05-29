from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_product_repository, get_samsung_product_client
from src.api.v1.schemas import SyncProductsResponse
from src.application.products import SyncProductsUseCase
from src.infrastructure.database.repositories import ProductRepository
from src.infrastructure.database.session import get_session
from src.infrastructure.scrapers.samsung_client import SamsungProductClient

router = APIRouter(prefix="/sync", tags=["sync"])


@router.post("/samsung", response_model=SyncProductsResponse)
async def sync_samsung_products(
    session: Annotated[AsyncSession, Depends(get_session)],
    repository: Annotated[ProductRepository, Depends(get_product_repository)],
    samsung_client: Annotated[SamsungProductClient, Depends(get_samsung_product_client)],
) -> SyncProductsResponse:
    use_case = SyncProductsUseCase(
        product_source=samsung_client,
        product_repository=repository,
    )
    result = await use_case.execute()
    await session.commit()
    return SyncProductsResponse(
        fetched_count=result.fetched_count,
        persisted_count=result.persisted_count,
        snapshot_count=result.snapshot_count,
    )
