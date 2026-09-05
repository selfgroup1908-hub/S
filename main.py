import logging
import re
import asyncio
import os
import json
from datetime import datetime, timedelta, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError, PhoneCodeExpiredError
from telethon.tl.functions.account import UpdateProfileRequest
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
clock_tasks = {}

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
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump(self_data, f)
    except Exception as e:
        logger.error(f"Error saving data: {e}")

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

# ============ توابع ساعت ============
async def set_clock_on_profile(session_string, api_id, api_hash):
    """گذاشتن ساعت روی اسم اکانت"""
    try:
        client = TelegramClient(StringSession(session_string), api_id, api_hash)
        await client.connect()
        
        if not await client.is_user_authorized():
            await client.disconnect()
            return False
        
        me = await client.get_me()
        first_name = me.first_name if me.first_name else ""
        last_name = me.last_name if me.last_name else ""
        current_name = f"{first_name} {last_name}".strip()
        
        if not current_name:
            current_name = me.username if me.username else "کاربر"
        
        time_str = get_iran_time_str()
        clean_name = re.sub(r'\s*\d{2}:\d{2}$', '', current_name).strip()
        new_name = f"{clean_name} {time_str}".strip()
        
        if new_name != current_name:
            try:
                await client(UpdateProfileRequest(first_name=new_name))
                await client.disconnect()
                return True
            except Exception as e:
                logger.error(f"Error updating profile: {e}")
                await client.disconnect()
                return False
        
        await client.disconnect()
        return True
        
    except Exception as e:
        logger.error(f"Error in set_clock_on_profile: {e}")
        return False

async def remove_clock_from_profile(session_string, api_id, api_hash):
    """حذف ساعت از روی اسم اکانت"""
    try:
        client = TelegramClient(StringSession(session_string), api_id, api_hash)
        await client.connect()
        
        if not await client.is_user_authorized():
            await client.disconnect()
            return False
        
        me = await client.get_me()
        first_name = me.first_name if me.first_name else ""
        last_name = me.last_name if me.last_name else ""
        current_name = f"{first_name} {last_name}".strip()
        
        if not current_name:
            current_name = me.username if me.username else "کاربر"
        
        clean_name = re.sub(r'\s*\d{2}:\d{2}$', '', current_name).strip()
        
        if clean_name != current_name:
            try:
                await client(UpdateProfileRequest(first_name=clean_name))
                await client.disconnect()
                return True
            except Exception as e:
                logger.error(f"Error removing clock: {e}")
                await client.disconnect()
                return False
        
        await client.disconnect()
        return True
        
    except Exception as e:
        logger.error(f"Error in remove_clock_from_profile: {e}")
        return False

async def clock_loop(user_id, session_string, api_id, api_hash):
    """حلقه برای بروزرسانی ساعت هر دقیقه"""
    while True:
        try:
            if user_id in clock_tasks and not clock_tasks[user_id]:
                break
            await set_clock_on_profile(session_string, api_id, api_hash)
            await asyncio.sleep(60)
        except Exception as e:
            logger.error(f"Error in clock loop: {e}")
            await asyncio.sleep(60)

# ============ منوی اصلی ============
async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, edit=False):
    user = update.effective_user
    name = user.first_name if user.first_name else "کاربر"
    user_id = str(user.id)
    
    self_count = len(self_data.get(user_id, []))
    
    text = f"""
🌟 <b>ربات مدیریت حساب‌های شخصی</b>

<b>جناب {name} گرامی</b>

با سلام و احترام، به ربات مدیریت حساب‌های شخصی خود خوش آمدید.
این ربات به شما امکان مدیریت سلف‌های تلگرام را می‌دهد.

<b>تعداد سلف‌های ثبت شده: {self_count}</b>

در صورت نیاز به ایجاد سلف جدید، از دکمه زیر استفاده فرمایید.
"""
    
    keyboard = [
        [InlineKeyboardButton("🔷 ایجاد سلف جدید", callback_data="new_session")],
        [InlineKeyboardButton("📋 مشاهده سلف‌ها", callback_data="list_selfs")]
    ]
    
    if edit and update.callback_query:
        try:
            await update.callback_query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='HTML'
            )
            await update.callback_query.answer()
        except:
            pass
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
📋 <b>لیست سلف‌ها</b>

❌ <b>هیچ سلفی ثبت نشده است.</b>

