"""Resolve a product's stored image reference into something aiogram can send.

Most products store a public image URL or a Telegram file_id directly. A
`local:` prefix means the file lives in ASSETS_DIR instead — used for images
that have no stable public URL (e.g. unreleased-game key art) and would
otherwise need a bot-specific file_id, which silently breaks every time the
bot token changes (file_ids aren't portable across bots).
"""

from __future__ import annotations

from aiogram.types import FSInputFile, InputFile

from playnext.core.config import ASSETS_DIR

_LOCAL_PREFIX = "local:"


def resolve_photo(image_ref: str | None) -> str | InputFile | None:
    if image_ref is None:
        return None
    if image_ref.startswith(_LOCAL_PREFIX):
        return FSInputFile(ASSETS_DIR / image_ref.removeprefix(_LOCAL_PREFIX))
    return image_ref
