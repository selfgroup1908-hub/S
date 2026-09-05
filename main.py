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
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError, PhoneCodeExpiredError, FloodWaitError
from telethon.tl.functions.account import UpdateProfileRequest, UpdateUsernameRequest
from telethon.tl.functions.photos import UploadProfilePhotoRequest, DeletePhotosRequest
from telethon.tl.types import InputPhoto, MessageMediaPhoto, MessageMediaDocument
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
profile_tasks = {}

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
    """دریافت زمان ایران با ثانیه"""
    now = datetime.now(timezone.utc)
    iran_time = now + timedelta(hours=3, minutes=30)
    return iran_time

def get_iran_time_str():
    """دریافت زمان ایران به صورت ساعت:دقیقه"""
    return get_iran_time().strftime("%H:%M")

def get_iran_full_time():
    """دریافت زمان کامل ایران با ثانیه"""
    return get_iran_time().strftime("%H:%M:%S")

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
    """گذاشتن ساعت روی اسم اکانت - دقیق و هماهنگ با زمان حال"""
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
        
        # دریافت زمان دقیق ایران با ثانیه
        time_str = get_iran_time_str()
        
        # حذف ساعت قبلی از اسم (با فرمت HH:MM)
        clean_name = re.sub(r'\s*\d{2}:\d{2}$', '', current_name).strip()
        new_name = f"{clean_name} {time_str}".strip()
        
        # اگر اسم تغییر کرده، آپدیت کن
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
            except:
                await client.disconnect()
                return False
        
        await client.disconnect()
        return True
        
    except Exception as e:
        logger.error(f"Error in remove_clock_from_profile: {e}")
        return False

async def clock_loop(user_id, session_string, api_id, api_hash):
    """حلقه برای بروزرسانی ساعت هر ثانیه - دقیق و هماهنگ"""
    last_minute = None
    while True:
        try:
            if user_id in clock_tasks and not clock_tasks[user_id]:
                break
            
            # دریافت دقیقه فعلی
            current_minute = get_iran_time().strftime("%H:%M")
            
            # فقط در صورتی که دقیقه تغییر کرده، آپدیت کن
            if current_minute != last_minute:
                await set_clock_on_profile(session_string, api_id, api_hash)
                last_minute = current_minute
            
            # هر 1 ثانیه چک کن
            await asyncio.sleep(1)
            
        except Exception as e:
            logger.error(f"Error in clock loop: {e}")
            await asyncio.sleep(1)

# ============ توابع تنظیم پروفایل ============
async def set_profile_picture(session_string, api_id, api_hash, file_path, count):
    """تنظیم پروفایل با محدودیت زمانی هوشمند"""
    try:
        client = TelegramClient(StringSession(session_string), api_id, api_hash)
        await client.connect()
        
        if not await client.is_user_authorized():
            await client.disconnect()
            return False, "اکانت معتبر نیست!"
        
        success_count = 0
        fail_count = 0
        
        for i in range(count):
            try:
                await client(UploadProfilePhotoRequest(
                    file=await client.upload_file(file_path)
                ))
                success_count += 1
                
                # محدودیت زمانی هوشمند
                if (i + 1) % 10 == 0 and i + 1 < count:
                    await asyncio.sleep(60)
                else:
                    await asyncio.sleep(5)
                    
            except FloodWaitError as e:
                wait_time = min(e.seconds, 300)
                await asyncio.sleep(wait_time + 5)
                fail_count += 1
                
            except Exception as e:
                logger.error(f"Error setting profile: {e}")
                fail_count += 1
                await asyncio.sleep(10)
        
        await client.disconnect()
        
        if success_count > 0:
            return True, f"✅ {success_count} بار با موفقیت تنظیم شد.\n❌ {fail_count} بار ناموفق."
        else:
            return False, "❌ هیچکدام تنظیم نشد!"
        
    except Exception as e:
        logger.error(f"Error in set_profile_picture: {e}")
        return False, f"❌ خطا: {str(e)[:200]}"

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