لطفاً از گزینه "ایجاد سلف جدید" استفاده فرمایید.
"""
        keyboard = [
            [InlineKeyboardButton("🔷 ایجاد سلف جدید", callback_data="new_session")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
        return
    
    text = f"""
📋 <b>لیست سلف‌های ثبت شده ({len(selfs)})</b>

"""
    
    keyboard = []
    
    for i, self_account in enumerate(selfs):
        phone = self_account.get('phone', 'نامشخص')
        active_time = self_account.get('active_time', 'تنظیم نشده')
        account_name = self_account.get('account_name', 'بدون نام')
        clock_active = self_account.get('clock_active', False)
        
        clock_status = "🟢 <b>فعال</b>" if clock_active else "🔴 <b>غیرفعال</b>"
        time_display = f"{account_name} {active_time}" if active_time != 'تنظیم نشده' else f"{account_name} - ساعت تنظیم نشده"
        
        text += f"""
🔹 <b>سلف شماره {i+1}</b>
   📱 شماره: <code>{phone}</code>
   👤 نام: <b>{account_name}</b>
   🕐 ساعت: <code>{time_display}</code>
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
        await query.edit_message_text("❌ <b>سلف مورد نظر یافت نشد.</b>", parse_mode='HTML')
        return
    
    self_account = selfs[index]
    phone = self_account.get('phone', 'نامشخص')
    account_name = self_account.get('account_name', 'بدون نام')
    clock_active = self_account.get('clock_active', False)
    active_time = self_account.get('active_time', 'تنظیم نشده')
    
    time_display = f"{account_name} {active_time}" if active_time != 'تنظیم نشده' else f"{account_name} - ساعت تنظیم نشده"
    clock_status = "🟢 <b>فعال</b>" if clock_active else "🔴 <b>غیرفعال</b>"
    
    text = f"""
⚙️ <b>مدیریت سلف شماره {index + 1}</b>

📱 شماره: <code>{phone}</code>
👤 نام اکانت: <b>{account_name}</b>
🕐 ساعت: <code>{time_display}</code>
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
        await query.edit_message_text("❌ <b>سلف مورد نظر یافت نشد.</b>", parse_mode='HTML')
        return
    
    self_account = selfs[index]
    phone = self_account.get('phone', 'نامشخص')
    account_name = self_account.get('account_name', 'بدون نام')
    clock_active = self_account.get('clock_active', False)
    
    text = f"""
👤 <b>تنظیم پروفایل سلف شماره {index + 1}</b>

📱 شماره: <code>{phone}</code>
👤 نام اکانت: <b>{account_name}</b>
📊 وضعیت ساعت: {'🟢 <b>فعال</b>' if clock_active else '🔴 <b>غیرفعال</b>'}

در حال دریافت اطلاعات پروفایل...
"""
    
    await query.edit_message_text(text, parse_mode='HTML')
    
    try:
        client = TelegramClient(StringSession(self_account.get('session')), self_account.get('api_id'), self_account.get('api_hash'))
        await client.connect()
        
        if await client.is_user_authorized():
            me = await client.get_me()
            
            first_name = me.first_name if me.first_name else "ندارد"
            last_name = me.last_name if me.last_name else "ندارد"
            username = f"@{me.username}" if me.username else "ندارد"
            
            profile_text = f"""
👤 <b>پروفایل اکانت</b>

📱 شماره: <code>{phone}</code>
👤 نام: <b>{first_name}</b>
👤 نام خانوادگی: <b>{last_name}</b>
👤 یوزرنیم: <b>{username}</b>
🆔 آیدی: <code>{me.id}</code>
📊 وضعیت ساعت: {'🟢 <b>فعال</b>' if clock_active else '🔴 <b>غیرفعال</b>'}

اطلاعات پروفایل با موفقیت دریافت شد.
"""
            
            await client.disconnect()
            
            keyboard = [
                [InlineKeyboardButton("🔙 بازگشت به مدیریت", callback_data=f"manage_{index}")],
                [InlineKeyboardButton("🏠 بازگشت به منو", callback_data="back")]
            ]
            
            await query.edit_message_text(profile_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
        else:
            await client.disconnect()
            text = """
