import logging
import re
import asyncio
import os
import json
from datetime import datetime, timedelta, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError, PhoneCodeExpiredError
import urllib.request
import sys
import signal

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
    """دریافت زمان ایران (فقط ساعت و دقیقه)"""
    now = datetime.now(timezone.utc)
    iran_time = now + timedelta(hours=3, minutes=30)
    return iran_time

def get_iran_time_str():
    """دریافت زمان ایران به صورت ساعت:دقیقه (بدون ثانیه)"""
    return get_iran_time().strftime("%H:%M")

def get_iran_date_str():
    """دریافت تاریخ ایران"""
    return get_iran_time().strftime("%Y/%m/%d")

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
    name = user.first_name if user.first_name else "کاربر"
    user_id = str(user.id)
    
    self_count = len(self_data.get(user_id, []))
    
    text = f"""
🌟 ربات مدیریت حساب‌های شخصی

جناب {name} گرامی

با سلام و احترام، به ربات مدیریت حساب‌های شخصی خود خوش آمدید.
این ربات به شما امکان مدیریت سلف‌های تلگرام را می‌دهد.

تعداد سلف‌های ثبت شده: {self_count}

در صورت نیاز به ایجاد سلف جدید، از دکمه زیر استفاده فرمایید.
"""
    
    keyboard = [
        [InlineKeyboardButton("🔷 ایجاد سلف جدید", callback_data="new_session")],
        [InlineKeyboardButton("📋 مشاهده سلف‌ها", callback_data="list_selfs")]
    ]
    
    if edit and update.callback_query:
        await update.callback_query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
        await update.callback_query.answer()
    else:
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )

# ============ لیست سلف‌ها ============
async def list_selfs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    selfs = self_data.get(user_id, [])
    
    if not selfs:
        text = """
📋 لیست سلف‌ها

❌ هیچ سلفی ثبت نشده است.

لطفاً از گزینه "ایجاد سلف جدید" استفاده فرمایید.
"""
        keyboard = [
            [InlineKeyboardButton("🔷 ایجاد سلف جدید", callback_data="new_session")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
        return
    
    text = f"""
📋 لیست سلف‌های ثبت شده ({len(selfs)})

"""
    
    keyboard = []
    
    for i, self_account in enumerate(selfs):
        phone = self_account.get('phone', 'نامشخص')
        active_time = self_account.get('active_time', 'تنظیم نشده')
        account_name = self_account.get('account_name', 'نامشخص')
        clock_active = self_account.get('clock_active', False)
        
        clock_status = "🟢 فعال" if clock_active else "🔴 غیرفعال"
        time_display = f"{account_name} {active_time}" if active_time != 'تنظیم نشده' else f"{account_name} - ساعت تنظیم نشده"
        
        text += f"""
🔹 سلف شماره {i+1}
   📱 شماره: {phone}
   🕐 ساعت: {time_display}
   📊 وضعیت ساعت: {clock_status}
"""
        keyboard.append([InlineKeyboardButton(f"⚙️ مدیریت سلف {i+1}", callback_data=f"manage_{i}")])
    
    keyboard.append([InlineKeyboardButton("🔷 ایجاد سلف جدید", callback_data="new_session")])
    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="back")])
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