لطفاً از منوی زیر انتخاب فرمایید:
"""
    
    keyboard = [
        [InlineKeyboardButton("🔷 ایجاد سلف جدید", callback_data="new_session")],
        [InlineKeyboardButton("📋 لیست سلف‌ها", callback_data="list_selfs")],
        [InlineKeyboardButton("🔄 بروزرسانی ساعت", callback_data="refresh_clock")],
        [InlineKeyboardButton("⏰ مدیریت ساعت", callback_data="manage_clock")]
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

# ============ مدیریت ساعت ============
async def manage_clock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    selfs = self_data.get(user_id, [])
    
    if not selfs:
        text = """
⏰ <b>مدیریت ساعت</b>

❌ <b>هیچ سلفی ثبت نشده است.</b>

لطفاً ابتدا یک سلف ایجاد کنید.
"""
        keyboard = [
            [InlineKeyboardButton("🔷 ایجاد سلف جدید", callback_data="new_session")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
        return
    
    text = f"""
⏰ <b>مدیریت ساعت</b>

لطفاً سلف مورد نظر برای مدیریت ساعت را انتخاب کنید:
"""
    
    keyboard = []
    for i, self_account in enumerate(selfs):
        phone = self_account.get('phone', 'نامشخص')
        account_name = self_account.get('account_name', 'بدون نام')
        clock_active = self_account.get('clock_active', False)
        status = "🟢 فعال" if clock_active else "🔴 غیرفعال"
        
        keyboard.append([InlineKeyboardButton(f"{i+1}. {account_name} - {status}", callback_data=f"clock_manage_{i}")])
    
    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="back")])
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

# ============ مدیریت ساعت یک سلف ============
async def clock_manage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    index = int(query.data.split('_')[2])
    
    selfs = self_data.get(user_id, [])
    if index >= len(selfs):
        await query.edit_message_text("❌ <b>سلف مورد نظر یافت نشد.</b>", parse_mode='HTML')
        return
    
    self_account = selfs[index]
    phone = self_account.get('phone', 'نامشخص')
    account_name = self_account.get('account_name', 'بدون نام')
    clock_active = self_account.get('clock_active', False)
    active_time = self_account.get('active_time', 'تنظیم نشده')
    
    status = "🟢 <b>فعال</b>" if clock_active else "🔴 <b>غیرفعال</b>"
    
    text = f"""
⏰ <b>مدیریت ساعت - {account_name}</b>

📱 شماره: <code>{phone}</code>
👤 نام: <b>{account_name}</b>
🕐 ساعت فعلی: <code>{active_time}</code>
📊 وضعیت: {status}

لطفاً یکی از گزینه‌های زیر را انتخاب کنید:
"""
    
    keyboard = []
    if clock_active:
        keyboard.append([InlineKeyboardButton("❌ غیرفعال کردن ساعت", callback_data=f"deactivate_clock_{index}")])
    else:
        keyboard.append([InlineKeyboardButton("✅ فعال کردن ساعت", callback_data=f"activate_clock_{index}")])
    
    keyboard.append([InlineKeyboardButton("🔄 بروزرسانی ساعت", callback_data=f"refresh_clock_{index}")])
    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="manage_clock")])
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

# ============ بروزرسانی ساعت ============
async def refresh_clock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    
    # اگر اندیس داره، برای یک سلف خاص
    if query.data.startswith("refresh_clock_"):
        index = int(query.data.split('_')[2])
        selfs = self_data.get(user_id, [])
        if index >= len(selfs):
            await query.edit_message_text("❌ <b>سلف مورد نظر یافت نشد.</b>", parse_mode='HTML')
            return
        
        self_account = selfs[index]
        session_string = self_account.get('session')
        api_id = self_account.get('api_id')
        api_hash = self_account.get('api_hash')
        
        result = await set_clock_on_profile(session_string, api_id, api_hash)
        
        if result:
            time_str = get_iran_time_str()
            selfs[index]['active_time'] = time_str
            save_data()
            text = f"✅ <b>ساعت با موفقیت بروزرسانی شد!</b>\n🕐 زمان: <code>{time_str}</code>"
        else:
            text = "❌ <b>خطا در بروزرسانی ساعت!</b>"
        
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data=f"clock_manage_{index}")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
        return
    
    # بروزرسانی همه سلف‌ها
    selfs = self_data.get(user_id, [])
    if not selfs:
        await query.edit_message_text("❌ <b>هیچ سلفی ثبت نشده است.</b>", parse_mode='HTML')
        return
    
    await query.edit_message_text("⏳ <b>در حال بروزرسانی ساعت همه سلف‌ها...</b>", parse_mode='HTML')
    
    success_count = 0
    for self_account in selfs:
        try:
            result = await set_clock_on_profile(
                self_account.get('session'),
                self_account.get('api_id'),
                self_account.get('api_hash')
            )
            if result:
                success_count += 1
        except:
            pass
    
    text = f"""
