import asyncio

import httpx
import structlog

from src.application.products import SyncProductsUseCase
from src.infrastructure.database.repositories import ProductRepository
from src.infrastructure.database.session import async_session_factory
from src.infrastructure.scrapers.samsung_client import SamsungProductClient
from src.infrastructure.tasks.celery_app import celery_app

logger = structlog.get_logger(__name__)


@celery_app.task(name="src.infrastructure.tasks.product_tasks.sync_samsung_products")  # type: ignore[untyped-decorator]
def sync_samsung_products() -> dict[str, int]:
    return asyncio.run(_sync_samsung_products())


async def _sync_samsung_products() -> dict[str, int]:
    async with httpx.AsyncClient(timeout=10.0) as http_client:
        async with async_session_factory() as session:
            repository = ProductRepository(session)
            product_source = SamsungProductClient(http_client)
            use_case = SyncProductsUseCase(
                product_source=product_source,
                product_repository=repository,
            )
            result = await use_case.execute()
            await session.commit()

    logger.info(
        "samsung_products_synced",
        fetched_count=result.fetched_count,
        persisted_count=result.persisted_count,
        snapshot_count=result.snapshot_count,
    )
    return {
        "fetched_count": result.fetched_count,
        "persisted_count": result.persisted_count,
        "snapshot_count": result.snapshot_count,
    }
