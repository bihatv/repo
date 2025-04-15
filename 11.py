import telebot
from telebot import types
import os
import json
import datetime
import random
import base64
from captcha.image import ImageCaptcha  # Thư viện tạo captcha
from io import BytesIO  # Thư viện hỗ trợ làm việc với dữ liệu nhị phân

# Bot information and required channels
# Bot information and required channels
API_TOKEN ='7707470835:AAF2TSWpsFvM0FLySx3XbO_-fRjjb_8utCQ'  # Updated token
bot = telebot.TeleBot(API_TOKEN)
NHOM_CANTHAMGIA = ['@hupcodenhacai1','@cheoreflink']
user_data, invited_users, captcha_codes = {}, {}, {}
min_withdraw_amount = 20000  # Minimum withdrawal amount
admins = [7014048216]  # Admin IDs
from PIL import Image, ImageDraw, ImageFont
import random
import string
from io import BytesIO

# Dictionary to store CAPTCHA solutions
captcha_solutions = {}

# Generate a simple CAPTCHA image
def generate_captcha():
    # Random 5-character string
    captcha_text = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    
    # Create a white image with PIL
    img = Image.new('RGB', (150, 60), color=(255, 255, 255))
    d = ImageDraw.Draw(img)

    # Use a basic font for the CAPTCHA (adjust the path to a .ttf font file if needed)
    font = ImageFont.load_default()

    # Draw the CAPTCHA text on the image
    d.text((10, 10), captcha_text, font=font, fill=(0, 0, 0))

    # Save image to a BytesIO object
    captcha_image = BytesIO()
    img.save(captcha_image, format='PNG')
    captcha_image.seek(0)

    return captcha_image, captcha_text

# When the user starts interacting with the bot
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
        markup.add(types.InlineKeyboardButton(f'👉 Tham Gia Nhóm 👈', url=f'https://t.me/{channel[1:]}'))
    
    # Generate a CAPTCHA image and solution
    captcha_image, captcha_text = generate_captcha()
    captcha_solutions[user_id] = captcha_text  # Store CAPTCHA solution for the user

    markup.add(types.InlineKeyboardButton('✔️ Xác minh CAPTCHA ✔️', callback_data='check_captcha'))

    caption = """
    <b>NHẬP CHỮ CÁI TRÊN ẢNH !</b>
    ❗ Trước tiên phải tham gia nhóm trước rồi giải CAPTCHA để tiếp tục.
    """  
    bot.send_photo(message.chat.id, 
                   captcha_image, 
                   caption=caption, 
                   reply_markup=markup, 
                   parse_mode='HTML')

# CAPTCHA verification process
@bot.callback_query_handler(func=lambda call: call.data == 'check_captcha')
def ask_for_captcha(call):
    user_id = call.from_user.id
    if user_id in captcha_solutions:
        bot.send_message(call.message.chat.id, "Vui lòng nhập mã CAPTCHA mà bạn thấy:")
    else:
        bot.send_message(call.message.chat.id, "Bạn đã vượt qua bước xác minh CAPTCHA!")

# Handle user's CAPTCHA input
@bot.message_handler(func=lambda message: message.from_user.id in captcha_solutions)
def handle_captcha_response(message):
    user_id = message.from_user.id
    user_input = message.text.strip()

    # Compare user input with stored CAPTCHA solution
    if user_input.upper() == captcha_solutions[user_id]:
        bot.send_message(message.chat.id, "✔️ Xác minh CAPTCHA thành công!")
        del captcha_solutions[user_id]  # Remove solved CAPTCHA

        # Now check if the user is subscribed to all required channels
        if check_subscription(user_id):
            referrer_id = invited_users.get(str(user_id))

            if str(user_id) not in user_data:
                initialize_user(user_id)
                save_data(user_data_file, user_data)

            markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
            markup.add(types.KeyboardButton('👤 Tài Khoản'), types.KeyboardButton('👥 Mời Bạn Bè'))
            markup.add(types.KeyboardButton('💵 Đổi Code'), types.KeyboardButton('📊 Thống Kê'))
            markup.add(types.KeyboardButton('🆘 Hỗ Trợ'))

            balance = get_balance(user_id)
            bot.send_message(message.chat.id, f"🫡 Chào Mừng Bạn Quay Trở Lại! Số Dư Của Bạn Là {balance} đồng. Tiếp Tục Mời Bạn Bè Kiếm Code Ngay Nào", reply_markup=markup)

            if referrer_id and referrer_id in user_data:
                update_user_balance(referrer_id, 4500)
                bot.send_message(referrer_id, f"Bạn đã nhận được 4500 đồng khi mời {message.from_user.username} tham gia.")
                invited_users.pop(str(user_id))
                save_data(invited_users_file, invited_users)
        else:
            bot.send_message(message.chat.id, "Vui lòng tham gia tất cả các kênh yêu cầu trước khi kiểm tra lại.")
    else:
        bot.send_message(message.chat.id, "❌ Sai CAPTCHA. Vui lòng thử lại.")

