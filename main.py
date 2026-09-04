import logging
import re
import asyncio
import os
import json
from datetime import datetime
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
🌟 **سلام {name} عزیز**

به ربات شخصی خودت خوش اومدی.
همیشه کنارتم تا کارهاتو راه بندازی.

📊 تعداد سلف‌های ساخته شده: {self_count}

🔄 هر وقت خواستی یه سلف جدید بساز، دکمه زیر رو بزن.
"""
    
    keyboard = [
        [InlineKeyboardButton("🔷 ساخت سلف جدید", callback_data="new_session")]
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

# ============ دکمه ساخت سلف ============
async def new_session(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    await clear_user_session(user_id)
    user_sessions[user_id] = {"step": "phone"}
    
    text = """
📱 **مرحله ۱: شماره تلفن**

لطفاً شماره تلفن مورد نظر را وارد کن.

مثال: `989123456789`
(با کد کشور، بدون +)
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
        await update.message.reply_text("❌ لطفاً از دکمه ساخت سلف استفاده کن.", parse_mode='Markdown')
        return
    
    phone = re.sub(r'[^0-9+]', '', text)
    
    if not is_valid_phone(phone):
        await update.message.reply_text(
            "❌ شماره نامعتبر!\n\nمثال: `989123456789`",
            parse_mode='Markdown'
        )
        return
    
    user_sessions[user_id]['phone'] = phone
    user_sessions[user_id]['step'] = "api_id"
    
    text = f"""
✅ شماره `{phone}` ثبت شد.

🔑 **مرحله ۲: API ID**

لطفاً API ID خود را وارد کن.
(از سایت my.telegram.org دریافت کن)
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
        await update.message.reply_text("❌ لطفاً از دکمه ساخت سلف استفاده کن.", parse_mode='Markdown')
        return
    
    if not text.isdigit():
        await update.message.reply_text("❌ API ID باید عدد باشد.", parse_mode='Markdown')
        return
    
    user_sessions[user_id]['api_id'] = int(text)
    user_sessions[user_id]['step'] = "api_hash"
    
    text = f"""
✅ API ID `{text}` ثبت شد.

🔐 **مرحله ۳: API Hash**

لطفاً API Hash خود را وارد کن.
(از سایت my.telegram.org دریافت کن)
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
        await update.message.reply_text("❌ لطفاً از دکمه ساخت سلف استفاده کن.", parse_mode='Markdown')
        return
    
    if len(text) < 30:
        await update.message.reply_text("❌ API Hash باید حداقل 30 کاراکتر باشد.", parse_mode='Markdown')
        return
    
    user_sessions[user_id]['api_hash'] = text
    user_sessions[user_id]['step'] = "code"
    
    msg = await update.message.reply_text("⏳ در حال ارسال کد تایید...", parse_mode='Markdown')
    
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
✅ کد تایید به شماره `{phone}` ارسال شد.

📝 لطفاً کد ۵ رقمی دریافت شده را وارد کن.

مثال: `12345` یا `1.2.3.4.5`
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
            text=f"❌ خطا در ارسال کد: {str(e)[:200]}",
            parse_mode='Markdown'
        )
        await clear_user_session(user_id)

