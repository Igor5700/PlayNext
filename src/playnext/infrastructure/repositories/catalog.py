"""Category, product and stock-key repositories."""

from __future__ import annotations

from sqlalchemy import ScalarSelect, Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from playnext.core.money import Money
from playnext.domain.enums import StockKeyStatus
from playnext.domain.errors import OutOfStock
from playnext.domain.models import Category, Product
from playnext.infrastructure.db.models import CategoryORM, ProductORM, StockKeyORM
from playnext.infrastructure.repositories.mappers import to_category, to_product

_AVAILABLE = StockKeyStatus.AVAILABLE.value
_SOLD = StockKeyStatus.SOLD.value


def _stock_subquery() -> ScalarSelect[int]:
    return (
        select(func.count(StockKeyORM.id))
        .where(StockKeyORM.product_id == ProductORM.id, StockKeyORM.status == _AVAILABLE)
        .correlate(ProductORM)
        .scalar_subquery()
    )


def _product_count_subquery(*, active_only: bool) -> ScalarSelect[int]:
    conditions = [ProductORM.category_id == CategoryORM.id]
    if active_only:
        conditions.append(ProductORM.is_active.is_(True))
    return (
        select(func.count(ProductORM.id))
        .where(*conditions)
        .correlate(CategoryORM)
        .scalar_subquery()
    )


class CategoryRepositoryImpl:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, category_id: int) -> Category | None:
        pc = _product_count_subquery(active_only=True)
        row = (
            await self._session.execute(
                select(CategoryORM, pc.label("pc")).where(CategoryORM.id == category_id)
            )
        ).first()
        return to_category(row[0], product_count=row[1]) if row else None

    async def list_active(self) -> list[Category]:
        return await self._list(active_only=True)

    async def list_all(self) -> list[Category]:
        return await self._list(active_only=False)

    async def _list(self, *, active_only: bool) -> list[Category]:
        pc = _product_count_subquery(active_only=active_only)
        stmt = select(CategoryORM, pc.label("pc")).order_by(CategoryORM.sort_order, CategoryORM.id)
        if active_only:
            stmt = stmt.where(CategoryORM.is_active.is_(True))
        rows = (await self._session.execute(stmt)).all()
        return [to_category(row[0], product_count=row[1]) for row in rows]

    async def create(self, *, title: str, sort_order: int) -> Category:
        row = CategoryORM(title=title, sort_order=sort_order)
        self._session.add(row)
        await self._session.flush()
        return to_category(row)

    async def update(
        self,
        category_id: int,
        *,
        title: str | None = None,
        is_active: bool | None = None,
    ) -> None:
        row = await self._session.get(CategoryORM, category_id)
        if row is None:
            return
        if title is not None:
            row.title = title
        if is_active is not None:
            row.is_active = is_active

    async def delete(self, category_id: int) -> None:
        row = await self._session.get(CategoryORM, category_id)
        if row is not None:
            await self._session.delete(row)


