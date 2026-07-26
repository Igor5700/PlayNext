"""The main-menu screen: photo banner + welcome caption.

Shown on /start and every time the user navigates back to the menu. The
banner is a local file — Telegram returns a `file_id` after the first upload,
which we cache in-process so later screens reuse it instead of re-uploading.
"""

from __future__ import annotations

from aiogram.types import FSInputFile, Message

from playnext.core.config import ASSETS_DIR, Settings
from playnext.domain.models import User
from playnext.presentation import texts
from playnext.presentation.keyboards.common import main_menu
from playnext.presentation.screen import Screen

_BANNER_PATH = ASSETS_DIR / "welcome_banner.png"
_banner_file_id: str | None = None


def _banner_photo() -> str | FSInputFile | None:
    if _banner_file_id is not None:
        return _banner_file_id
    if _BANNER_PATH.is_file():
        return FSInputFile(_BANNER_PATH)
    return None


def home_screen(user: User, settings: Settings) -> Screen:
    return Screen(
        text=texts.WELCOME,
        markup=main_menu(is_admin=settings.is_admin(user.id)),
        photo=_banner_photo(),
    )


def cache_banner(message: Message | None) -> None:
    global _banner_file_id
    if _banner_file_id is None and message is not None and message.photo:
        _banner_file_id = message.photo[-1].file_id
