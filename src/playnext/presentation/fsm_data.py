"""Typed shapes for FSM scratch data.

`FSMContext` stores a plain `dict[str, Any]` per user under the hood — this
doesn't change that at runtime, but it gives mypy a shape to check reads
against, so a mistyped/missing key surfaces at review time instead of as a
`KeyError` mid-flow. Each TypedDict below describes the data as it looks at
the point its flow reads it back (after all the preceding steps populated it).
"""

from __future__ import annotations

from typing import TypedDict, TypeVar, cast

from aiogram.fsm.context import FSMContext


class ProductDraftData(TypedDict):
    category_id: int
    title: str
    description: str
    price_minor: int


class ProductEditTarget(TypedDict):
    product_id: int
    page: int


class CategoryEditTarget(TypedDict):
    category_id: int


class PromoDraftData(TypedDict):
    code: str


class CheckoutDraftData(TypedDict, total=False):
    promo: str | None


_T = TypeVar("_T")


async def get_typed(state: FSMContext, shape: type[_T]) -> _T:
    """Read FSM scratch data as the given TypedDict shape.

    A static-typing aid only — performs no runtime validation. Callers rely on
    their own flow having populated `shape`'s keys by the time this is read.
    """
    del shape  # only used for the generic type parameter
    return cast(_T, await state.get_data())