✅ <b>بروزرسانی ساعت انجام شد!</b>

تعداد سلف‌های بروزرسانی شده: <b>{success_count}</b>
تعداد کل سلف‌ها: <b>{len(selfs)}</b>
"""
    
    keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="back")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

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
        [InlineKeyboardButton("👤 تنظیم پروفایل جدید", callback_data=f"new_profile_{index}")],
        [InlineKeyboardButton("📸 ارسال چند پروفایل", callback_data=f"multi_profile_{index}")]
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

# ============ تنظیم پروفایل جدید ============
async def new_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    index = int(query.data.split('_')[2])
    
    selfs = self_data.get(user_id, [])
    if index >= len(selfs):
        await query.edit_message_text("❌ <b>سلف مورد نظر یافت نشد.</b>", parse_mode='HTML')
        return
    
    context.user_data['profile_index'] = index
    context.user_data['profile_step'] = 'waiting_media'
    context.user_data['profile_files'] = []
    
    text = """
📸 <b>تنظیم پروفایل جدید</b>

لطفاً عکس یا فیلمی که می‌خواهید به عنوان پروفایل تنظیم شود را ارسال کنید.

⚠️ <b>نکات مهم:</b>
• می‌توانید چندین عکس و فیلم ارسال کنید
• پس از ارسال همه، دکمه "اتمام ارسال" را بزنید
• برای عکس‌ها، سایز مناسب توصیه می‌شود

برای اتمام ارسال، دکمه زیر را بزنید.
"""
    
    keyboard = [
        [InlineKeyboardButton("✅ اتمام ارسال", callback_data=f"done_profile_{index}")],
        [InlineKeyboardButton("🔙 لغو و بازگشت", callback_data=f"manage_{index}")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

# ============ دریافت مدیا برای پروفایل ============
async def handle_profile_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if 'profile_step' not in context.user_data or context.user_data['profile_step'] != 'waiting_media':
        await update.message.reply_text("❌ <b>لطفاً از دکمه تنظیم پروفایل استفاده کنید.</b>", parse_mode='HTML')
        return
    
    # دریافت فایل
    if update.message.photo:
        file = await update.message.photo[-1].get_file()
        file_ext = ".jpg"
    elif update.message.document:
        file = await update.message.document.get_file()
        file_ext = os.path.splitext(update.message.document.file_name)[1] if update.message.document.file_name else ".jpg"
    elif update.message.video:
        file = await update.message.video.get_file()
        file_ext = ".mp4"
    else:
        await update.message.reply_text("❌ <b>لطفاً فقط عکس یا فیلم ارسال کنید!</b>", parse_mode='HTML')
        return
    
    # ذخیره فایل
    file_path = f"temp_profile_{user_id}_{len(context.user_data.get('profile_files', []))}{file_ext}"
    await file.download_to_drive(file_path)
    
    if 'profile_files' not in context.user_data:
        context.user_data['profile_files'] = []
    context.user_data['profile_files'].append(file_path)
    
    count = len(context.user_data['profile_files'])
    
    await update.message.reply_text(
        f"✅ <b>فایل {count} با موفقیت دریافت شد!</b>\n\nلطفاً فایل بعدی را ارسال کنید یا دکمه اتمام را بزنید.",
        parse_mode='HTML'
    )

# ============ اتمام ارسال پروفایل ============
async def done_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    index = int(query.data.split('_')[2])
    
    selfs = self_data.get(user_id, [])
    if index >= len(selfs):
        await query.edit_message_text("❌ <b>سلف مورد نظر یافت نشد.</b>", parse_mode='HTML')
        return
    
    files = context.user_data.get('profile_files', [])
    
    if not files:
        await query.edit_message_text("❌ <b>هیچ فایلی ارسال نشده است!</b>\n\nلطفاً حداقل یک عکس یا فیلم ارسال کنید.", parse_mode='HTML')
        return
    
    text = f"""
