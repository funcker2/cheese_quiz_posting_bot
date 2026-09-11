from dataclasses import dataclass
from enum import Enum

# Telegram sendPhoto / InputMediaPhoto caption limit after entity parsing.
CAPTION_LIMIT = 1024


def utf16_len(text: str) -> int:
    return len(text.encode("utf-16-le")) // 2


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
