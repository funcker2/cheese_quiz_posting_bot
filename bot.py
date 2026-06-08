import asyncio
import logging

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    Message,
    MessageEntity,
)

from config import Config

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

cfg = Config.from_env()
bot = Bot(token=cfg.bot_token)
router = Router()


class PostForm(StatesGroup):
    choosing_project = State()
    waiting_photo = State()
    waiting_more_photo = State()
    waiting_text = State()
    waiting_button_choice = State()
    waiting_button_url = State()
    preview = State()
    choosing_channel = State()
    edit_photo = State()
    edit_more_photo = State()
    edit_text = State()
    edit_find = State()
    edit_replace = State()


PROJECTS = {
    "cheese": {"label": "🧀 CHEESE QUIZ",  "button_text": cfg.button_text, "url": cfg.signup_bot_url, "channels": cfg.channels},
    "sunny":  {"label": "☀️ SUNNY NIGHTS", "button_text": "РЕГИСТРАЦИЯ",   "url": None,               "channels": cfg.channels_sunny},
    "harry":  {"label": "🧙 HarryPotter",  "button_text": cfg.button_text, "url": cfg.signup_bot_url, "channels": cfg.channels_harry},
}


def is_admin(user_id: int) -> bool:
    return user_id in cfg.admin_ids


def signup_keyboard(button_text: str, button_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=button_text, url=button_url)]
    ])


def project_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=p["label"], callback_data=f"proj:{key}")]
        for key, p in PROJECTS.items()
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def channel_keyboard(channels) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=ch.label, callback_data=f"ch:{i}")]
        for i, ch in enumerate(channels)
    ]
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_preview")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def preview_keyboard(has_button: bool) -> InlineKeyboardMarkup:
    toggle_text = "🔘 Убрать кнопку" if has_button else "🔘 Добавить кнопку"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Опубликовать", callback_data="publish")],
        [
            InlineKeyboardButton(text="🖼 Изменить фото", callback_data="edit_photo"),
            InlineKeyboardButton(text="✏️ Изменить текст", callback_data="edit_text"),
        ],
        [InlineKeyboardButton(text=toggle_text, callback_data="toggle_button")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")],
    ])


def more_photo_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📸 Добавить ещё фото", callback_data="add_more_photo")],
        [InlineKeyboardButton(text="✏️ Перейти к тексту", callback_data="go_to_text")],
    ])


def button_choice_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да, добавить кнопку", callback_data="btn_yes")],
        [InlineKeyboardButton(text="❌ Нет, без кнопки", callback_data="btn_no")],
    ])


def _build_reply_markup(data: dict) -> InlineKeyboardMarkup | None:
    if not data.get("include_button", False):
        return None
    return signup_keyboard(data["btn_text"], data["btn_url"])


_CAPTION_LIMIT_SINGLE = 4096   # Telegram limit for single photo
_CAPTION_LIMIT_GROUP  = 1024   # Telegram limit for media group


