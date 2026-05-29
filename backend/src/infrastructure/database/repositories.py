from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.domain.price_history import PriceSnapshot
from src.domain.products import Product, StoreProvider
from src.domain.products.value_objects import ProductStatus
from src.infrastructure.database.models import PriceSnapshotModel, ProductModel, StoreModel


class ProductRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_or_create_store(self, provider: StoreProvider) -> StoreModel:
        statement = select(StoreModel).where(StoreModel.code == provider.value)
        store = await self._session.scalar(statement)
        if store is not None:
            return store

        store = StoreModel(code=provider.value, name=provider.value.replace("_", " ").title())
        self._session.add(store)
        await self._session.flush()
        return store

    async def upsert_product(self, product: Product) -> ProductModel:
        store = await self.get_or_create_store(product.provider)
        statement = select(ProductModel).where(
            ProductModel.store_id == store.id,
            ProductModel.external_id == product.external_id,
        )
        model = await self._session.scalar(statement)

        if model is None:
            model = ProductModel(
                store_id=store.id,
                external_id=product.external_id,
                name=product.name,
                category=product.category,
                product_url=product.product_url,
                status=product.status.value,
                original_price=product.original_price,
                current_price=product.current_price,
            )
            self._session.add(model)
            await self._session.flush()
            return model

        model.name = product.name
        model.category = product.category
        model.product_url = product.product_url
        model.status = product.status.value
        model.original_price = product.original_price
        model.current_price = product.current_price
        await self._session.flush()
        return model

    async def save_price_snapshot(
        self,
        product_model: ProductModel,
        captured_on: date,
        price: Decimal,
        status: str,
    ) -> PriceSnapshotModel:
        statement = select(PriceSnapshotModel).where(
            PriceSnapshotModel.product_id == product_model.id,
            PriceSnapshotModel.captured_on == captured_on,
        )
        snapshot = await self._session.scalar(statement)
        if snapshot is None:
            snapshot = PriceSnapshotModel(
                product_id=product_model.id,
                captured_on=captured_on,
                price=price,
                status=status,
            )
            self._session.add(snapshot)
            await self._session.flush()
            return snapshot

        snapshot.price = price
        snapshot.status = status
        await self._session.flush()
        return snapshot

    async def list_products(self, provider: StoreProvider | None = None) -> list[Product]:
        statement = select(ProductModel).options(selectinload(ProductModel.store)).join(StoreModel)
        if provider is not None:
            statement = statement.where(StoreModel.code == provider.value)
        statement = statement.order_by(ProductModel.name)

        rows = await self._session.scalars(statement)
        return [self._to_domain(model) for model in rows]

    def _to_domain(self, model: ProductModel) -> Product:
        provider = StoreProvider(model.store.code)
        try:
            status = ProductStatus(model.status)
        except ValueError:
            status = ProductStatus.UNKNOWN

        return Product(
            provider=provider,
            external_id=model.external_id,
            name=model.name,
            status=status,
            product_url=model.product_url,
            category=model.category,
            original_price=model.original_price,
            current_price=model.current_price,
        )

    async def list_price_history(
        self,
        provider: StoreProvider,
        external_product_id: str,
    ) -> list[PriceSnapshot]:
        statement = (
            select(PriceSnapshotModel)
            .join(ProductModel)
            .join(StoreModel)
            .where(
                StoreModel.code == provider.value,
                ProductModel.external_id == external_product_id,
            )
            .order_by(PriceSnapshotModel.captured_on)
        )
        rows = await self._session.scalars(statement)
        return [
            PriceSnapshot(
                provider=provider,
                external_product_id=external_product_id,
                captured_on=row.captured_on,
                price=row.price,
                status=self._status_from_value(row.status),
            )
            for row in rows
        ]

    def _status_from_value(self, value: str) -> ProductStatus:
        try:
            return ProductStatus(value)
        except ValueError:
            return ProductStatus.UNKNOWN