✅ <b>{len(files)} فایل با موفقیت دریافت شد!</b>

🔢 لطفاً تعداد دفعاتی که می‌خواهید این پروفایل‌ها برای اکانت شما تنظیم شود را وارد کنید.

<b>حداکثر: 100 بار برای هر فایل</b>
<b>حداقل: 1 بار</b>

⚠️ توجه: بین هر تنظیم، محدودیت‌های زمانی رعایت خواهد شد.
"""
    
    context.user_data['profile_step'] = 'waiting_count'
    
    keyboard = [[InlineKeyboardButton("🔙 لغو و بازگشت", callback_data=f"manage_{index}")]]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

# ============ دریافت تعداد دفعات ============
async def handle_profile_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if 'profile_step' not in context.user_data or context.user_data['profile_step'] != 'waiting_count':
        await update.message.reply_text("❌ <b>لطفاً از دکمه تنظیم پروفایل استفاده کنید.</b>", parse_mode='HTML')
        return
    
    try:
        count = int(update.message.text.strip())
        if count < 1 or count > 100:
            await update.message.reply_text("❌ <b>تعداد باید بین 1 تا 100 باشد!</b>\n\nلطفاً مجدداً وارد کنید:", parse_mode='HTML')
            return
    except:
        await update.message.reply_text("❌ <b>لطفاً یک عدد معتبر وارد کنید!</b>", parse_mode='HTML')
        return
    
    index = context.user_data['profile_index']
    files = context.user_data.get('profile_files', [])
    
    selfs = self_data.get(user_id, [])
    if index >= len(selfs):
        await update.message.reply_text("❌ <b>سلف مورد نظر یافت نشد!</b>", parse_mode='HTML')
        return
    
    self_account = selfs[index]
    session_string = self_account.get('session')
    api_id = self_account.get('api_id')
    api_hash = self_account.get('api_hash')
    account_name = self_account.get('account_name', 'کاربر')
    
    await update.message.reply_text(
        f"""
🚀 <b>شروع تنظیم پروفایل</b>

👤 نام اکانت: <b>{account_name}</b>
📁 تعداد فایل‌ها: <b>{len(files)}</b>
🔢 تعداد دفعات هر فایل: <b>{count}</b>
📊 مجموع تنظیمات: <b>{len(files) * count}</b>

⏳ لطفاً صبر کنید...
<b>⚠️ این عملیات ممکن است چند دقیقه طول بکشد.</b>
""",
        parse_mode='HTML'
    )
    
    total_success = 0
    total_fail = 0
    
    for file_path in files:
        success, message = await set_profile_picture(session_string, api_id, api_hash, file_path, count)
        if success:
            total_success += count
        else:
            total_fail += count
        # حذف فایل موقت
        try:
            os.remove(file_path)
        except:
            pass
    
    # پاک کردن داده‌های موقت
    if 'profile_files' in context.user_data:
        del context.user_data['profile_files']
    if 'profile_step' in context.user_data:
        del context.user_data['profile_step']
    if 'profile_index' in context.user_data:
        del context.user_data['profile_index']
    
    if total_success > 0:
        text = f"""
