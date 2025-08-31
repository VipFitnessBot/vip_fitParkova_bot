# bot.py - Telegram bot for VIP subscriptions with WayForPay integration
import os, time, json, threading, logging, requests
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import config, db_utils

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main_menu():
    kb = [
        [InlineKeyboardButton("📊 Мій рівень", callback_data="my_level")],
        [InlineKeyboardButton("ℹ️ Рівні та бонуси", callback_data="info")],
        [InlineKeyboardButton("💳 Сплатити підписку", callback_data="pay")]
    ]
    return InlineKeyboardMarkup(kb)

def generate_signature(payload: dict):
    import hashlib, base64
    concat = ";".join([str(payload.get(k,'')) for k in ("merchantAccount","merchantDomainName","orderReference","orderDate","amount","currency")])
    s = concat + config.MERCHANT_SECRET_KEY
    sha = hashlib.sha1(s.encode('utf-8')).digest()
    return base64.b64encode(sha).decode()

def create_invoice(user_id, price=None):
    price = price or int(config.SUBSCRIPTION_PRICE)
    order_ref = f"sub_{user_id}_{int(time.time())}"
    data = {
        "apiVersion": 1,
        "requestType": "CREATE_INVOICE",
        "merchantAccount": config.MERCHANT_ACCOUNT,
        "merchantDomainName": config.MERCHANT_DOMAIN_NAME,
        "orderReference": order_ref,
        "orderDate": int(time.time()),
        "amount": str(price),
        "currency": "UAH",
        "productName": ["VIP subscription"],
        "productPrice": [price],
        "productCount": [1],
        "language": "UA",
        "serviceUrl": config.CALLBACK_URL
    }
    data["merchantSignature"] = generate_signature(data)
    try:
        r = requests.post("https://api.wayforpay.com/api", json=data, timeout=30)
        logger.info("WFP create invoice response: %s", r.text)
        return r.json()
    except Exception as e:
        logger.exception("WFP create_invoice error")
        return {"error": str(e)}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    db_utils.ensure_user(uid)
    await update.message.reply_text("Вітаю у VIP! Обери дію:", reply_markup=main_menu())

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = str(q.from_user.id)
    if q.data == "my_level":
        u = db_utils.get_user(uid) or {}
        lvl = u.get("level",0)
        payments = u.get("payments",0)
        nd = u.get("next_due") or "—"
        text = f"Рівень: {lvl}\nОплат: {payments}\nНаступне списання: {nd}"
        await q.edit_message_text(text, reply_markup=main_menu())
    elif q.data == "info":
        text = ("1–2 оплати → 1 рівень (20%)\n"
                "3–4 → 2 рівень (25%)\n"
                "5–6 → 3 рівень (30%)\n"
                "7–8 → 4 рівень (35%)\n"
                "9–10 → 5 рівень (40%)\n"
                "11+ → 6 рівень (45%)\n\n"
                "Бонуси: 2 — кава; 3 — 2 кави; 4 — протеїн; 5 — кава+протеїн; 6 — 2 кави+протеїн")
        await q.edit_message_text(text, reply_markup=main_menu())
    elif q.data == "pay":
        resp = create_invoice(uid)
        if isinstance(resp, dict) and resp.get("invoiceUrl"):
            url = resp["invoiceUrl"]
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("Оплатити", url=url)]])
            await q.edit_message_text(f"Натисніть щоб оплатити: ", reply_markup=kb)
        else:
            await q.edit_message_text(f"❌ Помилка WayForPay:\n{json.dumps(resp, indent=2, ensure_ascii=False)}", reply_markup=main_menu())

def daily_job():
    from datetime import datetime
    users = dict(db_utils._load())
    for uid,u in users.items():
        nd = u.get("next_due")
        if not nd:
            continue
        try:
            ndt = datetime.fromisoformat(nd)
        except:
            continue
        if datetime.utcnow() >= ndt:
            rec = u.get("recToken")
            if not rec:
                continue
            order_ref = f"recur_{uid}_{int(time.time())}"
            payload = {
                "transactionType": "RECURRING",
                "merchantAccount": config.MERCHANT_ACCOUNT,
                "merchantDomainName": config.MERCHANT_DOMAIN_NAME,
                "orderReference": order_ref,
                "orderDate": int(time.time()),
                "amount": str(config.SUBSCRIPTION_PRICE),
                "currency": "UAH",
                "recToken": rec,
                "productName": ["VIP subscription (recurring)"],
                "productPrice": [config.SUBSCRIPTION_PRICE],
                "productCount": [1],
                "apiVersion": 1
            }
            payload["merchantSignature"] = generate_signature(payload)
            try:
                r = requests.post("https://api.wayforpay.com/api", json=payload, timeout=30)
                logger.info("WFP recurring response: %s", r.text)
                resp = r.json()
                status = resp.get("transactionStatus") or resp.get("orderStatus") or ""
                if str(status).lower() in ("approved","success","settled"):
                    db_utils.mark_paid(uid, months=1)
                else:
                    logger.info("Recurring not approved for %s: %s", uid, resp)
            except Exception:
                logger.exception("Recurring request failed for %s", uid)

def run_daily_scheduler():
    import time
    while True:
        try:
            daily_job()
        except Exception:
            logger.exception("daily_job failed")
        time.sleep(60*60)

def main():
    app = Application.builder().token(config.TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    t = threading.Thread(target=run_daily_scheduler, daemon=True)
    t.start()
    app.run_polling()

if __name__ == '__main__':
    main()
