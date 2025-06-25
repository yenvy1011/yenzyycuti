
import json
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler

BOT_TOKEN = "7924929679:AAFiDU20UiEYdG1hbkMTEMYa6aHuZYGO5EI"
ADMIN_ID = "6900636273"
JSON_FILE = "./lich_su_b52.json"

user_keys = {"ABC123": {"user_id": None, "expires": "2025-12-31"}}
STATE_INPUT = range(1)
STATE_AWAIT_RESULT = range(2)
pending_users = {}

def start(update, context):
    update.message.reply_text("👋 Chào mừng đến bot tài xỉu MD5!
/key <mã> để nhập key
/menu để xem chức năng.")

def menu(update, context):
    update.message.reply_text("📋 MENU
/key <mã> – Nhập key
/sudung – Bắt đầu dự đoán tự động
/stop – Dừng")

def handle_key(update, context):
    if len(context.args) != 1:
        update.message.reply_text("❗ Dùng: /key <mã>")
        return
    key = context.args[0]
    user_id = str(update.message.from_user.id)
    if key in user_keys:
        user_keys[key]["user_id"] = user_id
        update.message.reply_text("🔓 Key hợp lệ! Gõ /sudung để bắt đầu.")
    else:
        update.message.reply_text("❌ Key không đúng.")

def sudung_start(update, context):
    user_id = str(update.message.from_user.id)
    if user_id != ADMIN_ID and not any(info["user_id"] == user_id for info in user_keys.values()):
        update.message.reply_text("🔑 Bạn chưa nhập key. Dùng /key <mã>")
        return ConversationHandler.END
    update.message.reply_text("📌 Nhập chuỗi cầu (15 ký tự T/X) và phiên.
VD:
TXTTTXXTXXTTXTTT 1442030")
    return STATE_INPUT[0]

def load_result_from_json(session):
    try:
        with open(JSON_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            for item in data:
                if item.get("session") == session:
                    return item.get("result", "").lower()
    except:
        return None
    return None

def save_result_to_json(session, result):
    try:
        with open(JSON_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except:
        data = []

    if any(d.get("session") == session for d in data):
        return

    new_record = {
        "session": session,
        "result": result.capitalize(),
        "dice": [],
        "md5": "",
        "timestamp": "",
        "used_pattern": ""
    }
    data.append(new_record)
    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def handle_input(update, context):
    text = update.message.text.strip().upper()
    parts = text.split()
    if len(parts) != 2:
        update.message.reply_text("⚠️ Sai định dạng. VD: TXTTTXXTXXTTXTTT 1442030")
        return STATE_INPUT[0]

    pattern_str, session_str = parts
    if len(pattern_str) != 15 or not all(c in ("T", "X") for c in pattern_str):
        update.message.reply_text("⚠️ Chuỗi phải gồm đúng 15 ký tự T hoặc X.")
        return STATE_INPUT[0]
    try:
        session = int(session_str)
    except:
        update.message.reply_text("⚠️ Phiên phải là số.")
        return STATE_INPUT[0]

    context.user_data["pattern"] = list(pattern_str)
    context.user_data["session"] = session
    return auto_predict(update, context)

def auto_predict(update, context):
    pattern = context.user_data["pattern"]
    session = context.user_data["session"]
    t_count = pattern.count("T")
    x_count = pattern.count("X")
    prediction = "Tài" if t_count >= x_count else "Xỉu"
    pattern_str = "".join(pattern)

    update.message.reply_text(
        f"📍 Chuỗi cầu hiện tại: {pattern_str}
"
        f"🎯 Dự đoán phiên {session}: {prediction}"
    )

    result = load_result_from_json(session)
    if result in ["tài", "xỉu"]:
        pattern.append("T" if result == "tài" else "X")
        context.user_data["pattern"] = pattern[-15:]
        context.user_data["session"] += 1
        return auto_predict(update, context)

    pending_users[update.message.chat_id] = session
    update.message.reply_text(f"❓ Không có kết quả phiên {session}. Nhập kết quả thật (Tài/Xỉu):")
    return STATE_AWAIT_RESULT[0]

def handle_manual_result(update, context):
    user_input = update.message.text.strip().lower()
    if user_input not in ["tài", "xỉu"]:
        update.message.reply_text("⚠️ Vui lòng nhập đúng: Tài hoặc Xỉu.")
        return STATE_AWAIT_RESULT[0]

    chat_id = update.message.chat_id
    if chat_id not in pending_users:
        update.message.reply_text("⚠️ Không có phiên nào đang chờ kết quả.")
        return STATE_INPUT[0]

    session = pending_users[chat_id]
    save_result_to_json(session, user_input)
    pattern = context.user_data["pattern"]
    pattern.append("T" if user_input == "tài" else "X")
    context.user_data["pattern"] = pattern[-15:]
    context.user_data["session"] += 1
    del pending_users[chat_id]
    return auto_predict(update, context)

def stop(update, context):
    update.message.reply_text("🛑 Bot đã dừng.")
    return ConversationHandler.END

def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("menu", menu))
    dp.add_handler(CommandHandler("key", handle_key))
    dp.add_handler(ConversationHandler(
        entry_points=[CommandHandler("sudung", sudung_start)],
        states={
            STATE_INPUT[0]: [MessageHandler(Filters.text & ~Filters.command, handle_input)],
            STATE_AWAIT_RESULT[0]: [MessageHandler(Filters.text & ~Filters.command, handle_manual_result)],
        },
        fallbacks=[CommandHandler("stop", stop)],
    ))
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
