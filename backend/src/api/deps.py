from collections.abc import AsyncIterator
from typing import Annotated

import httpx
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.repositories import ProductRepository
from src.infrastructure.database.session import get_session
from src.infrastructure.scrapers.samsung_client import SamsungProductClient


async def get_http_client() -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient(timeout=10.0) as client:
        yield client


async def get_product_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ProductRepository:
    return ProductRepository(session)


async def get_samsung_product_client(
    http_client: Annotated[httpx.AsyncClient, Depends(get_http_client)],
) -> SamsungProductClient:
    return SamsungProductClient(http_client)
