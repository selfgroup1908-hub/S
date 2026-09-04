import logging
import re
import asyncio
import os
import json
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError, PhoneCodeExpiredError
import urllib.request

# ============ تنظیمات ============
TOKEN = "8810050319:AAH5T1qehg7U-oplDB_yp4JVGZl6W866BzY"

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

user_sessions = {}
self_data = {}

# ============ فایل ذخیره اطلاعات ============
DATA_FILE = "selfs.json"

def load_data():
    global self_data
    try:
        with open(DATA_FILE, 'r') as f:
            self_data = json.load(f)
    except:
        self_data = {}

def save_data():
    with open(DATA_FILE, 'w') as f:
        json.dump(self_data, f)

load_data()

# ============ توابع کمکی ============
def delete_webhook():
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/deleteWebhook"
        with urllib.request.urlopen(url) as response:
            return True
    except:
        return False

def is_valid_phone(text):
    phone = re.sub(r'[^0-9+]', '', text)
    return len(phone) >= 10

def is_valid_api_id(text):
    return text.isdigit()

def is_valid_api_hash(text):
    return len(text) >= 30

def clean_code(text):
    return re.sub(r'[.\s\-]', '', text).strip()

def mask_string(s, show=5):
    if not s:
        return "***"
    if len(s) <= show:
        return s
    return s[:show] + "..." + s[-3:]

def get_iran_time():
    """دریافت زمان دقیق ایران (UTC+3:30)"""
    now = datetime.utcnow()
    iran_time = now + timedelta(hours=3, minutes=30)
    return iran_time.strftime("%Y/%m/%d %H:%M:%S")

async def clear_user_session(user_id):
    if user_id in user_sessions:
        try:
            client = user_sessions[user_id].get('client')
            if client:
                await client.disconnect()
        except:
            pass
        del user_sessions[user_id]

# ============ منوی اصلی ============
async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, edit=False):
    user = update.effective_user
    name = user.first_name
    user_id = str(user.id)
    
    self_count = len(self_data.get(user_id, []))
    
    text = f"""
🌟 **ربات مدیریت حساب‌های شخصی**

*جناب {name} گرامی*

با سلام و احترام، به ربات مدیریت حساب‌های شخصی خود خوش آمدید.
این ربات به شما امکان مدیریت سلف‌های تلگرام را می‌دهد.

📊 *تعداد سلف‌های ثبت شده:* **{self_count}**

🔹 در صورت نیاز به ایجاد سلف جدید، از دکمه زیر استفاده فرمایید.
"""
    
    keyboard = [
        [InlineKeyboardButton("🔷 ایجاد سلف جدید", callback_data="new_session")],
        [InlineKeyboardButton("📋 مشاهده سلف‌ها", callback_data="list_selfs")]
    ]
    
    if edit and update.callback_query:
        await update.callback_query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        await update.callback_query.answer()
    else:
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

# ============ لیست سلف‌ها ============
async def list_selfs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    selfs = self_data.get(user_id, [])
    
    if not selfs:
        text = """
📋 *لیست سلف‌ها*

❌ *هیچ سلفی ثبت نشده است.*

🔹 لطفاً از گزینه *"ایجاد سلف جدید"* استفاده فرمایید.
"""
        keyboard = [
            [InlineKeyboardButton("🔷 ایجاد سلف جدید", callback_data="new_session")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        return
    
    text = f"""
📋 *لیست سلف‌های ثبت شده ({len(selfs)})*

"""
    
    keyboard = []
    
    for i, self_account in enumerate(selfs):
        status = "✅ *فعال*" if self_account.get('active', True) else "❌ *غیرفعال*"
        phone = self_account.get('phone', 'نامشخص')
        active_time = self_account.get('active_time', 'تنظیم نشده')
        
        text += f"""
🔹 *سلف شماره {i+1}*
   📱 شماره: `{phone}`
   📊 وضعیت: {status}
   ⏰ ساعت فعال: `{active_time}`
"""
        keyboard.append([InlineKeyboardButton(f"⚙️ مدیریت سلف {i+1}", callback_data=f"manage_{i}")])
    
    keyboard.append([InlineKeyboardButton("🔷 ایجاد سلف جدید", callback_data="new_session")])
    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="back")])
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

