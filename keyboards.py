from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
)


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔍 جستجو با آیدی"),
             KeyboardButton(text="📱 جستجو با شماره")],
            [KeyboardButton(text="👤 جستجو با یوزرنیم"),
             KeyboardButton(text="📝 جستجوی نام")],
            [KeyboardButton(text="📊 آمار"),
             KeyboardButton(text="📤 خروجی Excel")],
            [KeyboardButton(text="📜 لاگ‌ها")],
        ],
        resize_keyboard=True,
    )


def user_actions(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✏️ ویرایش",
                                 callback_data=f"edit:{user_id}"),
            InlineKeyboardButton(text="🗑 حذف",
                                 callback_data=f"del:{user_id}"),
        ],
    ])