# ============ مدیریت سلف ============
async def manage_self(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    index = int(query.data.split('_')[1])
    
    selfs = self_data.get(user_id, [])
    if index >= len(selfs):
        await query.edit_message_text("❌ سلف مورد نظر یافت نشد.", parse_mode='HTML')
        return
    
    self_account = selfs[index]
    phone = self_account.get('phone', 'نامشخص')
    account_name = self_account.get('account_name', 'نامشخص')
    clock_active = self_account.get('clock_active', False)
    active_time = self_account.get('active_time', 'تنظیم نشده')
    
    time_display = f"{account_name} {active_time}" if active_time != 'تنظیم نشده' else f"{account_name} - ساعت تنظیم نشده"
    clock_status = "🟢 فعال" if clock_active else "🔴 غیرفعال"
    
    text = f"""
⚙️ مدیریت سلف شماره {index + 1}

📱 شماره: {phone}
👤 نام اکانت: {account_name}
🕐 ساعت: {time_display}
📊 وضعیت: {clock_status}

لطفاً یکی از گزینه‌های زیر را انتخاب فرمایید:
"""
    
    keyboard = [
        [InlineKeyboardButton("👤 تنظیم پروفایل", callback_data=f"profile_{index}")]
    ]
    
    if clock_active:
        keyboard.append([InlineKeyboardButton("⏰ غیرفعال کردن ساعت", callback_data=f"deactivate_clock_{index}")])
    else:
        keyboard.append([InlineKeyboardButton("⏰ فعال کردن ساعت", callback_data=f"activate_clock_{index}")])
    
    keyboard.append([InlineKeyboardButton("🔙 بازگشت به لیست", callback_data="list_selfs")])
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

# ============ تنظیم پروفایل ============
async def profile_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    index = int(query.data.split('_')[1])
    
    selfs = self_data.get(user_id, [])
    if index >= len(selfs):
        await query.edit_message_text("❌ سلف مورد نظر یافت نشد.", parse_mode='HTML')
        return
    
    self_account = selfs[index]
    phone = self_account.get('phone', 'نامشخص')
    account_name = self_account.get('account_name', 'نامشخص')
    clock_active = self_account.get('clock_active', False)
    
    text = f"""
👤 تنظیم پروفایل سلف شماره {index + 1}

📱 شماره: {phone}
👤 نام اکانت: {account_name}
📊 وضعیت ساعت: {'🟢 فعال' if clock_active else '🔴 غیرفعال'}

در حال دریافت اطلاعات پروفایل...
"""
    
    await query.edit_message_text(
        text,
        parse_mode='HTML'
    )
    
    try:
        client = TelegramClient(
            self_account.get('session'),
            self_account.get('api_id'),
            self_account.get('api_hash')
        )
        await client.connect()
        
        if await client.is_user_authorized():
            me = await client.get_me()
            
            first_name = me.first_name if me.first_name else "ندارد"
            last_name = me.last_name if me.last_name else "ندارد"
            username = f"@{me.username}" if me.username else "ندارد"
            
            profile_text = f"""
👤 پروفایل اکانت

📱 شماره: {phone}
👤 نام: {first_name}
👤 نام خانوادگی: {last_name}
👤 یوزرنیم: {username}
🆔 آیدی: {me.id}
📊 وضعیت ساعت: {'🟢 فعال' if clock_active else '🔴 غیرفعال'}

اطلاعات پروفایل با موفقیت دریافت شد.
"""
            
            await client.disconnect()
            
            keyboard = [
                [InlineKeyboardButton("🔙 بازگشت به مدیریت", callback_data=f"manage_{index}")],
                [InlineKeyboardButton("🏠 بازگشت به منو", callback_data="back")]
            ]
            
            await query.edit_message_text(
                profile_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='HTML'
            )
        else:
            await client.disconnect()
            text = """
❌ اکانت معتبر نیست!

لطفاً مجدداً سلف را ایجاد کنید.
"""
            keyboard = [
                [InlineKeyboardButton("🔙 بازگشت به مدیریت", callback_data=f"manage_{index}")],
                [InlineKeyboardButton("🏠 بازگشت به منو", callback_data="back")]
            ]
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
            
    except Exception as e:
        logger.error(f"Error getting profile: {e}")
        text = f"""
❌ خطا در دریافت پروفایل!

{str(e)[:200]}
"""
        keyboard = [
            [InlineKeyboardButton("🔙 بازگشت به مدیریت", callback_data=f"manage_{index}")],
            [InlineKeyboardButton("🏠 بازگشت به منو", callback_data="back")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

# ============ فعال کردن ساعت ============
async def activate_clock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    index = int(query.data.split('_')[2])
    
    selfs = self_data.get(user_id, [])
    if index >= len(selfs):
        await query.edit_message_text("❌ سلف مورد نظر یافت نشد.", parse_mode='HTML')
        return
    
    time_str = get_iran_time_str()
    account_name = selfs[index].get('account_name', 'کاربر')
    
    selfs[index]['active_time'] = time_str
    selfs[index]['clock_active'] = True
    save_data()
    
    text = f"""
✅ ساعت با موفقیت فعال شد!

👤 نام اکانت: {account_name}
🕐 ساعت فعال: {time_str}

ساعت برای این سلف با موفقیت فعال گردید.
"""
    
    keyboard = [
        [InlineKeyboardButton("🔙 بازگشت به مدیریت", callback_data=f"manage_{index}")],
        [InlineKeyboardButton("🏠 بازگشت به منو", callback_data="back")]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

# ============ غیرفعال کردن ساعت ============
async def deactivate_clock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    index = int(query.data.split('_')[2])
    
    selfs = self_data.get(user_id, [])
    if index >= len(selfs):
        await query.edit_message_text("❌ سلف مورد نظر یافت نشد.", parse_mode='HTML')
        return
    
    account_name = selfs[index].get('account_name', 'کاربر')
    
    selfs[index]['clock_active'] = False
    save_data()
    
    text = f"""
❌ ساعت با موفقیت غیرفعال شد!

👤 نام اکانت: {account_name}

ساعت برای این سلف با موفقیت غیرفعال گردید.
"""
    
    keyboard = [
        [InlineKeyboardButton("🔙 بازگشت به مدیریت", callback_data=f"manage_{index}")],
        [InlineKeyboardButton("🏠 بازگشت به منو", callback_data="back")]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

# ============ دکمه ساخت سلف ============
async def new_session(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    await clear_user_session(user_id)
    user_sessions[user_id] = {"step": "phone"}
    
    text = """
📱 مرحله اول: وارد کردن شماره تلفن

لطفاً شماره تلفن مورد نظر را به همراه کد کشور وارد فرمایید.

مثال: 989123456789

تذکر: شماره را بدون علامت (+) وارد نمایید.
"""
    
    keyboard = [[InlineKeyboardButton("🔙 لغو و بازگشت", callback_data="back")]]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

# ============ دریافت شماره ============
async def handle_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    if user_id not in user_sessions or user_sessions[user_id].get("step") != "phone":
        await update.message.reply_text("❌ لطفاً از دکمه ایجاد سلف استفاده فرمایید.", parse_mode='HTML')
        return
    
    phone = re.sub(r'[^0-9+]', '', text)
    
    if not is_valid_phone(phone):
        await update.message.reply_text(
            "❌ شماره تلفن نامعتبر است!\n\nلطفاً شماره را به صورت صحیح وارد نمایید.\nمثال: 989123456789",
            parse_mode='HTML'
        )
        return
    
    user_sessions[user_id]['phone'] = phone
    user_sessions[user_id]['step'] = "api_id"
    
    text = f"""
✅ شماره تلفن با موفقیت ثبت شد.

📱 شماره: {phone}

🔑 مرحله دوم: وارد کردن API ID

لطفاً API ID خود را از سایت my.telegram.org دریافت و وارد فرمایید.
"""
    
    keyboard = [[InlineKeyboardButton("🔙 لغو و بازگشت", callback_data="back")]]
    
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

# ============ دریافت API ID ============
async def handle_api_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    if user_id not in user_sessions or user_sessions[user_id].get("step") != "api_id":
        await update.message.reply_text("❌ لطفاً از دکمه ایجاد سلف استفاده فرمایید.", parse_mode='HTML')
        return
    
    if not text.isdigit():
        await update.message.reply_text("❌ API ID باید عدد باشد.\n\nلطفاً مجدداً وارد نمایید.", parse_mode='HTML')
        return
    
    user_sessions[user_id]['api_id'] = int(text)
    user_sessions[user_id]['step'] = "api_hash"
    
    text = f"""
✅ API ID با موفقیت ثبت شد.

🔑 API ID: {text}

🔐 مرحله سوم: وارد کردن API Hash

لطفاً API Hash خود را از سایت my.telegram.org دریافت و وارد فرمایید.
"""
    
    keyboard = [[InlineKeyboardButton("🔙 لغو و بازگشت", callback_data="back")]]
    
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

# ============ دریافت API Hash ============
async def handle_api_hash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    if user_id not in user_sessions or user_sessions[user_id].get("step") != "api_hash":
        await update.message.reply_text("❌ لطفاً از دکمه ایجاد سلف استفاده فرمایید.", parse_mode='HTML')
        return
    
    if len(text) < 30:
        await update.message.reply_text("❌ API Hash باید حداقل 30 کاراکتر باشد.\n\nلطفاً مجدداً وارد نمایید.", parse_mode='HTML')
        return
    
    user_sessions[user_id]['api_hash'] = text
    user_sessions[user_id]['step'] = "code"
    
    msg = await update.message.reply_text("⏳ در حال ارسال کد تایید...\n\nلطفاً چند لحظه صبر فرمایید.", parse_mode='HTML')
    
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
✅ کد تایید با موفقیت ارسال شد.

📩 کد ۵ رقمی به شماره {phone} ارسال گردید.

📝 لطفاً کد دریافتی را وارد فرمایید.

مثال: 12345 یا 1.2.3.4.5
"""
        
        keyboard = [[InlineKeyboardButton("🔙 لغو و بازگشت", callback_data="back")]]
        
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=msg.message_id,
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
        
    except Exception as e:
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=msg.message_id,
            text=f"❌ خطا در ارسال کد: {str(e)[:200]}",
            parse_mode='HTML'
        )
        await clear_user_session(user_id)

# ============ دریافت کد ============
async def handle_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    raw_code = update.message.text.strip()
    
    if user_id not in user_sessions or user_sessions[user_id].get("step") != "code":
        await update.message.reply_text("❌ لطفاً از دکمه ایجاد سلف استفاده فرمایید.", parse_mode='HTML')
        return
    
    code = clean_code(raw_code)
    
    if not code.isdigit() or len(code) != 5:
        await update.message.reply_text(
            "❌ کد باید ۵ رقم باشد.\n\nمثال: 12345",
            parse_mode='HTML'
        )
        return
    
    data = user_sessions[user_id]
    client = data.get('client')
    
    if not client:
        await update.message.reply_text("❌ اتصال معتبر نیست.\n\nلطفاً مجدداً تلاش فرمایید.", parse_mode='HTML')
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
        
        # دریافت اطلاعات اکانت
        try:
            client2 = TelegramClient(session_string, api_id, api_hash)
            await client2.connect()
            me = await client2.get_me()
            account_name = me.first_name if me and me.first_name else "کاربر"
            await client2.disconnect()
        except:
            account_name = "کاربر"
        
        user_id_str = str(user_id)
        if user_id_str not in self_data:
            self_data[user_id_str] = []
        
        time_str = get_iran_time_str()
        date_str = get_iran_date_str()
        
        self_data[user_id_str].append({
            "session": session_string,
            "phone": phone,
            "api_id": api_id,
            "api_hash": api_hash,
            "account_name": account_name,
            "active": True,
            "clock_active": False,
            "active_time": "تنظیم نشده",
            "created": f"{date_str} {time_str}",
            "last_update": f"{date_str} {time_str}"
        })
        save_data()
        
        await clear_user_session(user_id)
        
        text = f"""
✅ سلف جدید با موفقیت ایجاد شد!

📱 شماره: {phone}
👤 نام اکانت: {account_name}
🔑 شناسه جلسه: {mask_string(session_string, 10)}

سلف جدید به لیست شما اضافه گردید.
"""
        
        keyboard = [
            [InlineKeyboardButton("🔷 ایجاد سلف جدید", callback_data="new_session")],
            [InlineKeyboardButton("📋 مشاهده سلف‌ها", callback_data="list_selfs")],
            [InlineKeyboardButton("🏠 بازگشت به صفحه اصلی", callback_data="back")]
        ]
        
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
        
    except SessionPasswordNeededError:
        user_sessions[user_id]['step'] = "password"
        text = """
🔐 رمز عبور دو مرحله‌ای

حساب کاربری مورد نظر دارای رمز عبور دو مرحله‌ای می‌باشد.

لطفاً رمز عبور خود را وارد فرمایید.
"""
        keyboard = [[InlineKeyboardButton("🔙 لغو و بازگشت", callback_data="back")]]
        
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
        
    except PhoneCodeExpiredError:
        await client.send_code_request(phone)
        await update.message.reply_text(
            "🔄 کد قبلی منقضی شده است.\n\n📩 کد جدید ارسال گردید.\n\n📝 لطفاً کد جدید را وارد فرمایید:",
            parse_mode='HTML'
        )
        
    except Exception as e:
        await update.message.reply_text(
            f"❌ خطا: {str(e)[:200]}",
            parse_mode='HTML'
        )
        await clear_user_session(user_id)

# ============ دریافت پسورد ============
async def handle_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    password = update.message.text.strip()
    
    if user_id not in user_sessions or user_sessions[user_id].get("step") != "password":
        await update.message.reply_text("❌ لطفاً از دکمه ایجاد سلف استفاده فرمایید.", parse_mode='HTML')
        return
    
    data = user_sessions[user_id]
    client = data.get('client')
    
    if not client:
        await update.message.reply_text("❌ اتصال معتبر نیست.\n\nلطفاً مجدداً تلاش فرمایید.", parse_mode='HTML')
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
        
        # دریافت اطلاعات اکانت
        try:
            client2 = TelegramClient(session_string, data['api_id'], data['api_hash'])
            await client2.connect()
            me = await client2.get_me()
            account_name = me.first_name if me and me.first_name else "کاربر"
            await client2.disconnect()
        except:
            account_name = "کاربر"
        
        user_id_str = str(user_id)
        if user_id_str not in self_data:
            self_data[user_id_str] = []
        
        time_str = get_iran_time_str()
        date_str = get_iran_date_str()
        
        self_data[user_id_str].append({
            "session": session_string,
            "phone": data['phone'],
            "api_id": data['api_id'],
            "api_hash": data['api_hash'],
            "account_name": account_name,
            "active": True,
            "clock_active": False,
            "active_time": "تنظیم نشده",
            "created": f"{date_str} {time_str}",
            "last_update": f"{date_str} {time_str}"
        })
        save_data()
        
        await clear_user_session(user_id)
        
        text = f"""
✅ سلف جدید با موفقیت ایجاد شد!

📱 شماره: {data['phone']}
👤 نام اکانت: {account_name}
🔑 شناسه جلسه: {mask_string(session_string, 10)}

سلف جدید به لیست شما اضافه گردید.
"""
        
        keyboard = [
            [InlineKeyboardButton("🔷 ایجاد سلف جدید", callback_data="new_session")],
            [InlineKeyboardButton("📋 مشاهده سلف‌ها", callback_data="list_selfs")],
            [InlineKeyboardButton("🏠 بازگشت به صفحه اصلی", callback_data="back")]
        ]
        
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
        
    except Exception as e:
        await update.message.reply_text(
            f"❌ رمز عبور اشتباه است.\n\n{str(e)[:100]}",
            parse_mode='HTML'
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
    
    await update.message.reply_text("❌ لطفاً از دکمه‌های منو استفاده فرمایید.", parse_mode='HTML')

# ============ اجرا ============
def main():
    try:
        # حذف webhook
        delete_webhook()
        
        print("=" * 60)
        print("🌟 ربات مدیریت حساب‌های شخصی")
        print("=" * 60)
        print(f"📌 توکن: {TOKEN[:10]}...{TOKEN[-5:]}")
        print("=" * 60)
        
        application = Application.builder().token(TOKEN).build()
        
        application.add_handler(CallbackQueryHandler(new_session, pattern="^new_session$"))
        application.add_handler(CallbackQueryHandler(list_selfs, pattern="^list_selfs$"))
        application.add_handler(CallbackQueryHandler(manage_self, pattern="^manage_"))
        application.add_handler(CallbackQueryHandler(profile_settings, pattern="^profile_"))
        application.add_handler(CallbackQueryHandler(activate_clock, pattern="^activate_clock_"))
        application.add_handler(CallbackQueryHandler(deactivate_clock, pattern="^deactivate_clock_"))
        application.add_handler(CallbackQueryHandler(back_to_menu, pattern="^back$"))
        
        application.add_handler(CommandHandler("start", start))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_messages))
        
        print("✅ ربات با موفقیت راه‌اندازی شد.")
        print("💡 برای شروع از /start استفاده فرمایید.")
        print("=" * 60)
        
        # اجرا با تنظیمات ساده
        application.run_polling(
            drop_pending_updates=True
        )
        
    except Exception as e:
        print(f"❌ خطا: {e}")

if __name__ == "__main__":
    main()
