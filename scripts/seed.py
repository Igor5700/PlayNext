"""Populate the database with a polished demo catalog (PS5 game store).

Run after migrations:  python scripts/seed.py
Idempotent: does nothing if categories already exist.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from playnext.core.config import get_settings
from playnext.core.money import Money
from playnext.domain.enums import DiscountType
from playnext.domain.models import PromoCode
from playnext.infrastructure.db.engine import build_engine, build_session_factory
from playnext.infrastructure.db.unit_of_work import make_uow_factory
from playnext.presentation.texts import GTA6_STORY

_STEAM = "https://cdn.cloudflare.steamstatic.com/steam/apps/{}/header.jpg"


def _desc(blurb: str) -> str:
    """Product description in the store's card layout: meta lines + lore."""
    return "Платформа: PS5\nПеревод: русские субтитры\n\n" + blurb


# ── Featured games (shown on the catalog screen, with cover art) ─────────────
FEATURED = [
    (
        "God of War Ragnarök",
        4990,
        12,
        _STEAM.format(2322010),
        _desc(
            "Кратос и его сын Атрей отправляются в опасное путешествие по Девяти "
            "мирам в поисках ответов, пока скандинавские земли готовятся к "
            "пророческой битве Рагнарёк. Их ждут суровые враги, боги и монстры, "
            "а также нелёгкий выбор между местью и семьёй. Один из самых "
            "масштабных эксклюзивов PlayStation с кинематографичным сюжетом и "
            "зрелищными боями."
        ),
    ),
    (
        "Elden Ring",
        3990,
        10,
        _STEAM.format(1245620),
        _desc(
            "Величайшее приключение от FromSoftware и Джорджа Р. Р. Мартина. "
            "Огромный открытый мир Междуземья, десятки боссов, свобода "
            "исследования и фирменная сложность. Станьте Погасшим, соберите "
            "осколки Кольца Элдена и взойдите на трон. Легендарная игра, "
            "получившая множество наград «Игра года»."
        ),
    ),
    (
        "Red Dead Redemption 2",
        2490,
        15,
        _STEAM.format(1174180),
        _desc(
            "Эпическая история о жизни на Диком Западе от создателей GTA. "
            "1899 год, Артур Морган и банда Ван дер Линде спасаются бегством "
            "после неудачного ограбления. Живой открытый мир, проработанные "
            "персонажи и один из лучших сюжетов в истории игр. Абсолютный "
            "must-have для PS5."
        ),
    ),
    (
        "Hogwarts Legacy",
        4490,
        11,
        _STEAM.format(990080),
        _desc(
            "Станьте учеником Хогвартса XIX века и раскройте тайну древней "
            "магии, способной уничтожить волшебный мир. Посещайте занятия, "
            "варите зелья, приручайте магических существ и исследуйте открытый "
            "мир вселенной «Гарри Поттера». Полное погружение для каждого фаната."
        ),
    ),
    (
        "Baldur's Gate 3",
        3690,
        9,
        _STEAM.format(1086940),
        _desc(
            "Ролевая игра года по правилам Dungeons & Dragons. Соберите отряд, "
            "принимайте решения, которые меняют мир, и сражайтесь в глубокой "
            "пошаговой боевой системе. Сотни часов контента, свобода выбора и "
            "невероятная реиграбельность. Шедевр студии Larian."
        ),
    ),
]


def _asset(appid: int) -> str:
    """Steam CDN header image (verified reachable) — same source as FEATURED covers."""
    return f"https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/{appid}/header.jpg"