# ============ دریافت کد ============
async def handle_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    raw_code = update.message.text.strip()
    
    if user_id not in user_sessions or user_sessions[user_id].get("step") != "code":
        await update.message.reply_text("❌ لطفاً از دکمه ساخت سلف استفاده کن.", parse_mode='Markdown')
        return
    
    code = clean_code(raw_code)
    
    if not code.isdigit() or len(code) != 5:
        await update.message.reply_text(
            "❌ کد باید ۵ رقم باشد.\n\nمثال: `12345`",
            parse_mode='Markdown'
        )
        return
    
    data = user_sessions[user_id]
    client = data.get('client')
    
    if not client:
        await update.message.reply_text("❌ اتصال معتبر نیست. لطفاً دوباره تلاش کن.", parse_mode='Markdown')
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
        
        self_data[user_id_str].append({
            "session": session_string,
            "phone": phone,
            "api_id": api_id,
            "api_hash": api_hash,
            "active": True,
            "created": datetime.now().isoformat()
        })
        save_data()
        
        await clear_user_session(user_id)
        
        text = f"""
✅ **سلف جدید ساخته شد!**

📱 شماره: `{phone}`
🔑 شناسه جلسه: `{mask_string(session_string, 10)}`

🎯 سلف جدید به لیست اضافه شد.
"""
        
        keyboard = [
            [InlineKeyboardButton("🔷 ساخت سلف جدید", callback_data="new_session")],
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
🔐 **رمز عبور دو مرحله‌ای**

حساب کاربری رمز عبور دو مرحله‌ای دارد.

لطفاً رمز عبور خود را وارد کن.
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
            "🔄 کد قبلی منقضی شد. کد جدید ارسال گردید.\n\n📝 لطفاً کد جدید را وارد کن:",
            parse_mode='Markdown'
        )
        
    except Exception as e:
        await update.message.reply_text(
            f"❌ خطا: {str(e)[:200]}",
            parse_mode='Markdown'
        )
        await clear_user_session(user_id)

# ============ دریافت پسورد ============
async def handle_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    password = update.message.text.strip()
    
    if user_id not in user_sessions or user_sessions[user_id].get("step") != "password":
        await update.message.reply_text("❌ لطفاً از دکمه ساخت سلف استفاده کن.", parse_mode='Markdown')
        return
    
    data = user_sessions[user_id]
    client = data.get('client')
    
    if not client:
        await update.message.reply_text("❌ اتصال معتبر نیست. لطفاً دوباره تلاش کن.", parse_mode='Markdown')
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
        
        self_data[user_id_str].append({
            "session": session_string,
            "phone": data['phone'],
            "api_id": data['api_id'],
            "api_hash": data['api_hash'],
            "active": True,
            "created": datetime.now().isoformat()
        })
        save_data()
        
        await clear_user_session(user_id)
        
        text = f"""
✅ **سلف جدید ساخته شد!**

📱 شماره: `{data['phone']}`
🔑 شناسه جلسه: `{mask_string(session_string, 10)}`

🎯 سلف جدید به لیست اضافه شد.
"""
        
        keyboard = [
            [InlineKeyboardButton("🔷 ساخت سلف جدید", callback_data="new_session")],
            [InlineKeyboardButton("🏠 بازگشت به صفحه اصلی", callback_data="back")]
        ]
        
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        await update.message.reply_text(
            f"❌ رمز عبور اشتباه است.\n\n{str(e)[:100]}\n\n📝 لطفاً دوباره وارد کن:",
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
    
    await update.message.reply_text("❌ لطفاً از دکمه ساخت سلف استفاده کن.", parse_mode='Markdown')

# ============ اجرا ============
def main():
    try:
        # حذف webhook قبل از شروع
        delete_webhook()
        
        print("=" * 60)
        print("🌟 ربات شخصی")
        print("=" * 60)
        print(f"📌 توکن: {TOKEN[:10]}...{TOKEN[-5:]}")
        print("=" * 60)
        
        # ساخت اپلیکیشن با تنظیمات ویژه برای جلوگیری از Conflict
        application = Application.builder().token(TOKEN).build()
        
        # دکمه‌ها
        application.add_handler(CallbackQueryHandler(new_session, pattern="^new_session$"))
        application.add_handler(CallbackQueryHandler(back_to_menu, pattern="^back$"))
        
        # دستور start
        application.add_handler(CommandHandler("start", start))
        
        # هندلر پیام‌ها
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_messages))
        
        print("✅ ربات با موفقیت راه‌اندازی شد.")
        print("💡 برای شروع از /start استفاده کن.")
        print("=" * 60)
        
        # اجرا با تنظیمات جلوگیری از Conflict
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,
            timeout=30,
            read_timeout=30,
            write_timeout=30,
            pool_timeout=30
        )
        
    except Exception as e:
        print(f"❌ خطا: {e}")

if __name__ == "__main__":
    main()
