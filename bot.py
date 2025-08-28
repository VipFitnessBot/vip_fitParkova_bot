import json
import time
import hmac
import hashlib
import base64
import requests
import schedule
import threading
from datetime import datetime, timedelta
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import config

USERS_FILE = "users.json"

# ---------- Робота з юзерами ----------
def load_users():
    try:
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)

def get_discount(level):
    return {0:0,1:20,2:20,3:25,4:25,5:30,6:30,7:35,8:35,9:40,10:40}.get(level,45)

def get_bonus(level):
    bonuses = {
        1: "❌ бонусів",
        2: "☕ кава",
        3: "☕☕ дві кави",
        4: "🥤 протеїновий коктейль",
        5: "☕ + 🥤",
        6: "☕☕ + 🥤"
    }
    return bonuses.get(level, "☕☕ + 🥤")

# ---------- WFP ----------
def generate_signature(data):
    keys = [
        "merchantAccount","merchantDomainName","orderReference","orderDate",
        "amount","currency"
    ]
    s = ";".join([str(data[k]) for k in keys])
    return base64.b64encode(hmac.new(config.MERCHANT_SECRET_KEY.encode(), s.encode(), hashlib.md5).digest()).decode()

def create_invoice(user_id, price=100):
    order_ref = f"sub_{user_id}_{int(time.time())}"
    data = {
        "merchantAccount": config.MERCHANT_ACCOUNT,
        "merchantDomainName": config.MERCHANT_DOMAIN_NAME,
        "orderReference": order_ref,
        "orderDate": int(time.time()),
        "amount": price,
        "currency": "UAH",
        "productName": ["Підписка"],
        "productPrice": [price],
        "productCount": [1],
        "language": "UA",
        "serviceUrl": "https://google.com",  # тут Railway callback
        "transactionType": "AUTO",  # recurrent
    }
    data["merchantSignature"] = generate_signature(data)
    r = requests.post("https://secure.wayforpay.com/pay", json=data)
    return r.json()

# ---------- Telegram ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    users = load_users()
    if user_id not in users:
        users[user_id] = {"level":0,"payments":0,"last_payment":None}
        save_users(users)

    keyboard = [
        [InlineKeyboardButton("ℹ️ Мій рівень", callback_data="my_level")],
        [InlineKeyboardButton("💳 Оплатити підписку", callback_data="pay")],
        [InlineKeyboardButton("📊 Інфо про рівні", callback_data="info")]
    ]
    await update.message.reply_text("Вітаю у клубі! 🎉", reply_markup=InlineKeyboardMarkup(keyboard))

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    users = load_users()

    if query.data == "my_level":
        level = users[user_id]["level"]
        payments = users[user_id]["payments"]
        text = f"📌 Рівень: {level}\nЗнижка: {get_discount(level)}%\nБонус: {get_bonus(level)}\nОплат: {payments}"
        await query.edit_message_text(text)

    elif query.data == "info":
        text = "📊 Система рівнів:\n1-2 оплати → 1 рівень (20%)\n3-4 → 2 рівень (25%)\n5-6 → 3 рівень (30%)\n7-8 → 4 рівень (35%)\n9-10 → 5 рівень (40%)\n11+ → 6 рівень (45%)"
        await query.edit_message_text(text)

    elif query.data == "pay":
        invoice = create_invoice(user_id)
        pay_url = invoice.get("invoiceUrl","https://google.com")
        await query.edit_message_text(f"💳 Сплатіть підписку: {pay_url}")

# ---------- Автоперевірка ----------
def check_subscriptions():
    users = load_users()
    for uid, data in users.items():
        if not data["last_payment"]:
            continue
        last = datetime.fromisoformat(data["last_payment"])
        if datetime.now() - last > timedelta(days=3):
            data["level"] = max(0, data["level"]-1)
    save_users(users)

def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(60)

schedule.every().day.at("10:00").do(check_subscriptions)

# ---------- MAIN ----------
def main():
    app = Application.builder().token(config.TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))

    t = threading.Thread(target=run_scheduler, daemon=True)
    t.start()
    app.run_polling()

if __name__ == "__main__":
    main()