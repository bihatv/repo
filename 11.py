from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters, ConversationHandler
)
import logging
import datetime
import asyncio
import requests
from flask import Flask
from threading import Thread
import random

# --- Logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Config ---
TOKEN = "8090462786:AAFoA1jDYP3lxoQ9P7UIBYEY34s6KORJ0W0"
GROUP_IDS = [-1002587301398, -1002344399471]
GROUP_JOIN_LINK = "https://t.me/hupcodenhacai1"
ADMIN_IDS = [7014048216]
REF_BONUS_MIN = 1000
REF_BONUS_MAX = 1500
MIN_WITHDRAW = 10000

# --- States ---
WITHDRAW = range(1)

# --- Data ---
USER_DATA = {}
TOTAL_WITHDRAWN = 0

# --- Flask keep-alive ---
app_flask = Flask('')

@app_flask.route('/')
def home():
    return "Bot đang chạy!"

def run():
    app_flask.run(host='0.0.0.0', port=8080)

Thread(target=run).start()

# --- Auto Ping ---
async def auto_ping():
    while True:
        try:
            requests.get("https://repo-urw6.onrender.com")
        except:
            pass
        await asyncio.sleep(280)

# --- Check group membership ---
async def is_member(user_id: int, context: ContextTypes.DEFAULT_TYPE):
    try:
        for group_id in GROUP_IDS:
            member = await context.bot.get_chat_member(group_id, user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                return False
        return True
    except Exception as e:
        print(f"Lỗi kiểm tra nhóm: {e}")
        return False

# --- Start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id

    if USER_DATA.get(user_id, {}).get("banned", False):
        await update.message.reply_text("🚫 Bạn đã bị chặn khỏi hệ thống.")
        return

    ref = update.message.text.split(' ')[1] if len(update.message.text.split(' ')) > 1 else None

    if user_id not in USER_DATA:
        USER_DATA[user_id] = {
            'balance': 0,
            'ref': ref,
            'ref_count': 0,
            'last_checkin': None,
            'banned': False,
        }

        if ref and ref.isdigit():
            ref_id = int(ref)
            if ref_id != user_id and ref_id in USER_DATA:
                if not USER_DATA[ref_id].get("banned", False):
                    bonus = random.randint(REF_BONUS_MIN, REF_BONUS_MAX)
                    USER_DATA[ref_id]['balance'] += bonus
                    USER_DATA[ref_id]['ref_count'] += 1
                    try:
                        await context.bot.send_message(ref_id, f"🎉 Bạn vừa nhận được {bonus}điểm vì đã mời người dùng mới!")
                    except:
                        pass

    if not await is_member(user_id, context):
        join_buttons = [[InlineKeyboardButton("🔗 Tham gia ", url=GROUP_JOIN_LINK)]]
        await update.message.reply_text("🚫 Bạn cần tham gia tất cả nhóm để sử dụng bot!", reply_markup=InlineKeyboardMarkup(join_buttons))
        return

    await show_menu(update, context)

# --- Show Menu ---
async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("💳 Ví điểm", callback_data="balance"),
            InlineKeyboardButton("💸 Nhiệm vụ", callback_data="ref")
        ],
        [
            InlineKeyboardButton("💱 Rút code", callback_data="withdraw"),
            InlineKeyboardButton("✅ Điểm danh", callback_data="checkin")
        ],
        [
            InlineKeyboardButton("🔧 Quản trị viên", callback_data="admin")
        ]
    ]
    await update.message.reply_text("📋 Menu chính:️🎉️🎊 Mời bạn sẽ tích điểm từ 1000-1500🎊", reply_markup=InlineKeyboardMarkup(keyboard))

# --- Button Callback Handler ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "balance":
        balance = USER_DATA.get(user_id, {}).get("balance", 0)
        await query.edit_message_text(f"💳Số dư hiện tại của bạn: {balance}đ")
    elif query.data == "ref":
        ref_link = f"https://t.me/{context.bot.username}?start={user_id}"
        ref_count = USER_DATA.get(user_id, {}).get("ref_count", 0)
        await query.edit_message_text(f"👥 Link mời của bạn nằm ở đây :\n{ref_link}\nĐã mời 👉 : {ref_count} friend")
    elif query.data == "withdraw":
        await query.edit_message_text("💸 Nhập điểm rút để đổi code (vd: 10000):")
        return WITHDRAW
    elif query.data == "checkin":
        now = datetime.datetime.now().date()
        last_checkin = USER_DATA[user_id].get("last_checkin")
        if last_checkin == now:
            await query.edit_message_text("❌Ơ!Bạn đã điểm danh hôm nay rồi.")
        else:
            USER_DATA[user_id]["last_checkin"] = now
            USER_DATA[user_id]["balance"] += 1000
            await query.edit_message_text("✅ Điểm danh thành công! Bạn nhận được 1.000.")
    elif query.data == "admin" and user_id in ADMIN_IDS:
        admin_keyboard = [
            [InlineKeyboardButton("📊 Thống kê", callback_data="stats")],
            [InlineKeyboardButton("🚫 Chặn người dùng", callback_data="ban")],
            [InlineKeyboardButton("✅ Bỏ chặn người dùng", callback_data="unban")],
        ]
        await query.edit_message_text("🔧 Menu quản trị:", reply_markup=InlineKeyboardMarkup(admin_keyboard))
    elif query.data == "stats" and user_id in ADMIN_IDS:
        total_users = len(USER_DATA)
        await query.edit_message_text(f"📊 Tổng người dùng: {total_users}\n💸 Tổng đã rút: {TOTAL_WITHDRAWN}đ")

# --- Xử lý rút tiền ---
async def handle_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        amount = int(update.message.text)
        balance = USER_DATA.get(user_id, {}).get("balance", 0)

        if amount < MIN_WITHDRAW:
            await update.message.reply_text(f"⚠️ Số điểm rút tối thiểu là {MIN_WITHDRAW}đ.")
        elif amount > balance:
            await update.message.reply_text("❌ Bạn không đủ điểm để rút.")
        else:
            USER_DATA[user_id]["balance"] -= amount
            global TOTAL_WITHDRAWN
            TOTAL_WITHDRAWN += amount
            await update.message.reply_text(f"✅ Yêu cầu rút {amount}đ đã được ghi nhận. Admin sẽ xử lý sớm nhất.")
            for admin_id in ADMIN_IDS:
                try:
                    await context.bot.send_message(admin_id, f"📥 Người dùng {user_id} yêu cầu rút {amount}đ.")
                except:
                    pass
    except:
        await update.message.reply_text("❌ Vui lòng nhập số hợp lệ.")
    return ConversationHandler.END

# --- Hủy bỏ rút ---
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Đã huỷ thao tác.")
    return ConversationHandler.END

# --- Main ---
if __name__ == '__main__':
    application = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern="^withdraw$")],
        states={
            WITHDRAW: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_withdraw)]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.ad
