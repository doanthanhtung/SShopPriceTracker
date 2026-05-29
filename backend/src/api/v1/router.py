from fastapi import APIRouter
from pydantic import BaseModel

from src.api.v1.products import router as products_router
from src.api.v1.sync import router as sync_router


class HealthResponse(BaseModel):
    status: str
    service: str


api_router = APIRouter()
api_router.include_router(products_router)
api_router.include_router(sync_router)


@api_router.get("/health", response_model=HealthResponse, tags=["health"])
async def health_check() -> HealthResponse:
    return HealthResponse(status="ok", service="backend")
