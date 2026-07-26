"""Application-wide exception hierarchy.

Domain/application code raises these; the presentation layer's error middleware
maps them to friendly user messages. Handlers never deal with raw tracebacks.
"""

from __future__ import annotations


class PlayNextError(Exception):
    """Base class for every expected (non-bug) error in the system.

    `user_message` is safe to show to an end user as-is.
    """

    user_message: str = "Что-то пошло не так. Попробуйте позже."

    def __init__(self, message: str | None = None, *, user_message: str | None = None) -> None:
        super().__init__(message or self.__class__.__name__)
        if user_message is not None:
            self.user_message = user_message


class NotFoundError(PlayNextError):
    user_message = "Не найдено. Возможно, элемент был удалён."


class ValidationError(PlayNextError):
    user_message = "Некорректные данные. Проверьте ввод и попробуйте снова."


class BusinessRuleError(PlayNextError):
    """A valid request that violates a business rule (e.g. out of stock)."""


class PermissionDeniedError(PlayNextError):
    user_message = "Недостаточно прав для этого действия."


class PaymentError(PlayNextError):
    user_message = "Не удалось обработать платёж. Попробуйте позже."
