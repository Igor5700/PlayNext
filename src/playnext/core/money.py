"""Money value object.

Money is stored and computed in **minor units** (integer kopecks) — never as a
float. This eliminates the rounding drift that plagues float-based prices and
makes equality and totals exact.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import ClassVar, Final

_MINOR_PER_MAJOR: Final = 100
_NBSP: Final = " "  # non-breaking space between amount and currency


@dataclass(frozen=True, slots=True, order=True)
class Money:
    """An exact monetary amount in minor units (e.g. kopecks)."""

    minor: int
    currency: str = "RUB"

    # ── constructors ─────────────────────────────────────────────────────────
    @classmethod
    def zero(cls, currency: str = "RUB") -> Money:
        return cls(0, currency)

    @classmethod
    def from_major(cls, major: Decimal | int | float | str, currency: str = "RUB") -> Money:
        minor = (Decimal(str(major)) * _MINOR_PER_MAJOR).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )
        return cls(int(minor), currency)

    # ── arithmetic (currency-safe) ───────────────────────────────────────────
    def _check(self, other: Money) -> None:
        if self.currency != other.currency:
            raise ValueError(f"currency mismatch: {self.currency} vs {other.currency}")

    def __add__(self, other: Money) -> Money:
        self._check(other)
        return Money(self.minor + other.minor, self.currency)

    def __sub__(self, other: Money) -> Money:
        self._check(other)
        return Money(self.minor - other.minor, self.currency)

    def __mul__(self, qty: int) -> Money:
        if not isinstance(qty, int):
            raise TypeError("Money can only be multiplied by an integer quantity")
        return Money(self.minor * qty, self.currency)

    __rmul__ = __mul__

    # ── predicates ───────────────────────────────────────────────────────────
    @property
    def is_zero(self) -> bool:
        return self.minor == 0

    @property
    def is_positive(self) -> bool:
        return self.minor > 0

    # ── representations ──────────────────────────────────────────────────────
    @property
    def major(self) -> Decimal:
        return Decimal(self.minor) / _MINOR_PER_MAJOR

    _SYMBOLS: ClassVar[dict[str, str]] = {"RUB": "₽", "USD": "$", "EUR": "€"}

    def format(self) -> str:
        """Human-readable, thousands-grouped, e.g. `1 500 ₽`."""
        symbol = self._SYMBOLS.get(self.currency, self.currency)
        whole, frac = divmod(abs(self.minor), _MINOR_PER_MAJOR)
        grouped = f"{whole:,}".replace(",", _NBSP)
        body = grouped if frac == 0 else f"{grouped},{frac:02d}"
        sign = "-" if self.minor < 0 else ""
        return f"{sign}{body}{_NBSP}{symbol}"

    def __str__(self) -> str:
        return self.format()


def parse_major(raw: str) -> Decimal | None:
    """Parse a user-typed major-unit amount, e.g. "1 500,50" or "1500.5".

    Accepts comma or dot as the decimal separator and tolerates spaces
    (thousands separators / stray whitespace, incl. non-breaking space).
    Returns None for anything that isn't a valid, finite decimal — never
    raises. Kept in core.money (not float()) so user-entered money never
    passes through binary floating point on its way to a `Money`.
    """
    cleaned = raw.strip().replace(" ", "").replace("\xa0", "").replace(",", ".")
    if not cleaned:
        return None
    try:
        value = Decimal(cleaned)
    except InvalidOperation:
        return None
    return value if value.is_finite() else None