❌ <b>اکانت معتبر نیست!</b>

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
❌ <b>خطا در دریافت پروفایل!</b>

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
        await query.edit_message_text("❌ <b>سلف مورد نظر یافت نشد.</b>", parse_mode='HTML')
        return
    
    self_account = selfs[index]
    session_string = self_account.get('session')
    api_id = self_account.get('api_id')
    api_hash = self_account.get('api_hash')
    
    time_str = get_iran_time_str()
    
    # فعال کردن ساعت روی پروفایل
    result = await set_clock_on_profile(session_string, api_id, api_hash)
    
    if result:
        selfs[index]['active_time'] = time_str
        selfs[index]['clock_active'] = True
        save_data()
        
        # شروع حلقه ساعت
        if user_id not in clock_tasks or not clock_tasks[user_id]:
            clock_tasks[user_id] = True
            asyncio.create_task(clock_loop(user_id, session_string, api_id, api_hash))
        
        text = f"""
✅ <b>ساعت با موفقیت فعال شد!</b>

👤 نام اکانت: <b>{selfs[index].get('account_name', 'کاربر')}</b>
🕐 ساعت فعال: <code>{time_str}</code>

ساعت برای این سلف با موفقیت فعال گردید.
"""
    else:
        text = """
❌ <b>خطا در فعال کردن ساعت!</b>

لطفاً مطمئن شوید که اکانت معتبر است و دوباره تلاش کنید.
"""
    
    keyboard = [
        [InlineKeyboardButton("🔙 بازگشت به مدیریت", callback_data=f"manage_{index}")],
        [InlineKeyboardButton("🏠 بازگشت به منو", callback_data="back")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

# ============ غیرفعال کردن ساعت ============
async def deactivate_clock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    index = int(query.data.split('_')[2])
    
    selfs = self_data.get(user_id, [])
    if index >= len(selfs):
        await query.edit_message_text("❌ <b>سلف مورد نظر یافت نشد.</b>", parse_mode='HTML')
        return
    
    self_account = selfs[index]
    session_string = self_account.get('session')
    api_id = self_account.get('api_id')
    api_hash = self_account.get('api_hash')
    account_name = selfs[index].get('account_name', 'کاربر')
    
    # غیرفعال کردن ساعت از پروفایل
    result = await remove_clock_from_profile(session_string, api_id, api_hash)
    
    if result:
        selfs[index]['clock_active'] = False
        save_data()
        
        # متوقف کردن حلقه ساعت
        if user_id in clock_tasks:
            clock_tasks[user_id] = False
        
        text = f"""
❌ <b>ساعت با موفقیت غیرفعال شد!</b>

👤 نام اکانت: <b>{account_name}</b>

ساعت برای این سلف با موفقیت غیرفعال گردید.
"""
    else:
        text = """
❌ <b>خطا در غیرفعال کردن ساعت!</b>

لطفاً مطمئن شوید که اکانت معتبر است و دوباره تلاش کنید.
"""
    
    keyboard = [
        [InlineKeyboardButton("🔙 بازگشت به مدیریت", callback_data=f"manage_{index}")],
        [InlineKeyboardButton("🏠 بازگشت به منو", callback_data="back")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

# ============ دکمه ساخت سلف ============
async def new_session(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    await clear_user_session(user_id)
    user_sessions[user_id] = {"step": "phone"}
    
    text = """
📱 <b>مرحله اول: وارد کردن شماره تلفن</b>

لطفاً شماره تلفن مورد نظر را به همراه کد کشور وارد فرمایید.

<b>مثال:</b> <code>989123456789</code>

⚠️ <b>تذکر:</b> شماره را بدون علامت (+) وارد نمایید.
"""
    
    keyboard = [[InlineKeyboardButton("🔙 لغو و بازگشت", callback_data="back")]]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

# ============ دریافت شماره ============
async def handle_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    if user_id not in user_sessions or user_sessions[user_id].get("step") != "phone":
        await update.message.reply_text("❌ <b>لطفاً از دکمه ایجاد سلف استفاده فرمایید.</b>", parse_mode='HTML')
        return
    
    phone = re.sub(r'[^0-9+]', '', text)
    
    if not is_valid_phone(phone):
        await update.message.reply_text(
            "❌ <b>شماره تلفن نامعتبر است!</b>\n\nلطفاً شماره را به صورت صحیح وارد نمایید.\n<b>مثال:</b> <code>989123456789</code>",
            parse_mode='HTML'
        )
        return
    
    user_sessions[user_id]['phone'] = phone
    user_sessions[user_id]['step'] = "api_id"
    
    text = f"""
✅ <b>شماره تلفن با موفقیت ثبت شد.</b>

📱 شماره: <code>{phone}</code>

🔑 <b>مرحله دوم: وارد کردن API ID</b>

لطفاً API ID خود را از سایت my.telegram.org دریافت و وارد فرمایید.
"""
    
    keyboard = [[InlineKeyboardButton("🔙 لغو و بازگشت", callback_data="back")]]
    
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

# ============ دریافت API ID ============
async def handle_api_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    if user_id not in user_sessions or user_sessions[user_id].get("step") != "api_id":
        await update.message.reply_text("❌ <b>لطفاً از دکمه ایجاد سلف استفاده فرمایید.</b>", parse_mode='HTML')
        return
    
    if not text.isdigit():
        await update.message.reply_text("❌ <b>API ID باید عدد باشد.</b>\n\nلطفاً مجدداً وارد نمایید.", parse_mode='HTML')
        return
    
    user_sessions[user_id]['api_id'] = int(text)
    user_sessions[user_id]['step'] = "api_hash"
    
    text = f"""
✅ <b>API ID با موفقیت ثبت شد.</b>

🔑 API ID: <code>{text}</code>

🔐 <b>مرحله سوم: وارد کردن API Hash</b>

لطفاً API Hash خود را از سایت my.telegram.org دریافت و وارد فرمایید.
"""
    
    keyboard = [[InlineKeyboardButton("🔙 لغو و بازگشت", callback_data="back")]]
    
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

# ============ دریافت API Hash ============
async def handle_api_hash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    if user_id not in user_sessions or user_sessions[user_id].get("step") != "api_hash":
        await update.message.reply_text("❌ <b>لطفاً از دکمه ایجاد سلف استفاده فرمایید.</b>", parse_mode='HTML')
        return
    
    if len(text) < 30:
        await update.message.reply_text("❌ <b>API Hash باید حداقل 30 کاراکتر باشد.</b>\n\nلطفاً مجدداً وارد نمایید.", parse_mode='HTML')
        return
    
    user_sessions[user_id]['api_hash'] = text
    user_sessions[user_id]['step'] = "code"
    
    msg = await update.message.reply_text("⏳ <b>در حال ارسال کد تایید...</b>\n\nلطفاً چند لحظه صبر فرمایید.", parse_mode='HTML')
    
    try:
        data = user_sessions[user_id]
        phone = data['phone']
        api_id = data['api_id']
        api_hash = data['api_hash']
        
        client = TelegramClient(StringSession(), api_id, api_hash)
        
        await client.connect()
        await client.send_code_request(phone)
        
        user_sessions[user_id]['client'] = client
        user_sessions[user_id]['msg_id'] = msg.message_id
        
        text = f"""
✅ <b>کد تایید با موفقیت ارسال شد.</b>

📩 کد ۵ رقمی به شماره <code>{phone}</code> ارسال گردید.

📝 لطفاً کد دریافتی را وارد فرمایید.

<b>مثال:</b> <code>12345</code> یا <code>1.2.3.4.5</code>
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
            text=f"❌ <b>خطا در ارسال کد:</b> {str(e)[:200]}",
            parse_mode='HTML'
        )
        await clear_user_session(user_id)

# ============ دریافت کد ============
async def handle_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    raw_code = update.message.text.strip()
    
    if user_id not in user_sessions or user_sessions[user_id].get("step") != "code":
        await update.message.reply_text("❌ <b>لطفاً از دکمه ایجاد سلف استفاده فرمایید.</b>", parse_mode='HTML')
        return
    
    code = clean_code(raw_code)
    
    if not code.isdigit() or len(code) != 5:
        await update.message.reply_text(
            "❌ <b>کد باید ۵ رقم باشد.</b>\n\n<b>مثال:</b> <code>12345</code>",
            parse_mode='HTML'
        )
        return
    
    data = user_sessions[user_id]
    client = data.get('client')
    
    if not client:
        await update.message.reply_text("❌ <b>اتصال معتبر نیست.</b>\n\nلطفاً مجدداً تلاش فرمایید.", parse_mode='HTML')
        await clear_user_session(user_id)
        return
    
    try:
        phone = data['phone']
        api_id = data['api_id']
        api_hash = data['api_hash']
        
        await client.sign_in(phone, code)
        session_string = client.session.save()
        await client.disconnect()
        
        # دریافت اطلاعات اکانت
        account_name = "بدون نام"
        try:
            client2 = TelegramClient(StringSession(session_string), api_id, api_hash)
            await client2.connect()
            if await client2.is_user_authorized():
                me = await client2.get_me()
                if me and me.first_name:
                    account_name = me.first_name
                elif me and me.username:
                    account_name = me.username
            await client2.disconnect()
        except:
            account_name = "بدون نام"
        
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
✅ <b>سلف جدید با موفقیت ایجاد شد!</b>

📱 شماره: <code>{phone}</code>
👤 نام اکانت: <b>{account_name}</b>
🔑 شناسه جلسه: <code>{mask_string(session_string, 10)}</code>

سلف جدید به لیست شما اضافه گردید.
"""
        
        keyboard = [
            [InlineKeyboardButton("🔷 ایجاد سلف جدید", callback_data="new_session")],
            [InlineKeyboardButton("📋 مشاهده سلف‌ها", callback_data="list_selfs")],
            [InlineKeyboardButton("🏠 بازگشت به صفحه اصلی", callback_data="back")]
        ]
        
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
        
    except SessionPasswordNeededError:
        user_sessions[user_id]['step'] = "password"
        text = """
🔐 <b>رمز عبور دو مرحله‌ای</b>

حساب کاربری مورد نظر دارای رمز عبور دو مرحله‌ای می‌باشد.

لطفاً رمز عبور خود را وارد فرمایید.
"""
        keyboard = [[InlineKeyboardButton("🔙 لغو و بازگشت", callback_data="back")]]
        
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
        
    except PhoneCodeExpiredError:
        await client.send_code_request(phone)
        await update.message.reply_text(
            "🔄 <b>کد قبلی منقضی شده است.</b>\n\n📩 کد جدید ارسال گردید.\n\n📝 لطفاً کد جدید را وارد فرمایید:",
            parse_mode='HTML'
        )
        
    except Exception as e:
        await update.message.reply_text(
            f"❌ <b>خطا:</b> {str(e)[:200]}",
            parse_mode='HTML'
        )
        await clear_user_session(user_id)

# ============ دریافت پسورد ============
async def handle_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    password = update.message.text.strip()
    
    if user_id not in user_sessions or user_sessions[user_id].get("step") != "password":
        await update.message.reply_text("❌ <b>لطفاً از دکمه ایجاد سلف استفاده فرمایید.</b>", parse_mode='HTML')
        return
    
    data = user_sessions[user_id]
    client = data.get('client')
    
    if not client:
        await update.message.reply_text("❌ <b>اتصال معتبر نیست.</b>\n\nلطفاً مجدداً تلاش فرمایید.", parse_mode='HTML')
        await clear_user_session(user_id)
        return
    
    try:
        await client.sign_in(password=password)
        session_string = client.session.save()
        await client.disconnect()
        
        # دریافت اطلاعات اکانت
        account_name = "بدون نام"
        try:
            client2 = TelegramClient(StringSession(session_string), data['api_id'], data['api_hash'])
            await client2.connect()
            if await client2.is_user_authorized():
                me = await client2.get_me()
                if me and me.first_name:
                    account_name = me.first_name
                elif me and me.username:
                    account_name = me.username
            await client2.disconnect()
        except:
            account_name = "بدون نام"
        
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
✅ <b>سلف جدید با موفقیت ایجاد شد!</b>

📱 شماره: <code>{data['phone']}</code>
👤 نام اکانت: <b>{account_name}</b>
🔑 شناسه جلسه: <code>{mask_string(session_string, 10)}</code>

سلف جدید به لیست شما اضافه گردید.
"""
        
        keyboard = [
            [InlineKeyboardButton("🔷 ایجاد سلف جدید", callback_data="new_session")],
            [InlineKeyboardButton("📋 مشاهده سلف‌ها", callback_data="list_selfs")],
            [InlineKeyboardButton("🏠 بازگشت به صفحه اصلی", callback_data="back")]
        ]
        
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
        
    except Exception as e:
        await update.message.reply_text(
            f"❌ <b>رمز عبور اشتباه است.</b>\n\n{str(e)[:100]}",
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
    
    await update.message.reply_text("❌ <b>لطفاً از دکمه‌های منو استفاده فرمایید.</b>", parse_mode='HTML')

# ============ اجرا ============
def main():
    try:
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
        
        application.run_polling(drop_pending_updates=True)
        
    except Exception as e:
        print(f"❌ خطا: {e}")

if __name__ == "__main__":
    main()
