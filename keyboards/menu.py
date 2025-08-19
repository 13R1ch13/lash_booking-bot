from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📝 Book")],
            [KeyboardButton(text="📅 My appointments")],
            [KeyboardButton(text="❌ Cancel appointment")]
        ],
        resize_keyboard=True
    )