# ── Regular catalog (35 games) ───────────────────────────────────────────────
# image is None for the 4 titles confirmed absent from Steam (console exclusives):
# Alan Wake 2, Astro Bot, Gran Turismo 7, UFC 5.
GAMES = [
    ("Alan Wake 2", 3290, 6, None, "Психологический хоррор о писателе, чьи книги оживают."),
    (
        "A Plague Tale: Requiem",
        2490,
        5,
        _asset(1182900),
        "Мрачная история брата и сестры в средневековой Франции.",
    ),
    (
        "Assassin's Creed Mirage",
        3490,
        8,
        _asset(3035570),
        "Возвращение к истокам серии: Багдад, стелс и паркур.",
    ),
    (
        "Assassin's Creed Shadows",
        5490,
        7,
        _asset(3159330),
        "Феодальная Япония, два героя — самурай и синоби.",
    ),
    (
        "Assassin's Creed Valhalla",
        2990,
        9,
        _asset(2208920),
        "Эпоха викингов: набеги, битвы и своё поселение.",
    ),
    ("Astro Bot", 3990, 10, None, "Красочный платформер-эксклюзив для всей семьи."),
    (
        "Atomic Heart",
        2790,
        7,
        _asset(668580),
        "Шутер в альтернативном СССР с роботами и аномалиями.",
    ),
    ("Battlefield 2042", 1990, 12, _asset(1517290), "Масштабные онлайн-сражения нового поколения."),
    (
        "Call of Duty: Modern Warfare III",
        4990,
        8,
        "https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/3595270/7d0f21912a075c33bbb5ea558100e187ceb234ac/header.jpg",
        "Кампания, мультиплеер и режим зомби.",
    ),
    (
        "Cyberpunk 2077",
        2990,
        11,
        "https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/1091500/e9047d8ec47ae3d94bb8b464fb0fc9e9972b4ac7/header.jpg",
        "Найт-Сити и нелинейный сюжет от CD Projekt RED.",
    ),
    (
        "Death Stranding Director's Cut",
        2290,
        6,
        _asset(1850570),
        "Уникальное приключение Хидео Кодзимы.",
    ),
    (
        "Detroit: Become Human",
        1790,
        9,
        _asset(1222140),
        "Интерактивная драма о правах андроидов будущего.",
    ),
    (
        "Devil May Cry 5",
        1990,
        7,
        _asset(601150),
        "Стильный слэшер с зрелищными комбо и тремя героями.",
    ),
    (
        "Diablo IV",
        3990,
        8,
        "https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/2344520/80f21a42e378b93e8fbb68ee43103be8ab84891b/header.jpg",
        "Тьма, лут и бесконечные подземелья Санктуария.",
    ),
    ("Dying Light 2", 2490, 6, _asset(534380), "Паркур и выживание в зомби-апокалипсисе."),
    (
        "EA Sports FC 25",
        4290,
        14,
        "https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/2669320/ec3fb7747fd8080ef53d7686e0d98c5abe1f51f1/header.jpg",
        "Новый сезон футбольного симулятора и Ultimate Team.",
    ),
    ("Final Fantasy XVI", 4490, 7, _asset(2515020), "Тёмное фэнтези с эпичными битвами Эйконов."),
    (
        "Ghost of Tsushima Director's Cut",
        3990,
        9,
        _asset(2215430),
        "Самурайская сага на острове Цусима.",
    ),
    ("Gran Turismo 7", 3990, 8, None, "Легендарный автосимулятор с сотнями машин и трасс."),
    (
        "Grand Theft Auto V",
        1990,
        20,
        _asset(3240220),
        "Лос-Сантос, три героя и онлайн-режим GTA Online.",
    ),
    (
        "Horizon Forbidden West",
        3490,
        10,
        _asset(2420110),
        "Элой в мире машин-динозавров на запретном западе.",
    ),
    ("It Takes Two", 1790, 8, _asset(1426210), "Лучшая кооперативная игра — только для двоих."),
    (
        "Marvel's Spider-Man 2",
        4990,
        12,
        _asset(2651280),
        "Питер и Майлз против Венома в открытом Нью-Йорке.",
    ),
    ("Mortal Kombat 1", 3990, 7, _asset(1971870), "Перезапуск легендарного файтинга с фаталити."),
    ("NBA 2K25", 3990, 6, _asset(2878980), "Флагманский баскетбольный симулятор нового сезона."),
    (
        "Need for Speed Unbound",
        2490,
        6,
        "https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/1846380/eacea0635efb7af9054f6b299060fee32404ace7/header.jpg",
        "Уличные гонки, тюнинг и погони от полиции.",
    ),
    (
        "Resident Evil 4 Remake",
        3290,
        9,
        _asset(2050650),
        "Обновлённая классика survival horror с Леоном.",
    ),
    (
        "Sekiro: Shadows Die Twice",
        2790,
        5,
        _asset(814380),
        "Хардкорный экшен про синоби в феодальной Японии.",
    ),
    (
        "Silent Hill 2 Remake",
        4290,
        7,
        _asset(2124490),
        "Легендарный хоррор в полностью пересозданном виде.",
    ),
    (
        "Stellar Blade",
        4490,
        8,
        _asset(3489700),
        "Стильный слэшер-эксклюзив о спасении человечества.",
    ),
    (
        "The Last of Us Part II Remastered",
        3490,
        10,
        _asset(2531310),
        "История мести в постапокалипсисе.",
    ),
    (
        "The Witcher 3: Wild Hunt",
        1490,
        15,
        "https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/292030/ad9240e088f953a84aee814034c50a6a92bf4516/header.jpg",
        "Геральт из Ривии, огромный мир и легендарные квесты.",
    ),
    ("UFC 5", 3990, 6, None, "Реалистичный симулятор смешанных единоборств."),
    (
        "Uncharted: Legacy of Thieves",
        1990,
        8,
        _asset(1659420),
        "Два приключения Нейтана Дрейка в одном сборнике.",
    ),
    ("WWE 2K24", 3490, 6, _asset(2315690), "Симулятор рестлинга с сотнями звёзд WWE."),
]