✅ <b>تنظیم پروفایل با موفقیت انجام شد!</b>

👤 نام اکانت: <b>{account_name}</b>
📊 نتیجه:
• ✅ موفق: <b>{total_success}</b>
• ❌ ناموفق: <b>{total_fail}</b>

پروفایل با موفقیت تنظیم گردید.
"""
    else:
        text = f"""
❌ <b>خطا در تنظیم پروفایل!</b>

👤 نام اکانت: <b>{account_name}</b>
📊 نتیجه: همه تنظیمات ناموفق بود.

لطفاً دوباره تلاش کنید.
"""
    
    keyboard = [
        [InlineKeyboardButton("🔙 بازگشت به مدیریت", callback_data=f"manage_{index}")],
        [InlineKeyboardButton("🏠 بازگشت به منو", callback_data="back")]
    ]
    
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

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

ساعت هر دقیقه به‌طور خودکار بروزرسانی می‌شود.
"""
    else:
        text = """
❌ <b>خطا در فعال کردن ساعت!</b>

لطفاً مطمئن شوید که اکانت معتبر است و دوباره تلاش کنید.
"""
    
    keyboard = [
        [InlineKeyboardButton("🔙 بازگشت", callback_data=f"manage_{index}")],
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
    
    result = await remove_clock_from_profile(session_string, api_id, api_hash)
    
    if result:
        selfs[index]['clock_active'] = False
        save_data()
        
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
        [InlineKeyboardButton("🔙 بازگشت", callback_data=f"manage_{index}")],
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
    
    # پاک کردن داده‌های موقت پروفایل
    if 'profile_files' in context.user_data:
        for file_path in context.user_data['profile_files']:
            try:
                os.remove(file_path)
            except:
                pass
        del context.user_data['profile_files']
    if 'profile_step' in context.user_data:
        del context.user_data['profile_step']
    if 'profile_index' in context.user_data:
        del context.user_data['profile_index']
    
    await main_menu(update, context, edit=True)

# ============ دستور start ============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await main_menu(update, context)

# ============ هندلر پیام‌ها ============
async def handle_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # بررسی مرحله تنظیم پروفایل
    if 'profile_step' in context.user_data:
        step = context.user_data['profile_step']
        if step == 'waiting_media':
            await handle_profile_media(update, context)
            return
        elif step == 'waiting_count':
            await handle_profile_count(update, context)
            return
    
    # مراحل ساخت سلف
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
        application.add_handler(CallbackQueryHandler(manage_clock, pattern="^manage_clock$"))
        application.add_handler(CallbackQueryHandler(clock_manage, pattern="^clock_manage_"))
        application.add_handler(CallbackQueryHandler(refresh_clock, pattern="^refresh_clock"))
        application.add_handler(CallbackQueryHandler(new_profile, pattern="^new_profile_"))
        application.add_handler(CallbackQueryHandler(done_profile, pattern="^done_profile_"))
        application.add_handler(CallbackQueryHandler(activate_clock, pattern="^activate_clock_"))
        application.add_handler(CallbackQueryHandler(deactivate_clock, pattern="^deactivate_clock_"))
        application.add_handler(CallbackQueryHandler(back_to_menu, pattern="^back$"))
        
        application.add_handler(CommandHandler("start", start))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND | filters.PHOTO | filters.VIDEO | filters.Document.ALL, handle_messages))
        
        print("✅ ربات با موفقیت راه‌اندازی شد.")
        print("💡 برای شروع از /start استفاده فرمایید.")
        print("=" * 60)
        
        application.run_polling(drop_pending_updates=True)
        
    except Exception as e:
        print(f"❌ خطا: {e}")

if __name__ == "__main__":
    main()
