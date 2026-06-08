from dataclasses import dataclass
from os import getenv
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Channel:
    id: str
    label: str


def _parse_channels(raw: str) -> tuple[Channel, ...]:
    channels: list[Channel] = []
    for entry in raw.split(";"):
        entry = entry.strip()
        if not entry:
            continue
        parts = entry.split("|", maxsplit=1)
        ch_id = parts[0].strip()
        ch_label = parts[1].strip() if len(parts) > 1 else ch_id
        channels.append(Channel(id=ch_id, label=ch_label))
    return tuple(channels)


@dataclass(frozen=True)
class Config:
    bot_token: str
    channels: tuple[Channel, ...]
    channels_sunny: tuple[Channel, ...]
    channels_harry: tuple[Channel, ...]
    admin_ids: tuple[int, ...]
    signup_bot_url: str
    button_text: str

    @classmethod
    def from_env(cls) -> "Config":
        token = getenv("BOT_TOKEN")
        if not token:
            raise ValueError("BOT_TOKEN is not set")

        raw_admins = getenv("ADMIN_IDS", "")
        admin_ids = tuple(
            int(uid.strip()) for uid in raw_admins.split(",") if uid.strip()
        )
        if not admin_ids:
            raise ValueError("ADMIN_IDS is not set — provide comma-separated Telegram user IDs")

        channels = _parse_channels(getenv("CHANNELS", ""))
        if not channels:
            raise ValueError("CHANNELS is not set — use format: @id1|Label1;@id2|Label2")

        channels_sunny = _parse_channels(getenv("CHANNELS_SUNNY", ""))
        channels_harry = _parse_channels(getenv("CHANNELS_HARRY", ""))

        return cls(
            bot_token=token,
            channels=channels,
            channels_sunny=channels_sunny,
            channels_harry=channels_harry,
            admin_ids=admin_ids,
            signup_bot_url=getenv("SIGNUP_BOT_URL", "https://t.me/cheese_quiz_bg_bot"),
            button_text=getenv("BUTTON_TEXT", "Записаться на игру"),
        )
