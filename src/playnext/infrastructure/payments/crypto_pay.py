"""Crypto Pay gateway — async, via httpx (never blocks the event loop).

Crypto Pay is the payment API behind @CryptoBot: create an invoice priced in
fiat (RUB) -> the payer settles it with any crypto asset Crypto Pay accepts ->
we poll invoice status. Docs: https://help.crypt.bot/crypto-pay-api
"""

from __future__ import annotations

from typing import TypeVar

import httpx
from pydantic import BaseModel, ConfigDict, ValidationError

from playnext.application.ports.payment_gateway import GatewayPayment
from playnext.core.exceptions import PaymentError
from playnext.core.money import Money
from playnext.domain.enums import PaymentStatus

_MAINNET_BASE = "https://pay.crypt.bot/api"
_TESTNET_BASE = "https://testnet-pay.crypt.bot/api"

_STATUS_MAP = {
    "active": PaymentStatus.PENDING,
    "paid": PaymentStatus.SUCCEEDED,
    "expired": PaymentStatus.EXPIRED,
}


# ── Response shapes ───────────────────────────────────────────────────────────
# Validated with pydantic rather than indexed as raw dicts: an unexpected or
# malformed response from the provider becomes a clean PaymentError instead of
# an uncaught KeyError/TypeError deep inside gateway parsing.
class _Invoice(BaseModel):
    model_config = ConfigDict(extra="ignore")

    invoice_id: int
    status: str
    bot_invoice_url: str | None = None
    pay_url: str | None = None


class _CreateInvoiceResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    ok: bool
    result: _Invoice | None = None
    error: object = None


class _InvoiceList(BaseModel):
    model_config = ConfigDict(extra="ignore")

    items: list[_Invoice] = []


class _GetInvoicesResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    ok: bool
    result: _InvoiceList | None = None
    error: object = None


_ModelT = TypeVar("_ModelT", bound=BaseModel)


def _parse(model_cls: type[_ModelT], raw: object, *, method: str) -> _ModelT:
    try:
        return model_cls.model_validate(raw)
    except ValidationError as exc:
        raise PaymentError(f"Crypto Pay {method} returned an unexpected response: {exc}") from exc


def _to_gateway_payment(invoice: _Invoice) -> GatewayPayment:
    return GatewayPayment(
        provider_payment_id=str(invoice.invoice_id),
        status=_STATUS_MAP.get(invoice.status, PaymentStatus.PENDING),
        confirmation_url=invoice.bot_invoice_url or invoice.pay_url,
    )


class CryptoPayGateway:
    name = "crypto_pay"

    def __init__(self, *, api_token: str, testnet: bool = False) -> None:
        if not api_token:
            raise PaymentError("Crypto Pay API token is not configured")
        self._client = httpx.AsyncClient(
            base_url=_TESTNET_BASE if testnet else _MAINNET_BASE,
            headers={"Crypto-Pay-API-Token": api_token},
            timeout=httpx.Timeout(20.0),
            # Don't inherit the host's proxy env/registry settings — httpx reads
            # them by default (trust_env=True) and chokes on schemes it can't
            # parse (e.g. a system-wide socks4:// proxy), which has nothing to
            # do with reaching the Crypto Pay API.
            trust_env=False,
        )

    async def create_payment(
        self, *, amount: Money, description: str, idempotence_key: str
    ) -> GatewayPayment:
        raw = await self._post(
            "createInvoice",
            {
                "currency_type": "fiat",
                "fiat": amount.currency,
                "amount": f"{amount.major:.2f}",
                "description": description[:1024],
                "payload": idempotence_key,
                "expires_in": 3600,
            },
        )
        parsed = _parse(_CreateInvoiceResponse, raw, method="createInvoice")
        if not parsed.ok or parsed.result is None:
            raise PaymentError(f"Crypto Pay createInvoice error: {parsed.error}")
        return _to_gateway_payment(parsed.result)

    async def get_payment(self, provider_payment_id: str) -> GatewayPayment:
        raw = await self._get("getInvoices", {"invoice_ids": provider_payment_id})
        parsed = _parse(_GetInvoicesResponse, raw, method="getInvoices")
        if not parsed.ok or parsed.result is None or not parsed.result.items:
            raise PaymentError(f"Crypto Pay invoice {provider_payment_id} not found")
        return _to_gateway_payment(parsed.result.items[0])

    async def _post(self, method: str, payload: dict[str, object]) -> object:
        try:
            response = await self._client.post(f"/{method}", json=payload)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise PaymentError(f"Crypto Pay {method} failed: {exc}") from exc
        return response.json()

    async def _get(self, method: str, params: dict[str, str]) -> object:
        try:
            response = await self._client.get(f"/{method}", params=params)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise PaymentError(f"Crypto Pay {method} failed: {exc}") from exc
        return response.json()

    async def aclose(self) -> None:
        await self._client.aclose()
