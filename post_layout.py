from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

# Telegram sendPhoto / InputMediaPhoto caption limit after entity parsing.
CAPTION_LIMIT = 1024


def utf16_len(text: str) -> int:
    return len(text.encode("utf-16-le")) // 2


def caption_overflow(text: str) -> int:
    return max(0, utf16_len(text) - CAPTION_LIMIT)


def _ru_symbol_word(n: int) -> str:
    n_abs = abs(n) % 100
    n1 = n_abs % 10
    if 11 <= n_abs <= 14:
        return "символов"
    if n1 == 1:
        return "символ"
    if 2 <= n1 <= 4:
        return "символа"
    return "символов"


def split_preview_notice(text: str) -> str | None:
    over = caption_overflow(text)
    if over == 0:
        return None
    amount = f"{over} {_ru_symbol_word(over)}"
    return (
        f"⚠️ Текст длиннее подписи к фото на {amount}. "
        f"Сейчас уйдёт двумя сообщениями. "
        f"Укороти на {amount}, чтобы склеить фото и текст в один пост."
    )


class CaptionMode(Enum):
    GLUE = "glue"
    SPLIT = "split"


@dataclass(frozen=True)
class PostLayout:
    caption_mode: CaptionMode
    button_on: str  # "media" | "text" | "followup" | "none"


def plan_post_layout(*, n_photos: int, text: str, has_button: bool) -> PostLayout:
    if n_photos < 1:
        raise ValueError("n_photos must be >= 1")

    if utf16_len(text) <= CAPTION_LIMIT:
        if n_photos == 1:
            button_on = "media" if has_button else "none"
        else:
            button_on = "followup" if has_button else "none"
        return PostLayout(caption_mode=CaptionMode.GLUE, button_on=button_on)

    button_on = "text" if has_button else "none"
    return PostLayout(caption_mode=CaptionMode.SPLIT, button_on=button_on)



class CaptionMode(Enum):
    GLUE = "glue"
    SPLIT = "split"


@dataclass(frozen=True)
class PostLayout:
    caption_mode: CaptionMode
    button_on: str  # "media" | "text" | "followup" | "none"


def plan_post_layout(*, n_photos: int, text: str, has_button: bool) -> PostLayout:
    if n_photos < 1:
        raise ValueError("n_photos must be >= 1")

    if utf16_len(text) <= CAPTION_LIMIT:
        if n_photos == 1:
            button_on = "media" if has_button else "none"
        else:
            button_on = "followup" if has_button else "none"
        return PostLayout(caption_mode=CaptionMode.GLUE, button_on=button_on)

    button_on = "text" if has_button else "none"
    return PostLayout(caption_mode=CaptionMode.SPLIT, button_on=button_on)