user_data_file = 'userdata.json'
invited_users_file = 'invitedusers.json'

# Check channel subscription
def check_subscription(user_id):
    for channel in NHOM_CANTHAMGIA:
        try:
            member = bot.get_chat_member(channel, user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                return False
        except Exception:
            return False
    return True

# Hàm tải dữ liệu
def load_data(file_path):
    try:
        with open(file_path, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

# Hàm lưu dữ liệu
def save_data(file_path, data):
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=4)

user_data = load_data(user_data_file)
invited_users = load_data(invited_users_file)

# Hàm lấy số dư của người dùng
def get_balance(user_id):
    return user_data.get(str(user_id), {}).get('balance', 0)

# Hàm khởi tạo người dùng
def initialize_user(user_id):
    if str(user_id) not in user_data:
        user_data[str(user_id)] = {'balance': 1000, 'registration_date': datetime.datetime.now().timestamp()}

# Hàm cập nhật số dư của người dùng
def update_user_balance(user_id, amount):
    if str(user_id) in user_data:
        user_data[str(user_id)]['balance'] += amount
    else:
        user_data[str(user_id)] = {'balance': amount}
    save_data(user_data_file, user_data)

@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = message.from_user.id
    referrer_id = None

    # Kiểm tra nếu có mã giới thiệu trong tin nhắn
    if len(message.text.split()) > 1:
        referrer_id = message.text.split()[1]

    # Lưu thông tin người mời và xử lý thưởng
    if referrer_id:
        if str(user_id) not in user_data:  # Chỉ xử lý nếu người dùng chưa có tài khoản
            invited_users[str(user_id)] = referrer_id
            save_data(invited_users_file, invited_users)
            
            # Khởi tạo tài khoản cho người mới nếu chưa tồn tại
            initialize_user(user_id)
            save_data(user_data_file, user_data)

            # Thưởng cho người mời
            if referrer_id in user_data:
                update_user_balance(referrer_id, 4500 )  # Thưởng cho người mời
                bot.send_message(referrer_id, f"🎉 Bạn đã nhận được 4500 đồng khi mời {message.from_user.username} tham gia.")

        # Xóa thông tin người mời sau khi thưởng
        if str(user_id) in invited_users:
            invited_users.pop(str(user_id))
            save_data(invited_users_file, invited_users)

    markup = types.InlineKeyboardMarkup()
    for channel in NHOM_CANTHAMGIA:
        markup.add(types.InlineKeyboardButton(f'👉 Tham Gia Nhóm 👈', url=f'https://t.me/{channel[1:]}'))
    markup.add(types.InlineKeyboardButton('✔️Kiểm Tra✔️', callback_data='check'))
    photo_url = "https://i.imgur.com/wmsTcUg.jpeg"
    caption = """


"""  
    bot.send_photo(message.chat.id, 
                   photo_url,
                   caption=caption,
                   reply_markup=markup,
                   parse_mode='HTML')

# Hàm xử lý khi người dùng kiểm tra kênh
@bot.callback_query_handler(func=lambda call: call.data == 'check')
def check_channels(call):
    user_id = call.from_user.id

    if check_subscription(user_id):
        referrer_id = invited_users.get(str(user_id))

        # Khởi tạo tài khoản cho người dùng nếu chưa tồn tại
        if str(user_id) not in user_data:
            initialize_user(user_id)
            save_data(user_data_file, user_data)

        markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        markup.add(types.KeyboardButton('👤 Tài Khoản'), types.KeyboardButton('👥 Mời Bạn Bè'))
        markup.add(types.KeyboardButton('💵 Đổi Code'), types.KeyboardButton('Link Game'))
        markup.add(types.KeyboardButton('📊 Thống Kê'))  # Thêm nút "Thống Kê"

        balance = get_balance(user_id)
        bot.send_message(call.message.chat.id, f"🫡 Chào Mừng Bạn Quay Trở Lại! Số Dư Của Bạn Là {balance} đồng. Tiếp Tục Mời Bạn Bè Kiếm Code Ngay Nào", reply_markup=markup)

        if referrer_id and referrer_id in user_data:
            update_user_balance(referrer_id, 4500)  # Thưởng cho người mời
            bot.send_message(referrer_id, f"Bạn đã nhận được 4500 đồng khi mời {call.from_user.username} tham gia.")
            invited_users.pop(str(user_id))
            save_data(invited_users_file, invited_users)
    else:
        bot.send_message(call.message.chat.id, "Vui lòng tham gia tất cả các kênh yêu cầu trước khi kiểm tra lại.")

@bot.message_handler(func=lambda message: message.text == "👥 Mời Bạn Bè")
def handle_invite_friends(message):
    user_id = message.from_user.id
    invite_link = f"https://t.me/{bot.get_me().username}?start={user_id}"

    photo_url = "https://images.app.goo.gl/exG6Xy6FhadwQP8K7"
    caption = """
<b>❗️ NHẬN GIFCODE RẤT ĐƠN GIẢN CHỈ CẦN VÀI THAO TÁC
✅ MỜI BẠN BÈ THAM GIA BOT NHẬN NGAY 4500đ 
✅ http://sum34.club/ LÀ TÊN MIỀN CHÍNH HÃNG DUY NHẤT!</b>

👤 Link Mời Bạn Bè ( Bấm vào coppy ) :<code> {invite_link}</code>
    """.format(invite_link=invite_link)

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Sao chép link", callback_data=f"copy_invite_link_{user_id}"))

    bot.send_photo(message.chat.id, 
                   photo_url,
                   caption=caption,
                   reply_markup=markup,
                   parse_mode='HTML')

@bot.message_handler(commands=['thongbao'])
def thongbao_text(message):
    if message.from_user.id in admins:
        try:
            parts = message.text.split(maxsplit=1)
            if len(parts) < 2:
                raise ValueError("Sai cú pháp. Sử dụng: /thongbao [Nội dung thông báo]")

            announcement = parts[1]

            for user_id in user_data.keys():
                try:
                    bot.send_message(user_id, f"<b>{announcement}</b>", parse_mode='HTML')
                except Exception as e:
                    print(f"Gửi thông báo cho user_id {user_id} không thành công: {str(e)}")

            bot.reply_to(message, "Đã gửi thông báo đến tất cả người dùng thành công!")

        except ValueError as e:
            bot.reply_to(message, str(e))

    else:
        bot.reply_to(message, "Bạn không có quyền sử dụng lệnh này.")

@bot.message_handler(commands=['addcoin'])
def handle_addcoin_command(message):
    user_id = message.from_user.id
    if user_id not in admins:
        bot.reply_to(message, "Bạn không có quyền thực hiện lệnh này.")
        return

    try:
        details = message.text.split()
        target_user_id = int(details[1])
        amount = int(details[2])

        update_user_balance(target_user_id, amount)
        bot.reply_to(message, f'Đã cộng {amount} coins cho user {target_user_id}. Số dư hiện tại: {get_balance(target_user_id)} coins')
    except (IndexError, ValueError):
        bot.reply_to(message, 'Vui lòng nhập theo cú pháp /addcoin [user_id] [số tiền]')

@bot.message_handler(commands=['truemoney'])
def handle_truemoney_command(message):
    user_id = message.from_user.id
    if user_id not in admins:
        bot.reply_to(message, "Bạn không có quyền thực hiện lệnh này.")
        return

    try:
        details = message.text.split()
        target_user_id = int(details[1])
        amount = int(details[2])

        balance = get_balance(target_user_id)
        if balance >= amount:
            update_user_balance(target_user_id, -amount)
            bot.reply_to(message, f'Đã trừ {amount} coins từ user {target_user_id}. Số dư hiện tại: {get_balance(target_user_id)} coins')
        else:
            bot.reply_to(message, 'Số dư không đủ để thực hiện giao dịch.')
    except (IndexError, ValueError):
        bot.reply_to(message, 'Vui lòng nhập theo cú pháp /truemoney [user_id] [số tiền]')

@bot.message_handler(func=lambda message: message.text == '👤 Tài Khoản')
def handle_account_command(message):
    user_id = message.from_user.id
    username = message.from_user.username
    full_name = f"{message.from_user.first_name} {message.from_user.last_name}"
    balance = get_balance(user_id)
    balance_formatted = "{:,} Đ".format(balance) 
    
    registration_date = datetime.datetime.fromtimestamp(user_data.get(str(user_id), {}).get('registration_date', datetime.datetime.now().timestamp())).strftime('%d-%m-%Y')  # Ngày đăng ký tài khoản
    last_active = datetime.datetime.now().strftime('%d-%m-%Y %H:%M:%S')  
    
    text = f"""
Họ và tên: {full_name}
Số Dư: {balance_formatted}
ID Của Bạn: {user_id}

"""
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

@bot.message_handler(func=lambda message: message.text == '💵 Đổi Code')
def handle_withdraw(message):
    user_id = message.from_user.id
    if str(user_id) in user_data and user_data[str(user_id)]['balance'] >= min_withdraw_amount:
        withdraw_instructions = """
✅ Số Tiền Rút Tối Thiểu 20K
👉 Làm Theo Các Lệnh Sau Đây Để Rút Tiền

▶/doicode [ ID TELE ] [ SỐ TIỀN ] 
VD : /doicode 7214228954 20000
        """
        bot.send_message(message.chat.id, withdraw_instructions)
    else:
        bot.send_message(message.chat.id, "⚠️ Bạn cần có số dư ít nhất 20.000 đồng để thực hiện lệnh rút tiền.")

# Tải danh sách mã đổi thưởng từ file
def load_redeemable_codes(filename):
    try:
        with open(filename, 'r') as file:
            codes = [line.strip() for line in file.readlines() if line.strip()]
        return codes
    except FileNotFoundError:
        return []

# Lưu danh sách mã đổi thưởng đã cập nhật lại vào file
def save_redeemable_codes(filename, codes):
    with open(filename, 'w') as file:
        file.write('\n'.join(codes))

# Đường dẫn đến file chứa mã đổi thưởng
redeemable_codes_file = 'redeemable_codes.txt'

# Hàm xử lý lệnh /doicode với chức năng duyệt tự động
@bot.message_handler(commands=['doicode'])
def handle_withdraw_request(message):
    user_id = message.from_user.id
    if str(user_id) in user_data:
        current_balance = user_data[str(user_id)]['balance']
        details = message.text.split()
        
        # Kiểm tra cú pháp lệnh
        if len(details) == 3:
            bank_name = details[1]
            try:
                amount = int(details[2])
            except ValueError:
                bot.send_message(message.chat.id, "🚫 Số tiền phải là một số nguyên hợp lệ.")
                return

            # Kiểm tra điều kiện số dư tối thiểu
            if amount >= min_withdraw_amount:
                if current_balance >= amount:
                    # Tải mã đổi thưởng có sẵn
                    redeemable_codes = load_redeemable_codes(redeemable_codes_file)
                    
                    if redeemable_codes:
                        # Trừ số dư
                        user_data[str(user_id)]['balance'] -= amount
                        save_data(user_data_file, user_data)

                        # Cấp mã cho người dùng và xóa khỏi danh sách
                        code = redeemable_codes.pop(0)
                        save_redeemable_codes(redeemable_codes_file, redeemable_codes)

                        # Gửi mã cho người dùng
                        bot.send_message(message.chat.id, f"🎉 Bạn đã nhận được mã code: {code}\n"
                                                          f"Số tiền {amount} đồng đã được trừ khỏi tài khoản của bạn.")
                    
                        # Thông báo cho admin về giao dịch
                        for admin_id in admins:
                            bot.send_message(admin_id, f"🛡 Yêu cầu rút mã tự động cho user @{message.from_user.username} (ID: {user_id}):"
                                                       f"\n- Ngân hàng: {bank_name}"
                                                       f"\n- Số tiền: {amount} đồng"
                                                       f"\n- Mã code: {code}")
                    else:
                        bot.send_message(message.chat.id, "⛔️ Hiện tại không có mã code nào khả dụng. Vui lòng thử lại sau.")
                else:
                    bot.send_message(message.chat.id, "⛔️ Số dư của bạn không đủ để thực hiện giao dịch.")
            else:
                bot.send_message(message.chat.id, "⚠️ Số tiền rút tối thiểu là 20.000 VND.")
        else:
            bot.send_message(message.chat.id, "🚫 Sai cú pháp. Vui lòng nhập theo mẫu: /doicode [uid game] [số tiền]")
    else:
        bot.send_message(message.chat.id, "🔒 Bạn cần có số dư ít nhất 20.000 VND và đã đăng ký để thực hiện lệnh rút tiền.")


@bot.callback_query_handler(func=lambda call: call.data.startswith(('approve_', 'decline_')))
def handle_approval(call):
    try:
        action, user_id, amount = call.data.split('_')
        if action == "approve":
            bot.send_message(user_id, f"🎉 Yêu cầu rút tiền của bạn đã được duyệt thành công với số tiền {amount} đồng ✅.")
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="✅ Đã duyệt yêu cầu rút tiền.")
        elif action == "decline":
            bot.send_message(user_id, "❌ Yêu cầu rút tiền của bạn đã bị hủy. Vui lòng liên hệ admin để biết thêm chi tiết.")
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="❌ Đã hủy yêu cầu rút tiền.")

        # Xóa nút inline sau khi duyệt hoặc hủy
        bot.edit_message_text("Yêu cầu đã được xử lý", call.message.chat.id, call.message.message_id)
    except ValueError:
        bot.send_message(call.message.chat.id, "⚠️ Đã xảy ra lỗi khi xử lý yêu cầu. Vui lòng thử lại sau.")

