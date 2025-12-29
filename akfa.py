import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    WebAppInfo
)

TOKEN = "7551652669:AAGQQIlNzGWWQqBCLo31Xy5Dk21i2pXL_Ow"
WEBAPP_URL = "https://akfazakazbot.netlify.app/"

# Список ID админов
ADMIN_IDS = [570269160, 8440837236]  # <-- сюда добавь нужные ID

bot = Bot(token=TOKEN)
dp = Dispatcher()

market_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(
                text="🛒 Маркет",
                web_app=WebAppInfo(url=WEBAPP_URL)
            )
        ]
    ],
    resize_keyboard=True
)

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

@dp.message(CommandStart())
async def start_handler(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к этому боту.")
        return

    await message.answer(
        "Добро пожаловать 👋\nНажмите «Маркет», чтобы открыть магазин.",
        reply_markup=market_keyboard
    )

@dp.message(lambda m: m.text == "🛒 Маркет")
async def market_handler(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к этому боту.")
        return

    await message.answer(
        "Открываю маркет 👇",
        reply_markup=market_keyboard
    )

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
