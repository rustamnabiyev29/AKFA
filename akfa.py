import os
import hmac
import json
import hashlib
import asyncio
import logging
import sqlite3
from urllib.parse import parse_qsl

from aiohttp import web

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton

# ================== НАСТРОЙКИ (через ENV) ==================
# ОБЯЗАТЕЛЬНО замени токен через BotFather и задай его через env BOT_TOKEN
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "8440837236"))
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://akfazakazbot.netlify.app/")
DB_PATH = os.getenv("DB_PATH", "orders.db")
PORT = int(os.getenv("PORT", "8080"))

if not BOT_TOKEN:
    raise RuntimeError("Set BOT_TOKEN env var")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ================== DB ==================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    username TEXT,
                    name TEXT,
                    phone TEXT,
                    address TEXT,
                    windows TEXT,
                    window_square REAL,
                    doors TEXT,
                    door_square REAL,
                    profile TEXT,
                    color TEXT,
                    glass TEXT,
                    net TEXT,
                    sill TEXT,
                    total REAL,
                    deposit REAL,
                    rest REAL,
                    date TEXT,
                    raw_text TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                 )''')
    conn.commit()
    conn.close()

init_db()

def safe_float(x):
    try:
        return float(str(x).replace(",", "."))
    except:
        return None

def db_insert_order(user_id, username, name, phone, address,
                    windows, window_square, doors, door_square,
                    profile, color, glass, net, sill, total, deposit, rest, date, raw_text):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT INTO orders (
                    user_id, username, name, phone, address,
                    windows, window_square, doors, door_square,
                    profile, color, glass, net, sill,
                    total, deposit, rest, date, raw_text
                 ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
              (
                  user_id, username, name, phone, address,
                  windows, window_square, doors, door_square,
                  profile, color, glass, net, sill,
                  total, deposit, rest, date, raw_text
              ))
    conn.commit()
    conn.close()

def db_get_orders(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("""
        SELECT
          name, phone, address,
          windows, window_square, doors, door_square,
          profile, color, glass, net, sill,
          total, deposit, rest, date,
          timestamp
        FROM orders
        WHERE user_id=?
        ORDER BY datetime(timestamp) DESC, id DESC
    """, (user_id,))
    rows = c.fetchall()
    conn.close()

    # Формат под твой фронт
    out = []
    for r in rows:
        out.append({
            "name": r["name"] or "",
            "phone": r["phone"] or "",
            "address": r["address"] or "",
            "windows": r["windows"] or "",
            "windowSquare": str(r["window_square"] or ""),
            "doors": r["doors"] or "",
            "doorSquare": str(r["door_square"] or ""),
            "profile": r["profile"] or "",
            "color": r["color"] or "",
            "glass": r["glass"] or "",
            "net": r["net"] or "Setkasiz",
            "sill": r["sill"] or "",
            "total": str(r["total"] or ""),
            "deposit": str(r["deposit"] or ""),
            "rest": str(r["rest"] or ""),
            "date": r["date"] or ""
        })
    return out

# ================== Telegram initData verify (для API) ==================
def verify_init_data(init_data: str) -> dict | None:
    try:
        data = dict(parse_qsl(init_data, strict_parsing=True))
        received_hash = data.pop("hash", None)
        if not received_hash:
            return None

        check_arr = [f"{k}={data[k]}" for k in sorted(data.keys())]
        check_string = "\n".join(check_arr).encode("utf-8")

        secret = hmac.new(b"WebAppData", BOT_TOKEN.encode("utf-8"), hashlib.sha256).digest()
        calculated_hash = hmac.new(secret, check_string, hashlib.sha256).hexdigest()

        if not hmac.compare_digest(calculated_hash, received_hash):
            return None

        if "user" in data:
            data["user"] = json.loads(data["user"])
        return data
    except:
        return None

def api_auth_user(request: web.Request):
    init_data = request.headers.get("X-TG-INITDATA", "")
    verified = verify_init_data(init_data)
    if not verified:
        return None
    user = verified.get("user") or {}
    uid = user.get("id")
    if not uid:
        return None
    return int(uid)

# ================== API ==================
async def api_orders(request: web.Request):
    uid = api_auth_user(request)
    if not uid:
        return web.json_response({"error": "unauthorized"}, status=401)
    return web.json_response(db_get_orders(uid))

async def api_health(request: web.Request):
    return web.json_response({"ok": True})

async def run_api():
    app = web.Application()
    app.router.add_get("/api/health", api_health)
    app.router.add_get("/api/orders", api_orders)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=PORT)
    await site.start()
    logging.info("API started on port %s", PORT)

# ================== BOT ==================
@dp.message(Command("start"))
async def start(message: Message):
    keyboard = types.ReplyKeyboardMarkup(
        resize_keyboard=True,
        keyboard=[[
            types.KeyboardButton(
                text="AKFA",
                web_app=WebAppInfo(url=WEBAPP_URL)
            )
        ]]
    )
    await message.answer("Salom! AKFA buyurtmalar uchun tugmani bosing 👇", reply_markup=keyboard)

@dp.message(Command("myorders"))
async def myorders(message: Message):
    orders = db_get_orders(message.from_user.id)[:10]
    if not orders:
        return await message.answer("Sizda buyurtma yo‘q.")
    text = "🧾 Sizning oxirgi 10 buyurtmangiz:\n\n"
    for o in orders:
        text += f"👤 {o['name']} | 📞 {o['phone']}\n📍 {o['address']}\n🧱 {o['profile']}\n💰 {o['total']} | 📅 {o['date']}\n---\n"
    await message.answer(text)

@dp.message(Command("admin_orders"))
async def admin_orders(message: Message):
    if message.from_user.id != ADMIN_ID:
        return await message.answer("Ruxsat yo‘q.")
    # последние 10 по всем
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("""
        SELECT username, name, phone, address, profile, total, date, timestamp
        FROM orders
        ORDER BY datetime(timestamp) DESC, id DESC
        LIMIT 10
    """)
    rows = c.fetchall()
    conn.close()
    if not rows:
        return await message.answer("Buyurtmalar yo‘q.")
    text = "🧾 Oxirgi 10 buyurtma (hamma):\n\n"
    for r in rows:
        text += f"👤 {r['name']} (@{r['username']})\n📞 {r['phone']}\n📍 {r['address']}\n🧱 {r['profile']}\n💰 {r['total']} | 📅 {r['date']}\n⏱ {r['timestamp']}\n---\n"
    await message.answer(text)

@dp.message(F.web_app_data)
async def web_app_handler(message: Message):
    try:
        data = message.web_app_data.data

        lines = [line.strip() for line in data.split('\n') if line.strip()]
        if lines and lines[0].startswith('🆕'):
            lines = lines[1:]
        data_lines = [line for line in lines if ':' in line]

        name = data_lines[0].split(':', 1)[1].strip() if len(data_lines) > 0 else ''
        phone = data_lines[1].split(':', 1)[1].strip() if len(data_lines) > 1 else ''
        address = data_lines[2].split(':', 1)[1].strip() if len(data_lines) > 2 else ''

        order_dict = {}
        for line in data_lines[3:]:
            if ':' in line:
                key, value = line.split(':', 1)
                order_dict[key.strip()] = value.strip()

        def get_count(text, default=''):
            if not text: return default
            return text.split('(')[0].strip() if '(' in text else text.strip()

        def get_square(text, default=None):
            if not text or '(' not in text:
                return default
            try:
                return safe_float(text.split('(')[1].replace(' м²)', '').strip())
            except:
                return default

        windows_text = order_dict.get('🪟 Oynalar', '')
        doors_text = order_dict.get('🚪 Eshiklar', '')

        db_insert_order(
            user_id=message.from_user.id,
            username=message.from_user.username or "—",
            name=name,
            phone=phone,
            address=address,
            windows=get_count(windows_text),
            window_square=get_square(windows_text),
            doors=get_count(doors_text),
            door_square=get_square(doors_text),
            profile=order_dict.get('🧱 Profil', ''),
            color=order_dict.get('🎨 Rang', ''),
            glass=order_dict.get('🪟 Shisha paket', ''),
            net=order_dict.get('🕸  Setka', order_dict.get('🕸 Setka', 'Setkasiz')),
            sill=order_dict.get('🪟 Podokolnik', ''),
            total=safe_float(order_dict.get('💰 Umumiy summa', '')),
            deposit=safe_float(order_dict.get("💵 Zalo'g", order_dict.get("💵 Zalo\'g", ''))),
            rest=safe_float(order_dict.get('💸 Qoldi', '')),
            date=order_dict.get('📅 O‘rnatiladigan sana', ''),
            raw_text=data
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➡️ Forward", callback_data=f"forward_{message.message_id}")]
        ])

        await bot.send_message(ADMIN_ID, data, reply_markup=keyboard)

    except Exception as e:
        logging.exception("web_app_handler error")
        try:
            await bot.send_message(ADMIN_ID, f"🚨 Bot xatosi:\n{e}")
        except:
            pass

@dp.callback_query(F.data.startswith("forward_"))
async def forward_order(callback: types.CallbackQuery):
    try:
        original_message_id = int(callback.data.split("_")[1])
        await bot.forward_message(chat_id=ADMIN_ID, from_chat_id=ADMIN_ID, message_id=original_message_id)
        await callback.answer("Forward qilindi ✅")
    except Exception:
        await callback.answer("Forward bo‘lmadi", show_alert=True)

async def main():
    logging.basicConfig(level=logging.INFO)
    await run_api()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