@bot.message_handler(func=lambda message: message.text == '📊 Thống Kê')
def handle_statistics(message):
    user_id = message.from_user.id

    if user_id not in admins:
        bot.reply_to(message, "Bạn không có quyền xem thống kê.")
        return

    total_users = len(user_data)
    total_balance = sum(user['balance'] for user in user_data.values())

    response_text = f"""
    📊 **Thống Kê Hiện Tại**
    - Tổng số người dùng: {total_users}
    - Tổng số dư: {total_balance} đồng
    """
    bot.send_message(message.chat.id, response_text, parse_mode='Markdown')

@bot.message_handler(func=lambda message: message.text == '🆘 Hỗ Trợ')
def handle_support(message):
    bot.send_message(message.chat.id, "🆘 Bạn cần hỗ trợ? Vui lòng liên hệ với chúng tôi qua Telegram: @nguyendanh8386 Và Đợi Phản Hồi.")

@bot.message_handler(commands=['chatmem'])
def handle_chatmem_command(message):
    if message.from_user.id not in admins:
        bot.reply_to(message, "Bạn không có quyền sử dụng lệnh này.")
        return

    try:
        details = message.text.split(maxsplit=2)
        if len(details) < 3:
            raise ValueError("Sai cú pháp. Sử dụng: /chatmem [user_id] [Nội dung tin nhắn]")

        target_user_id = int(details[1])
        message_text = details[2]

        bot.send_message(target_user_id, message_text)
        bot.reply_to(message, f"Đã gửi tin nhắn đến người dùng ID {target_user_id}.")
    except (IndexError, ValueError):
        bot.reply_to(message, 'Vui lòng nhập theo cú pháp: /chatmem [user_id] [Nội dung tin nhắn]')

# Start the bot
bot.infinity_polling(timeout=60, long_polling_timeout=1)
#phần cuối
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import CommandHandler, Dispatcher, CallbackContext
import os

# ====== Cấu hình bot ======
TOKEN = "7707470835:AAF2TSWpsFvM0FLySx3XbO_-fRjjb_8utCQ"  # Thay bằng token thật
bot = Bot(token=TOKEN)

# ====== Flask App ======
app = Flask(__name__)

@app.route("/")
def index():
    return "Bot is running!"

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "ok"

# ====== Hàm lệnh /start ======
def start(update: Update, context: CallbackContext):
    update.message.reply_text("Chào mừng bạn đến với bot!")

# ====== Khởi tạo dispatcher ======
dispatcher = Dispatcher(bot, None, use_context=True)
dispatcher.add_handler(CommandHandler("start", start))

# ====== Set webhook khi khởi động ======
WEBHOOK_URL = f"https://repo-urw6.onrender.com/{TOKEN}"  # Thay URL thật nếu dùng Render hoặc domain riêng
bot.delete_webhook()
bot.set_webhook(url=WEBHOOK_URL)

# ====== Chạy Flask app ======
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