# ============ مدیریت سلف ============
async def manage_self(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    index = int(query.data.split('_')[1])
    
    selfs = self_data.get(user_id, [])
    if index >= len(selfs):
        await query.edit_message_text("❌ سلف مورد نظر یافت نشد.", parse_mode='Markdown')
        return
    
    self_account = selfs[index]
    phone = self_account.get('phone', 'نامشخص')
    is_active = self_account.get('active', True)
    active_time = self_account.get('active_time', 'تنظیم نشده')
    
    status_text = "✅ *فعال*" if is_active else "❌ *غیرفعال*"
    
    text = f"""
⚙️ *مدیریت سلف شماره {index + 1}*

📱 *شماره:* `{phone}`
📊 *وضعیت:* {status_text}
⏰ *ساعت فعال:* `{active_time}`

🔹 لطفاً یکی از گزینه‌های زیر را انتخاب فرمایید:
"""
    
    keyboard = []
    
    if is_active:
        keyboard.append([InlineKeyboardButton("⏰ تنظیم ساعت فعال", callback_data=f"set_time_{index}")])
        keyboard.append([InlineKeyboardButton("❌ غیرفعال کردن سلف", callback_data=f"deactivate_{index}")])
    else:
        keyboard.append([InlineKeyboardButton("✅ فعال کردن سلف", callback_data=f"activate_{index}")])
    
    keyboard.append([InlineKeyboardButton("🔙 بازگشت به لیست", callback_data="list_selfs")])
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

# ============ تنظیم ساعت فعال ============
async def set_active_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    index = int(query.data.split('_')[2])
    
    selfs = self_data.get(user_id, [])
    if index >= len(selfs):
        await query.edit_message_text("❌ سلف مورد نظر یافت نشد.", parse_mode='Markdown')
        return
    
    # دریافت زمان دقیق ایران
    time_str = get_iran_time()
    
    # ذخیره زمان در دیتا
    selfs[index]['active_time'] = time_str
    selfs[index]['active'] = True
    save_data()
    
    text = f"""
✅ *ساعت فعال با موفقیت ثبت شد!*

📱 *شماره:* `{selfs[index].get('phone', 'نامشخص')}`
⏰ *ساعت فعال:* `{time_str}`

🔹 ساعت فعال برای این سلف با موفقیت تنظیم گردید.
"""
    
    keyboard = [
        [InlineKeyboardButton("🔙 بازگشت به مدیریت", callback_data=f"manage_{index}")],
        [InlineKeyboardButton("🏠 بازگشت به منو", callback_data="back")]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

# ============ فعال کردن سلف ============
async def activate_self(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    index = int(query.data.split('_')[1])
    
    selfs = self_data.get(user_id, [])
    if index >= len(selfs):
        await query.edit_message_text("❌ سلف مورد نظر یافت نشد.", parse_mode='Markdown')
        return
    
    selfs[index]['active'] = True
    save_data()
    
    text = f"""
✅ *سلف با موفقیت فعال شد!*

📱 *شماره:* `{selfs[index].get('phone', 'نامشخص')}`

🔹 سلف مورد نظر با موفقیت فعال گردید.
"""
    
    keyboard = [
        [InlineKeyboardButton("🔙 بازگشت به مدیریت", callback_data=f"manage_{index}")],
        [InlineKeyboardButton("🏠 بازگشت به منو", callback_data="back")]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

# ============ غیرفعال کردن سلف ============
async def deactivate_self(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    index = int(query.data.split('_')[1])
    
    selfs = self_data.get(user_id, [])
    if index >= len(selfs):
        await query.edit_message_text("❌ سلف مورد نظر یافت نشد.", parse_mode='Markdown')
        return
    
    selfs[index]['active'] = False
    save_data()
    
    text = f"""
❌ *سلف با موفقیت غیرفعال شد!*

📱 *شماره:* `{selfs[index].get('phone', 'نامشخص')}`

🔹 سلف مورد نظر با موفقیت غیرفعال گردید.
"""
    
    keyboard = [
        [InlineKeyboardButton("🔙 بازگشت به مدیریت", callback_data=f"manage_{index}")],
        [InlineKeyboardButton("🏠 بازگشت به منو", callback_data="back")]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

# ============ دکمه ساخت سلف ============
async def new_session(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    await clear_user_session(user_id)
    user_sessions[user_id] = {"step": "phone"}
    
    text = """
📱 *مرحله اول: وارد کردن شماره تلفن*

🔹 لطفاً شماره تلفن مورد نظر را به همراه کد کشور وارد فرمایید.

📌 *مثال:* `989123456789`

⚠️ *تذکر:* شماره را بدون علامت (+) وارد نمایید.
"""
    
    keyboard = [[InlineKeyboardButton("🔙 لغو و بازگشت", callback_data="back")]]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

# ============ دریافت شماره ============
async def handle_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    if user_id not in user_sessions or user_sessions[user_id].get("step") != "phone":
        await update.message.reply_text("❌ لطفاً از دکمه ایجاد سلف استفاده فرمایید.", parse_mode='Markdown')
        return
    
    phone = re.sub(r'[^0-9+]', '', text)
    
    if not is_valid_phone(phone):
        await update.message.reply_text(
            "❌ *شماره تلفن نامعتبر است!*\n\n📌 لطفاً شماره را به صورت صحیح وارد نمایید.\nمثال: `989123456789`",
            parse_mode='Markdown'
        )
        return
    
    user_sessions[user_id]['phone'] = phone
    user_sessions[user_id]['step'] = "api_id"
    
    text = f"""
✅ *شماره تلفن با موفقیت ثبت شد.*

📱 شماره: `{phone}`

🔑 *مرحله دوم: وارد کردن API ID*

🔹 لطفاً API ID خود را از سایت my.telegram.org دریافت و وارد فرمایید.
"""
    
    keyboard = [[InlineKeyboardButton("🔙 لغو و بازگشت", callback_data="back")]]
    
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

# ============ دریافت API ID ============
async def handle_api_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    if user_id not in user_sessions or user_sessions[user_id].get("step") != "api_id":
        await update.message.reply_text("❌ لطفاً از دکمه ایجاد سلف استفاده فرمایید.", parse_mode='Markdown')
        return
    
    if not text.isdigit():
        await update.message.reply_text("❌ *API ID باید عدد باشد.*\n\n📌 لطفاً مجدداً وارد نمایید.", parse_mode='Markdown')
        return
    
    user_sessions[user_id]['api_id'] = int(text)
    user_sessions[user_id]['step'] = "api_hash"
    
    text = f"""
✅ *API ID با موفقیت ثبت شد.*

🔑 API ID: `{text}`

🔐 *مرحله سوم: وارد کردن API Hash*

🔹 لطفاً API Hash خود را از سایت my.telegram.org دریافت و وارد فرمایید.
"""
    
    keyboard = [[InlineKeyboardButton("🔙 لغو و بازگشت", callback_data="back")]]
    
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

# ============ دریافت API Hash ============
async def handle_api_hash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    if user_id not in user_sessions or user_sessions[user_id].get("step") != "api_hash":
        await update.message.reply_text("❌ لطفاً از دکمه ایجاد سلف استفاده فرمایید.", parse_mode='Markdown')
        return
    
    if len(text) < 30:
        await update.message.reply_text("❌ *API Hash باید حداقل 30 کاراکتر باشد.*\n\n📌 لطفاً مجدداً وارد نمایید.", parse_mode='Markdown')
        return
    
    user_sessions[user_id]['api_hash'] = text
    user_sessions[user_id]['step'] = "code"
    
    msg = await update.message.reply_text("⏳ *در حال ارسال کد تایید...*\n\nلطفاً چند لحظه صبر فرمایید.", parse_mode='Markdown')
    
    try:
        data = user_sessions[user_id]
        phone = data['phone']
        api_id = data['api_id']
        api_hash = data['api_hash']
        
        session_name = f"temp_{phone}_{api_id}"
        client = TelegramClient(session_name, api_id, api_hash)
        
        await client.connect()
        await client.send_code_request(phone)
        
        user_sessions[user_id]['client'] = client
        user_sessions[user_id]['session_name'] = session_name
        user_sessions[user_id]['msg_id'] = msg.message_id
        
        text = f"""
✅ *کد تایید با موفقیت ارسال شد.*

📩 کد ۵ رقمی به شماره `{phone}` ارسال گردید.

📝 لطفاً کد دریافتی را وارد فرمایید.

📌 *مثال:* `12345` یا `1.2.3.4.5`
"""
        
        keyboard = [[InlineKeyboardButton("🔙 لغو و بازگشت", callback_data="back")]]
        
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=msg.message_id,
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=msg.message_id,
            text=f"❌ *خطا در ارسال کد:* {str(e)[:200]}",
            parse_mode='Markdown'
        )
        await clear_user_session(user_id)

# ============ دریافت کد ============
async def handle_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    raw_code = update.message.text.strip()
    
    if user_id not in user_sessions or user_sessions[user_id].get("step") != "code":
        await update.message.reply_text("❌ لطفاً از دکمه ایجاد سلف استفاده فرمایید.", parse_mode='Markdown')
        return
    
    code = clean_code(raw_code)
    
    if not code.isdigit() or len(code) != 5:
        await update.message.reply_text(
            "❌ *کد باید ۵ رقم باشد.*\n\n📌 مثال: `12345`",
            parse_mode='Markdown'
        )
        return
    
    data = user_sessions[user_id]
    client = data.get('client')
    
    if not client:
        await update.message.reply_text("❌ *اتصال معتبر نیست.*\n\nلطفاً مجدداً تلاش فرمایید.", parse_mode='Markdown')
        await clear_user_session(user_id)
        return
    
    try:
        phone = data['phone']
        api_id = data['api_id']
        api_hash = data['api_hash']
        
        await client.sign_in(phone, code)
        session_string = client.session.save()
        await client.disconnect()
        
        try:
            os.remove(f"{data.get('session_name', 'temp')}.session")
        except:
            pass
        
        user_id_str = str(user_id)
        if user_id_str not in self_data:
            self_data[user_id_str] = []
        
        # دریافت زمان دقیق ایران
        time_str = get_iran_time()
        
        self_data[user_id_str].append({
            "session": session_string,
            "phone": phone,
            "api_id": api_id,
            "api_hash": api_hash,
            "active": True,
            "created": time_str,
            "active_time": time_str
        })
        save_data()
        
        await clear_user_session(user_id)
        
        text = f"""
✅ *سلف جدید با موفقیت ایجاد شد!*

📱 *شماره:* `{phone}`
🔑 *شناسه جلسه:* `{mask_string(session_string, 10)}`
⏰ *ساعت فعال:* `{time_str}`

🎯 سلف جدید به لیست شما اضافه گردید.
"""
        
        keyboard = [
            [InlineKeyboardButton("🔷 ایجاد سلف جدید", callback_data="new_session")],
            [InlineKeyboardButton("📋 مشاهده سلف‌ها", callback_data="list_selfs")],
            [InlineKeyboardButton("🏠 بازگشت به صفحه اصلی", callback_data="back")]
        ]
        
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    except SessionPasswordNeededError:
        user_sessions[user_id]['step'] = "password"
        text = """
🔐 *رمز عبور دو مرحله‌ای*

🔹 حساب کاربری مورد نظر دارای رمز عبور دو مرحله‌ای می‌باشد.

📝 لطفاً *رمز عبور* خود را وارد فرمایید.
"""
        keyboard = [[InlineKeyboardButton("🔙 لغو و بازگشت", callback_data="back")]]
        
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    except PhoneCodeExpiredError:
        await client.send_code_request(phone)
        await update.message.reply_text(
            "🔄 *کد قبلی منقضی شده است.*\n\n📩 کد جدید ارسال گردید.\n\n📝 لطفاً کد جدید را وارد فرمایید:",
            parse_mode='Markdown'
        )
        
    except Exception as e:
        await update.message.reply_text(
            f"❌ *خطا:* {str(e)[:200]}",
            parse_mode='Markdown'
        )
        await clear_user_session(user_id)

# ============ دریافت پسورد ============
async def handle_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    password = update.message.text.strip()
    
    if user_id not in user_sessions or user_sessions[user_id].get("step") != "password":
        await update.message.reply_text("❌ لطفاً از دکمه ایجاد سلف استفاده فرمایید.", parse_mode='Markdown')
        return
    
    data = user_sessions[user_id]
    client = data.get('client')
    
    if not client:
        await update.message.reply_text("❌ *اتصال معتبر نیست.*\n\nلطفاً مجدداً تلاش فرمایید.", parse_mode='Markdown')
        await clear_user_session(user_id)
        return
    
    try:
        await client.sign_in(password=password)
        session_string = client.session.save()
        await client.disconnect()
        
        try:
            os.remove(f"{data.get('session_name', 'temp')}.session")
        except:
            pass
        
        user_id_str = str(user_id)
        if user_id_str not in self_data:
            self_data[user_id_str] = []
        
        time_str = get_iran_time()
        
        self_data[user_id_str].append({
            "session": session_string,
            "phone": data['phone'],
            "api_id": data['api_id'],
            "api_hash": data['api_hash'],
            "active": True,
            "created": time_str,
            "active_time": time_str
        })
        save_data()
        
        await clear_user_session(user_id)
        
        text = f"""
✅ *سلف جدید با موفقیت ایجاد شد!*

📱 *شماره:* `{data['phone']}`
🔑 *شناسه جلسه:* `{mask_string(session_string, 10)}`
⏰ *ساعت فعال:* `{time_str}`

🎯 سلف جدید به لیست شما اضافه گردید.
"""
        
        keyboard = [
            [InlineKeyboardButton("🔷 ایجاد سلف جدید", callback_data="new_session")],
            [InlineKeyboardButton("📋 مشاهده سلف‌ها", callback_data="list_selfs")],
            [InlineKeyboardButton("🏠 بازگشت به صفحه اصلی", callback_data="back")]
        ]
        
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        await update.message.reply_text(
            f"❌ *رمز عبور اشتباه است.*\n\n{str(e)[:100]}\n\n📝 لطفاً مجدداً وارد فرمایید:",
            parse_mode='Markdown'
        )

# ============ بازگشت ============
async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    await clear_user_session(user_id)
    
    await main_menu(update, context, edit=True)

# ============ دستور start ============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await main_menu(update, context)

# ============ هندلر پیام‌ها ============
async def handle_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id in user_sessions:
        step = user_sessions[user_id].get("step")
        if step == "phone":
            await handle_phone(update, context)
        elif step == "api_id":
            await handle_api_id(update, context)
        elif step == "api_hash":
            await handle_api_hash(update, context)
        elif step == "code":
            await handle_code(update, context)
        elif step == "password":
            await handle_password(update, context)
        return
    
    await update.message.reply_text("❌ لطفاً از دکمه‌های منو استفاده فرمایید.", parse_mode='Markdown')

# ============ اجرا ============
async def main():
    try:
        delete_webhook()
        
        print("=" * 60)
        print("🌟 ربات مدیریت حساب‌های شخصی")
        print("=" * 60)
        print(f"📌 توکن: {TOKEN[:10]}...{TOKEN[-5:]}")
        print("=" * 60)
        
        application = Application.builder().token(TOKEN).build()
        
        # دکمه‌ها
        application.add_handler(CallbackQueryHandler(new_session, pattern="^new_session$"))
        application.add_handler(CallbackQueryHandler(list_selfs, pattern="^list_selfs$"))
        application.add_handler(CallbackQueryHandler(manage_self, pattern="^manage_"))
        application.add_handler(CallbackQueryHandler(set_active_time, pattern="^set_time_"))
        application.add_handler(CallbackQueryHandler(activate_self, pattern="^activate_"))
        application.add_handler(CallbackQueryHandler(deactivate_self, pattern="^deactivate_"))
        application.add_handler(CallbackQueryHandler(back_to_menu, pattern="^back$"))
        
        # دستور start
        application.add_handler(CommandHandler("start", start))
        
        # هندلر پیام‌ها
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_messages))
        
        print("✅ ربات با موفقیت راه‌اندازی شد.")
        print("💡 برای شروع از /start استفاده فرمایید.")
        print("=" * 60)
        
        # شروع پولینگ
        await application.initialize()
        await application.start()
        await application.updater.start_polling(drop_pending_updates=True)
        
        # نگه داشتن ربات در حال اجرا
        while True:
            await asyncio.sleep(1)
            
    except Exception as e:
        print(f"❌ خطا: {e}")

if __name__ == "__main__":
    asyncio.run(main())