# ── Grand Theft Auto VI — shown as ONE entry on the catalog screen; opening
# it offers a choice between the two editions below (variant_group="gta6").
# Unreleased game, no public store-page art to hotlink — "local:" tells
# presentation.media.resolve_photo() to pull assets/gta6.jpg instead of
# a Telegram file_id (file_ids aren't portable across bots/tokens).
_GTA6_IMAGE = "local:gta6.jpg"

GTA6_EDITIONS = [
    (
        "GTA 6 — Grand Theft Auto VI (Стандартное издание)",
        7990,
        20,
        _GTA6_IMAGE,
        GTA6_STORY + "\n\nБазовая версия игры, без дополнительного контента.",
        "gta6",
    ),
    (
        "GTA 6 — Grand Theft Auto VI (Ultimate-издание)",
        10490,
        15,
        _GTA6_IMAGE,
        GTA6_STORY + "\n\nВключает бонус-контент, сезонный пропуск и эксклюзивные "
        "косметические предметы для персонажей.",
        "gta6",
    ),
]

# ── PS Plus subscriptions ────────────────────────────────────────────────────
SUBSCRIPTIONS = [
    ("PS Plus Essential — 3 месяца", 1990, 20, "Онлайн-игра, игры месяца и облачные сохранения."),
    ("PS Plus Extra — 3 месяца", 3490, 15, "Essential + каталог из сотен игр PS4 и PS5."),
    ("PS Plus Deluxe — 12 месяцев", 8990, 12, "Каталог игр, классика и пробные версии на год."),
]


async def main() -> None:
    settings = get_settings()
    engine = build_engine(settings.database_url)
    uow_factory = make_uow_factory(build_session_factory(engine))

    async with uow_factory() as uow:
        if await uow.categories.list_all():
            print("Database already seeded — skipping.")
            await engine.dispose()
            return

    # Games category (featured + regular)
    async with uow_factory() as uow:
        games = await uow.categories.create(title="Игры PS5", sort_order=0)
        total = 0
        for title, price, stock, image, description in FEATURED:
            product = await uow.products.create(
                category_id=games.id,
                title=title,
                description=description,
                price=Money.from_major(price),
                image_file_id=image,
                is_featured=True,
            )
            keys = [f"PSN-{product.id}-{i:04d}-{title[:3].upper()}" for i in range(1, stock + 1)]
            await uow.stock.add_keys(product.id, keys)
            total += 1
        for title, price, stock, image, description, group in GTA6_EDITIONS:
            product = await uow.products.create(
                category_id=games.id,
                title=title,
                description=description,
                price=Money.from_major(price),
                image_file_id=image,
                is_featured=True,
                variant_group=group,
            )
            keys = [f"PSN-{product.id}-{i:04d}-GTA6" for i in range(1, stock + 1)]
            await uow.stock.add_keys(product.id, keys)
            total += 1
        for title, price, stock, image, blurb in GAMES:
            product = await uow.products.create(
                category_id=games.id,
                title=title,
                description=_desc(blurb),
                price=Money.from_major(price),
                image_file_id=image,
            )
            keys = [f"PSN-{product.id}-{i:04d}-{title[:3].upper()}" for i in range(1, stock + 1)]
            await uow.stock.add_keys(product.id, keys)
            total += 1
        await uow.commit()
        featured_count = len(FEATURED) + len(GTA6_EDITIONS)
        print(f"+ Игры PS5: {total} games ({featured_count} featured)")

    # Subscriptions category
    async with uow_factory() as uow:
        subs = await uow.categories.create(title="Подписки PS Plus", sort_order=1)
        for title, price, stock, blurb in SUBSCRIPTIONS:
            product = await uow.products.create(
                category_id=subs.id,
                title=title,
                description="Платформа: PS5\n\n" + blurb,
                price=Money.from_major(price),
                image_file_id=None,
            )
            keys = [f"PLUS-{product.id}-{i:04d}" for i in range(1, stock + 1)]
            await uow.stock.add_keys(product.id, keys)
        await uow.commit()
        print(f"+ Подписки PS Plus: {len(SUBSCRIPTIONS)} items")

    async with uow_factory() as uow:
        await uow.promos.create(
            PromoCode(code="WELCOME10", discount_type=DiscountType.PERCENT, value=10)
        )
        await uow.commit()
        print("+ promo WELCOME10 (10%)")

    await engine.dispose()
    print("Seed complete.")


if __name__ == "__main__":
    asyncio.run(main())
