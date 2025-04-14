from flask import Flask, request
import telebot
import os
import json
import datetime
import random
import string
from telebot import types
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO

API_TOKEN = 'YOUR_BOT_TOKEN'  # <-- Thay bằng token bot thật của bạn
WEBHOOK_URL = 'https://your-render-service-name.onrender.com/'  # <-- Thay bằng URL Render của bạn

bot = telebot.TeleBot(API_TOKEN)
app = Flask(__name__)

# Khởi tạo biến
NHOM_CANTHAMGIA = ['@hupcodenhacai1','@cheoreflink']
user_data_file = 'userdata.json'
invited_users_file = 'invitedusers.json'
captcha_solutions = {}
min_withdraw_amount = 20000
admins = [7014048216]

# Helper
user_data = {}
invited_users = {}

def load_data(file_path):
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_data(file_path, data):
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=4)

def initialize_user(user_id):
    if str(user_id) not in user_data:
        user_data[str(user_id)] = {'balance': 1000, 'registration_date': datetime.datetime.now().timestamp()}

def update_user_balance(user_id, amount):
    if str(user_id) in user_data:
        user_data[str(user_id)]['balance'] += amount
    else:
        user_data[str(user_id)] = {'balance': amount}
    save_data(user_data_file, user_data)

def get_balance(user_id):
    return user_data.get(str(user_id), {}).get('balance', 0)

def check_subscription(user_id):
    for channel in NHOM_CANTHAMGIA:
        try:
            member = bot.get_chat_member(channel, user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                return False
        except:
            return False
    return True

def generate_captcha():
    captcha_text = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    img = Image.new('RGB', (150, 60), color=(255, 255, 255))
    d = ImageDraw.Draw(img)
    font = ImageFont.load_default()
    d.text((10, 10), captcha_text, font=font, fill=(0, 0, 0))
    captcha_image = BytesIO()
    img.save(captcha_image, format='PNG')
    captcha_image.seek(0)
    return captcha_image, captcha_text

# Bot logic
@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = message.from_user.id
    referrer_id = None
    if len(message.text.split()) > 1:
        referrer_id = message.text.split()[1]
    if referrer_id:
        if str(user_id) not in user_data:
            invited_users[str(user_id)] = referrer_id
            save_data(invited_users_file, invited_users)
            initialize_user(user_id)
            save_data(user_data_file, user_data)

    markup = types.InlineKeyboardMarkup()
    for channel in NHOM_CANTHAMGIA:
        markup.add(types.InlineKeyboardButton('Tham Gia Nhóm', url=f'https://t.me/{channel[1:]}'))
    captcha_image, captcha_text = generate_captcha()
    captcha_solutions[user_id] = captcha_text
    markup.add(types.InlineKeyboardButton('Xác minh CAPTCHA', callback_data='check_captcha'))
    bot.send_photo(message.chat.id, captcha_image, caption="Vui lòng nhập CAPTCHA!", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == 'check_captcha')
def ask_for_captcha(call):
    user_id = call.from_user.id
    if user_id in captcha_solutions:
        bot.send_message(call.message.chat.id, "Nhập CAPTCHA: ")
    else:
        bot.send_message(call.message.chat.id, "Bạn đã xong CAPTCHA!")

@bot.message_handler(func=lambda message: message.from_user.id in captcha_solutions)
def handle_captcha_input(message):
    user_id = message.from_user.id
    if message.text.strip().upper() == captcha_solutions[user_id]:
        del captcha_solutions[user_id]
        if check_subscription(user_id):
            initialize_user(user_id)
            save_data(user_data_file, user_data)
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add('👤 Tài Khoản', '👥 Mời Bạn Bè')
            bot.send_message(message.chat.id, f'Chào mừng! Số dư: {get_balance(user_id)}', reply_markup=markup)
        else:
            bot.send_message(message.chat.id, "Vui lòng tham gia nhóm trước khi tiếp tục.")
    else:
        bot.send_message(message.chat.id, "CAPTCHA sai. Thử lại!")

# Webhook route
@app.route('/', methods=['POST'])
def webhook():
    update = telebot.types.Update.de_json(request.stream.read().decode("utf-8"))
    bot.process_new_updates([update])
    return "OK", 200

@app.before_first_request
def set_webhook():
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)

if __name__ == '__main__':
    user_data = load_data(user_data_file)
    invited_users = load_data(invited_users_file)
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 10000)))