class ProductRepositoryImpl:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _base(self) -> Select[tuple[ProductORM, int]]:
        return select(ProductORM, _stock_subquery().label("stock"))

    async def _paginate(
        self,
        stmt: Select[tuple[ProductORM, int]],
        count_stmt: Select[tuple[int]],
        *,
        limit: int,
        offset: int,
    ) -> tuple[list[Product], int]:
        total = int(await self._session.scalar(count_stmt) or 0)
        rows = (
            await self._session.execute(
                stmt.order_by(ProductORM.id.desc()).limit(limit).offset(offset)
            )
        ).all()
        return [to_product(row[0], stock=row[1]) for row in rows], total

    async def get(self, product_id: int) -> Product | None:
        row = (await self._session.execute(self._base().where(ProductORM.id == product_id))).first()
        return to_product(row[0], stock=row[1]) if row else None

    async def get_many(self, product_ids: list[int]) -> list[Product]:
        if not product_ids:
            return []
        stmt = self._base().where(ProductORM.id.in_(product_ids))
        rows = (await self._session.execute(stmt)).all()
        return [to_product(row[0], stock=row[1]) for row in rows]

    async def list_by_category(
        self, category_id: int, *, limit: int, offset: int, active_only: bool = True
    ) -> tuple[list[Product], int]:
        stmt = self._base().where(ProductORM.category_id == category_id)
        count = select(func.count(ProductORM.id)).where(ProductORM.category_id == category_id)
        if active_only:
            stmt = stmt.where(ProductORM.is_active.is_(True))
            count = count.where(ProductORM.is_active.is_(True))
        return await self._paginate(stmt, count, limit=limit, offset=offset)

    async def search(self, query: str, *, limit: int, offset: int) -> tuple[list[Product], int]:
        pattern = f"%{query}%"
        cond = ProductORM.is_active.is_(True) & ProductORM.title.ilike(pattern)
        stmt = self._base().where(cond)
        count = select(func.count(ProductORM.id)).where(cond)
        return await self._paginate(stmt, count, limit=limit, offset=offset)

    async def list_newest(self, *, limit: int) -> list[Product]:
        rows = (
            await self._session.execute(
                self._base()
                .where(ProductORM.is_active.is_(True))
                .order_by(ProductORM.id.desc())
                .limit(limit)
            )
        ).all()
        return [to_product(row[0], stock=row[1]) for row in rows]

    async def list_all(self, *, limit: int, offset: int) -> tuple[list[Product], int]:
        return await self._paginate(
            self._base(), select(func.count(ProductORM.id)), limit=limit, offset=offset
        )

    async def list_featured(self, *, limit: int) -> list[Product]:
        rows = (
            await self._session.execute(
                self._base()
                .where(ProductORM.is_active.is_(True), ProductORM.is_featured.is_(True))
                .order_by(ProductORM.id)
                .limit(limit)
            )
        ).all()
        return [to_product(row[0], stock=row[1]) for row in rows]

    async def list_by_variant_group(self, group: str) -> list[Product]:
        rows = (
            await self._session.execute(
                self._base()
                .where(ProductORM.is_active.is_(True), ProductORM.variant_group == group)
                .order_by(ProductORM.id)
            )
        ).all()
        return [to_product(row[0], stock=row[1]) for row in rows]

    async def create(
        self,
        *,
        category_id: int,
        title: str,
        description: str,
        price: Money,
        image_file_id: str | None,
        is_featured: bool = False,
        variant_group: str | None = None,
    ) -> Product:
        row = ProductORM(
            category_id=category_id,
            title=title,
            description=description,
            price_minor=price.minor,
            image_file_id=image_file_id,
            is_featured=is_featured,
            variant_group=variant_group,
        )
        self._session.add(row)
        await self._session.flush()
        return to_product(row, stock=0)

    async def update(
        self,
        product_id: int,
        *,
        title: str | None = None,
        description: str | None = None,
        price: Money | None = None,
        image_file_id: str | None = None,
        is_active: bool | None = None,
    ) -> None:
        row = await self._session.get(ProductORM, product_id)
        if row is None:
            return
        if title is not None:
            row.title = title
        if description is not None:
            row.description = description
        if price is not None:
            row.price_minor = price.minor
        if image_file_id is not None:
            row.image_file_id = image_file_id
        if is_active is not None:
            row.is_active = is_active

    async def delete(self, product_id: int) -> None:
        row = await self._session.get(ProductORM, product_id)
        if row is not None:
            await self._session.delete(row)

    async def count_active(self) -> int:
        return int(
            await self._session.scalar(
                select(func.count(ProductORM.id)).where(ProductORM.is_active.is_(True))
            )
            or 0
        )


class StockKeyRepositoryImpl:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_keys(self, product_id: int, secrets: list[str]) -> int:
        clean = [s.strip() for s in secrets if s.strip()]
        self._session.add_all(StockKeyORM(product_id=product_id, secret=secret) for secret in clean)
        await self._session.flush()
        return len(clean)

    async def count_available(self, product_id: int) -> int:
        return int(
            await self._session.scalar(
                select(func.count(StockKeyORM.id)).where(
                    StockKeyORM.product_id == product_id, StockKeyORM.status == _AVAILABLE
                )
            )
            or 0
        )

    async def total_available(self) -> int:
        return int(
            await self._session.scalar(
                select(func.count(StockKeyORM.id)).where(StockKeyORM.status == _AVAILABLE)
            )
            or 0
        )

    async def consume(self, product_id: int, quantity: int, *, order_id: int) -> list[str]:
        rows = list(
            await self._session.scalars(
                select(StockKeyORM)
                .where(StockKeyORM.product_id == product_id, StockKeyORM.status == _AVAILABLE)
                .with_for_update(skip_locked=True)
                .limit(quantity)
            )
        )
        if len(rows) < quantity:
            raise OutOfStock
        for row in rows:
            row.status = _SOLD
            row.order_id = order_id
        await self._session.flush()
        return [row.secret for row in rows]

    async def has_sold(self, product_id: int) -> bool:
        row = await self._session.scalar(
            select(StockKeyORM.id)
            .where(StockKeyORM.product_id == product_id, StockKeyORM.status == _SOLD)
            .limit(1)
        )
        return row is not None

    async def has_sold_in_category(self, category_id: int) -> bool:
        row = await self._session.scalar(
            select(StockKeyORM.id)
            .join(ProductORM, StockKeyORM.product_id == ProductORM.id)
            .where(ProductORM.category_id == category_id, StockKeyORM.status == _SOLD)
            .limit(1)
        )
        return row is not None
