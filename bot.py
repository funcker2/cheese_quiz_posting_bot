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
    Message,
)

from config import Config

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

cfg = Config.from_env()
bot = Bot(token=cfg.bot_token)
router = Router()


class PostForm(StatesGroup):
    waiting_photo = State()
    waiting_text = State()
    preview = State()
    choosing_channel = State()
    edit_photo = State()
    edit_text = State()


def is_admin(user_id: int) -> bool:
    return user_id in cfg.admin_ids


def signup_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=cfg.button_text, url=cfg.signup_bot_url)]
    ])


def channel_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=ch.label, callback_data=f"ch:{i}")]
        for i, ch in enumerate(cfg.channels)
    ]
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_preview")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def preview_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Опубликовать", callback_data="publish")],
        [
            InlineKeyboardButton(text="🖼 Изменить фото", callback_data="edit_photo"),
            InlineKeyboardButton(text="✏️ Изменить текст", callback_data="edit_text"),
        ],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")],
    ])


async def send_preview(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    photo_id = data["photo_id"]
    text = data["post_text"]
    entities = data.get("post_entities")

    await message.answer("👁 Предпросмотр поста:")
    await message.answer_photo(
        photo=photo_id,
        caption=text,
        caption_entities=entities,
        reply_markup=signup_keyboard(),
    )
    await message.answer("Что делаем?", reply_markup=preview_keyboard())
    await state.set_state(PostForm.preview)


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
    await message.answer("📸 Отправь фото для поста:")
    await state.set_state(PostForm.waiting_photo)


# ── /cancel (в любом состоянии) ─────────────────────────

@router.message(Command("cancel"), StateFilter("*"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    await state.clear()
    await message.answer("Отменено. /newpost — начать заново.")


# ── Шаг 1: получаем фото ───────────────────────────────

@router.message(PostForm.waiting_photo, F.photo)
async def on_photo(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    photo_id = message.photo[-1].file_id
    await state.update_data(photo_id=photo_id)
    await message.answer(
        "✏️ Теперь отправь текст поста.\n"
        "Можно использовать форматирование: жирный, курсив, подчёркнутый, зачёркнутый, ссылки, эмодзи."
    )
    await state.set_state(PostForm.waiting_text)


@router.message(PostForm.waiting_photo)
async def on_photo_invalid(message: Message) -> None:
    if not is_admin(message.from_user.id):
        return
    await message.answer("Нужно именно фото. Отправь изображение:")


# ── Шаг 2: получаем текст ──────────────────────────────

@router.message(PostForm.waiting_text, F.text)
async def on_text(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    await state.update_data(post_text=message.text, post_entities=message.entities)
    await send_preview(message, state)


@router.message(PostForm.waiting_text)
async def on_text_invalid(message: Message) -> None:
    if not is_admin(message.from_user.id):
        return
    await message.answer("Нужен текст. Отправь текстовое сообщение:")


# ── Предпросмотр: кнопки ───────────────────────────────

@router.callback_query(PostForm.preview, F.data == "publish")
async def on_publish(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        return
    await callback.message.answer("📢 Выбери канал для публикации:", reply_markup=channel_keyboard())
    await state.set_state(PostForm.choosing_channel)
    await callback.answer()


@router.callback_query(PostForm.choosing_channel, F.data.startswith("ch:"))
async def on_channel_chosen(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        return
    idx = int(callback.data.split(":")[1])
    channel = cfg.channels[idx]
    data = await state.get_data()

    try:
        await bot.send_photo(
            chat_id=channel.id,
            photo=data["photo_id"],
            caption=data["post_text"],
            caption_entities=data.get("post_entities"),
            reply_markup=signup_keyboard(),
        )
        await callback.message.answer(f"✅ Пост опубликован в {channel.label}!")
    except Exception as e:
        log.exception("Failed to publish post to %s", channel.id)
        await callback.message.answer(f"❌ Ошибка публикации: {e}")
    finally:
        await state.clear()
        await callback.answer()


@router.callback_query(PostForm.choosing_channel, F.data == "back_to_preview")
async def on_back_to_preview(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        return
    await callback.message.answer("Что делаем?", reply_markup=preview_keyboard())
    await state.set_state(PostForm.preview)
    await callback.answer()


@router.callback_query(PostForm.preview, F.data == "edit_photo")
async def on_edit_photo(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        return
    await callback.message.answer("📸 Отправь новое фото:")
    await state.set_state(PostForm.edit_photo)
    await callback.answer()


@router.callback_query(PostForm.preview, F.data == "edit_text")
async def on_edit_text(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        return
    await callback.message.answer("✏️ Отправь новый текст:")
    await state.set_state(PostForm.edit_text)
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
async def on_new_photo(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    photo_id = message.photo[-1].file_id
    await state.update_data(photo_id=photo_id)
    await send_preview(message, state)


@router.message(PostForm.edit_photo)
async def on_new_photo_invalid(message: Message) -> None:
    if not is_admin(message.from_user.id):
        return
    await message.answer("Нужно фото. Отправь изображение:")


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


# ── Entry point ─────────────────────────────────────────

async def main() -> None:
    dp = Dispatcher()
    dp.include_router(router)

    ch_names = ", ".join(ch.label for ch in cfg.channels)
    log.info("Bot starting — admins: %s, channels: [%s]", cfg.admin_ids, ch_names)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
