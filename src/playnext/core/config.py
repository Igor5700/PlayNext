"""Typed, validated application configuration (12-factor, env-driven)."""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"


class Environment(StrEnum):
    LOCAL = "local"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """Single source of truth for configuration.

    Everything is validated on boot — a misconfigured deployment fails fast and
    loudly instead of erroring deep inside a handler at runtime.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
    )

    # ── Telegram ─────────────────────────────────────────────────────────────
    bot_token: str = Field(alias="BOT_TOKEN")
    admin_ids: frozenset[int] = Field(default_factory=frozenset, alias="ADMIN_IDS")

    # ── Database ─────────────────────────────────────────────────────────────
    database_url: str = Field(
        default="postgresql+asyncpg://playnext:playnext@localhost:5432/playnext",
        alias="DATABASE_URL",
    )

    # ── Payments ─────────────────────────────────────────────────────────────
    # Demo top-ups are always available. Crypto Pay is added on top whenever a
    # token is configured — both providers coexist, the user picks per top-up.
    crypto_pay_token: str = Field(default="", alias="CRYPTO_PAY_TOKEN")
    crypto_pay_testnet: bool = Field(default=False, alias="CRYPTO_PAY_TESTNET")

    # ── Observability ────────────────────────────────────────────────────────
    sentry_dsn: str = Field(default="", alias="SENTRY_DSN")

    @field_validator("bot_token", "crypto_pay_token", "sentry_dsn", mode="before")
    @classmethod
    def _strip(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    # ── Runtime ──────────────────────────────────────────────────────────────
    environment: Environment = Field(default=Environment.LOCAL, alias="ENVIRONMENT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_json: bool = Field(default=False, alias="LOG_JSON")
    currency: str = Field(default="RUB", alias="CURRENCY")

    @field_validator("admin_ids", mode="before")
    @classmethod
    def _parse_admin_ids(cls, value: object) -> frozenset[int]:
        """Accept "111,222", "111 222", a single int, or an iterable of ids.

        Note: pydantic-settings JSON-decodes a lone numeric env value into an int
        before this runs, so a single-id `ADMIN_IDS=123` arrives here as an int.
        """
        if value is None or value == "":
            return frozenset()
        if isinstance(value, bool):
            raise ValueError("ADMIN_IDS must be integers")
        if isinstance(value, int):
            return frozenset({value})
        if isinstance(value, str):
            raw = value.replace(",", " ").split()
            return frozenset(int(x) for x in raw)
        if isinstance(value, (list, tuple, set, frozenset)):
            return frozenset(int(x) for x in value)
        raise ValueError("ADMIN_IDS must be a comma/space separated list of integers")

    @property
    def is_production(self) -> bool:
        return self.environment is Environment.PRODUCTION

    def is_admin(self, user_id: int) -> bool:
        return user_id in self.admin_ids


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings accessor. Import this, never instantiate Settings directly."""
    return Settings()