async def send_preview(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    photos = data["photos"]
    text = data["post_text"]
    entities = data.get("post_entities")
    has_button = data.get("include_button", False)

    reply_markup = _build_reply_markup(data)

    await message.answer("👁 Предпросмотр поста:")

    if len(photos) == 1:
        await message.answer_photo(
            photo=photos[0],
            caption=text,
            caption_entities=entities,
            reply_markup=reply_markup,
        )
    else:
        if len(text) <= _CAPTION_LIMIT_GROUP:
            media = [
                InputMediaPhoto(media=photos[0], caption=text, caption_entities=entities),
                InputMediaPhoto(media=photos[1]),
            ]
            await message.answer_media_group(media=media)
        else:
            # Text > 1024: attach to first photo as single, send second separately
            await message.answer_photo(
                photo=photos[0],
                caption=text,
                caption_entities=entities,
                reply_markup=reply_markup,
            )
            await message.answer_photo(photo=photos[1])
            reply_markup = None  # already attached above

        if has_button and reply_markup is not None:
            await message.answer("Кнопка будет добавлена к посту при публикации.")

    btn_status = "с кнопкой записи" if has_button else "без кнопки записи"
    await message.answer(f"Пост {btn_status}. Что делаем?", reply_markup=preview_keyboard(has_button))
    await state.set_state(PostForm.preview)


async def publish_post(channel_id: str, data: dict) -> None:
    photos = data["photos"]
    text = data["post_text"]
    entities = data.get("post_entities")
    has_button = data.get("include_button", False)

    reply_markup = _build_reply_markup(data)

    if len(photos) == 1:
        await bot.send_photo(
            chat_id=channel_id,
            photo=photos[0],
            caption=text,
            caption_entities=entities,
            reply_markup=reply_markup,
        )
    else:
        if len(text) <= _CAPTION_LIMIT_GROUP:
            media = [
                InputMediaPhoto(media=photos[0], caption=text, caption_entities=entities),
                InputMediaPhoto(media=photos[1]),
            ]
            await bot.send_media_group(chat_id=channel_id, media=media)
            if has_button:
                await bot.send_message(chat_id=channel_id, text="\u200b", reply_markup=reply_markup)
        else:
            # Text > 1024: attach to first photo as single, send second separately
            await bot.send_photo(
                chat_id=channel_id,
                photo=photos[0],
                caption=text,
                caption_entities=entities,
                reply_markup=reply_markup,
            )
            await bot.send_photo(chat_id=channel_id, photo=photos[1])


# ── /start ──────────────────────────────────────────────

@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    if not is_admin(message.from_user.id):
        return
    await message.answer(
        "Привет! Я бот для публикации постов в канал.\n"
        "Используй /newpost чтобы создать новый пост."
    )


# ── /newpost ────────────────────────────────────────────

@router.message(Command("newpost"))
async def cmd_newpost(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    await state.clear()
    await message.answer("Выбери проект:", reply_markup=project_keyboard())
    await state.set_state(PostForm.choosing_project)


@router.callback_query(PostForm.choosing_project, F.data.startswith("proj:"))
async def on_project_chosen(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        return
    key = callback.data.split(":", 1)[1]
    proj = PROJECTS[key]
    await state.update_data(
        project=key,
        btn_text=proj["button_text"],
        btn_url=proj["url"],
    )
    await callback.message.edit_text(f"Проект: <b>{proj['label']}</b>\n\n📸 Отправь фото для поста (можно 1 или 2):")
    await state.set_state(PostForm.waiting_photo)
    await callback.answer()


# ── /cancel (в любом состоянии) ─────────────────────────

@router.message(Command("cancel"), StateFilter("*"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    await state.clear()
    await message.answer("Отменено. /newpost — начать заново.")


# ── Шаг 1: получаем первое фото ────────────────────────

@router.message(PostForm.waiting_photo, F.photo)
async def on_photo(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    photo_id = message.photo[-1].file_id
    await state.update_data(photos=[photo_id])
    await message.answer(
        "✅ Фото получено (1 из 2).",
        reply_markup=more_photo_keyboard(),
    )
    await state.set_state(PostForm.waiting_more_photo)


@router.message(PostForm.waiting_photo)
async def on_photo_invalid(message: Message) -> None:
    if not is_admin(message.from_user.id):
        return
    await message.answer("Нужно именно фото. Отправь изображение:")


# ── Шаг 1.5: второе фото или переход к тексту ──────────

@router.callback_query(PostForm.waiting_more_photo, F.data == "add_more_photo")
async def on_add_more_photo(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        return
    await callback.message.answer("📸 Отправь второе фото:")
    await callback.answer()


@router.message(PostForm.waiting_more_photo, F.photo)
async def on_second_photo(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    photos = data["photos"]
    photos.append(message.photo[-1].file_id)
    await state.update_data(photos=photos)
    await message.answer(
        "✅ Фото получено (2 из 2).\n\n"
        "✏️ Теперь отправь текст поста.\n"
        "Можно использовать форматирование: жирный, курсив, подчёркнутый, зачёркнутый, ссылки, эмодзи."
    )
    await state.set_state(PostForm.waiting_text)


@router.callback_query(PostForm.waiting_more_photo, F.data == "go_to_text")
async def on_go_to_text(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        return
    await callback.message.answer(
        "✏️ Отправь текст поста.\n"
        "Можно использовать форматирование: жирный, курсив, подчёркнутый, зачёркнутый, ссылки, эмодзи."
    )
    await state.set_state(PostForm.waiting_text)
    await callback.answer()


# ── Шаг 2: получаем текст ──────────────────────────────

@router.message(PostForm.waiting_text, F.text)
async def on_text(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    btn_text = data.get("btn_text", cfg.button_text)
    await state.update_data(post_text=message.text, post_entities=message.entities)
    await message.answer(
        f"Добавить кнопку «{btn_text}» к посту?",
        reply_markup=button_choice_keyboard(),
    )
    await state.set_state(PostForm.waiting_button_choice)


@router.message(PostForm.waiting_text)
async def on_text_invalid(message: Message) -> None:
    if not is_admin(message.from_user.id):
        return
    await message.answer("Нужен текст. Отправь текстовое сообщение:")


# ── Шаг 3: выбор кнопки ────────────────────────────────

@router.callback_query(PostForm.waiting_button_choice, F.data == "btn_yes")
async def on_button_yes(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        return
    data = await state.get_data()
    await state.update_data(include_button=True)

    if data.get("btn_url") is None:
        await callback.message.edit_text("🔗 Отправь ссылку для кнопки:")
        await state.set_state(PostForm.waiting_button_url)
    else:
        await send_preview(callback.message, state)
    await callback.answer()


@router.message(PostForm.waiting_button_url, F.text)
async def on_button_url(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    url = message.text.strip()
    if not url.startswith("http://") and not url.startswith("https://"):
        await message.answer("Ссылка должна начинаться с http:// или https://. Попробуй ещё раз:")
        return
    await state.update_data(btn_url=url)
    await send_preview(message, state)


@router.message(PostForm.waiting_button_url)
async def on_button_url_invalid(message: Message) -> None:
    if not is_admin(message.from_user.id):
        return
    await message.answer("Нужна ссылка. Отправь URL:")


@router.callback_query(PostForm.waiting_button_choice, F.data == "btn_no")
async def on_button_no(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        return
    await state.update_data(include_button=False)
    await send_preview(callback.message, state)
    await callback.answer()


# ── Предпросмотр: кнопки ───────────────────────────────

@router.callback_query(PostForm.preview, F.data == "publish")
async def on_publish(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        return
    data = await state.get_data()
    proj = PROJECTS.get(data.get("project", "cheese"))
    channels = proj["channels"]
    if len(channels) == 1:
        try:
            await publish_post(channels[0].id, data)
            await callback.message.answer(f"✅ Пост опубликован в {channels[0].label}!")
        except Exception as e:
            log.exception("Failed to publish post to %s", channels[0].id)
            await callback.message.answer(f"❌ Ошибка публикации: {e}")
        finally:
            await state.clear()
            await callback.answer()
        return
    await callback.message.answer("📢 Выбери канал для публикации:", reply_markup=channel_keyboard(channels))
    await state.set_state(PostForm.choosing_channel)
    await callback.answer()


@router.callback_query(PostForm.choosing_channel, F.data.startswith("ch:"))
async def on_channel_chosen(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        return
    idx = int(callback.data.split(":")[1])
    data = await state.get_data()
    proj = PROJECTS.get(data.get("project", "cheese"))
    channel = proj["channels"][idx]

    try:
        await publish_post(channel.id, data)
        await callback.message.answer(f"✅ Пост опубликован в {channel.label}!")
    except Exception as e:
        log.exception("Failed to publish post to %s", channel.id)
        await callback.message.answer(f"❌ Ошибка публикации: {e}")
    finally:
        await state.clear()
        await callback.answer()


@router.callback_query(F.data == "back_to_preview")
async def on_back_to_preview(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        return
    data = await state.get_data()
    has_button = data.get("include_button", False)
    btn_status = "с кнопкой записи" if has_button else "без кнопки записи"
    await callback.message.answer(f"Пост {btn_status}. Что делаем?", reply_markup=preview_keyboard(has_button))
    await state.set_state(PostForm.preview)
    await callback.answer()


@router.callback_query(PostForm.preview, F.data == "toggle_button")
async def on_toggle_button(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        return
    data = await state.get_data()
    new_value = not data.get("include_button", False)
    await state.update_data(include_button=new_value)

    if new_value and data.get("btn_url") is None:
        await callback.message.answer("🔗 Отправь ссылку для кнопки:")
        await state.set_state(PostForm.waiting_button_url)
    else:
        await send_preview(callback.message, state)
    await callback.answer()


@router.callback_query(PostForm.preview, F.data == "edit_photo")
async def on_edit_photo(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        return
    await callback.message.answer("📸 Отправь новое фото (начнём заново, 1 или 2):")
    await state.set_state(PostForm.edit_photo)
    await callback.answer()


@router.callback_query(PostForm.preview, F.data == "edit_text")
async def on_edit_text(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        return
    await callback.message.answer(
        "✏️ Как изменить текст?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔍 Найти и заменить", callback_data="edit_find_replace")],
            [InlineKeyboardButton(text="📝 Заменить полностью", callback_data="edit_full_replace")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_preview")],
        ]),
    )
    await callback.answer()


@router.callback_query(F.data == "edit_full_replace")
async def on_edit_full_replace(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        return
    await callback.message.edit_text("✏️ Отправь новый текст:")
    await state.set_state(PostForm.edit_text)
    await callback.answer()


@router.callback_query(F.data == "edit_find_replace")
async def on_edit_find_replace(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        return
    await callback.message.edit_text("🔍 Отправь текст, который нужно найти:")
    await state.set_state(PostForm.edit_find)
    await callback.answer()


@router.callback_query(PostForm.preview, F.data == "cancel")
async def on_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        return
    await state.clear()
    await callback.message.answer("Отменено. /newpost — начать заново.")
    await callback.answer()


# ── Редактирование фото ────────────────────────────────

@router.message(PostForm.edit_photo, F.photo)
async def on_edit_first_photo(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    photo_id = message.photo[-1].file_id
    await state.update_data(photos=[photo_id])
    await message.answer(
        "✅ Фото получено (1 из 2).",
        reply_markup=more_photo_keyboard(),
    )
    await state.set_state(PostForm.edit_more_photo)


@router.message(PostForm.edit_photo)
async def on_edit_photo_invalid(message: Message) -> None:
    if not is_admin(message.from_user.id):
        return
    await message.answer("Нужно фото. Отправь изображение:")


@router.callback_query(PostForm.edit_more_photo, F.data == "add_more_photo")
async def on_edit_add_more_photo(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        return
    await callback.message.answer("📸 Отправь второе фото:")
    await callback.answer()


@router.message(PostForm.edit_more_photo, F.photo)
async def on_edit_second_photo(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    photos = data["photos"]
    photos.append(message.photo[-1].file_id)
    await state.update_data(photos=photos)
    await send_preview(message, state)


@router.callback_query(PostForm.edit_more_photo, F.data == "go_to_text")
async def on_edit_go_to_preview(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        return
    await send_preview(callback.message, state)
    await callback.answer()


# ── Редактирование текста ───────────────────────────────

@router.message(PostForm.edit_text, F.text)
async def on_new_text(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    await state.update_data(post_text=message.text, post_entities=message.entities)
    await send_preview(message, state)


@router.message(PostForm.edit_text)
async def on_new_text_invalid(message: Message) -> None:
    if not is_admin(message.from_user.id):
        return
    await message.answer("Нужен текст. Отправь текстовое сообщение:")


# ── Найти и заменить ───────────────────────────────────

@router.message(PostForm.edit_find, F.text)
async def on_find_text(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    current = data.get("post_text", "")
    needle = message.text
    if needle not in current:
        await message.answer(f"❌ Текст «{needle[:50]}» не найден в посте.\n\n🔍 Попробуй другой фрагмент или /cancel:")
        return
    await state.update_data(find_needle=needle)
    await message.answer(f"✅ Найдено. Теперь отправь текст для замены:\n\n(заменяем «{needle[:80]}»)")
    await state.set_state(PostForm.edit_replace)


@router.message(PostForm.edit_find)
async def on_find_text_invalid(message: Message) -> None:
    if not is_admin(message.from_user.id):
        return
    await message.answer("Отправь текст для поиска. /cancel — отмена.")


@router.message(PostForm.edit_replace, F.text)
async def on_replace_text(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    needle = data["find_needle"]
    replacement = message.text
    current_text = data.get("post_text", "")
    current_entities = data.get("post_entities")

    needle_start = current_text.find(needle)
    if needle_start == -1:
        await message.answer("❌ Фрагмент больше не найден. Попробуй заново.")
        await state.set_state(PostForm.edit_find)
        return

    new_text = current_text[:needle_start] + replacement + current_text[needle_start + len(needle):]
    shift = len(replacement) - len(needle)

    new_entities = None
    if current_entities:
        new_entities = []
        for e in current_entities:
            eo = e.model_dump(exclude_none=True)
            offset = eo.get("offset", 0)
            length = eo.get("length", 0)
            end = offset + length

            if end <= needle_start:
                new_entities.append(e)
            elif offset >= needle_start + len(needle):
                eo["offset"] = offset + shift
                new_entities.append(MessageEntity.model_validate(eo))
            else:
                pass

    await state.update_data(post_text=new_text, post_entities=new_entities)
    await send_preview(message, state)


@router.message(PostForm.edit_replace)
async def on_replace_text_invalid(message: Message) -> None:
    if not is_admin(message.from_user.id):
        return
    await message.answer("Отправь текст для замены. /cancel — отмена.")


# ── Entry point ─────────────────────────────────────────

async def main() -> None:
    dp = Dispatcher()
    dp.include_router(router)

    ch_names = ", ".join(ch.label for ch in cfg.channels)
    log.info("Bot starting — admins: %s, channels: [%s]", cfg.admin_ids, ch_names)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
