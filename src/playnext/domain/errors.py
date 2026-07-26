"""Concrete domain errors with user-facing messages."""

from __future__ import annotations

from playnext.core.exceptions import BusinessRuleError, NotFoundError, ValidationError


class ProductNotFound(NotFoundError):
    user_message = "Товар не найден или снят с продажи."


class CategoryNotFound(NotFoundError):
    user_message = "Категория не найдена."


class OrderNotFound(NotFoundError):
    user_message = "Заказ не найден."


class CartEmpty(BusinessRuleError):
    user_message = "Ваша корзина пуста."


class OutOfStock(BusinessRuleError):
    user_message = "Недостаточно товара в наличии."


class InsufficientBalance(BusinessRuleError):
    user_message = "Недостаточно средств на балансе. Пополните кошелёк."


class PromoInvalid(ValidationError):
    user_message = "Промокод недействителен."


class UserBlocked(BusinessRuleError):
    user_message = "Ваш аккаунт заблокирован. Обратитесь в поддержку."


class ProductHasSalesHistory(BusinessRuleError):
    user_message = (
        "Нельзя удалить товар — есть проданные ключи. Снимите его с продажи вместо удаления."
    )


class CategoryHasSalesHistory(BusinessRuleError):
    user_message = (
        "Нельзя удалить категорию — в ней есть товары с проданными ключами. "
        "Скройте категорию вместо удаления."
    )
