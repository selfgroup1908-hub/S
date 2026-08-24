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
TOKEN = "8954675509:AAGkdKpnKjoPPf-irMnCHZyswmqJCoIruiI"

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

user_sessions = {}
tabchi_data = {}
ad_data = {}

# ============ فایل ذخیره اطلاعات ============
DATA_FILE = "tabchis.json"

def load_data():
    global tabchi_data
    try:
        with open(DATA_FILE, 'r') as f:
            tabchi_data = json.load(f)
    except:
        tabchi_data = {}

def save_data():
    with open(DATA_FILE, 'w') as f:
        json.dump(tabchi_data, f)

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
    mention = f"@{user.username}" if user.username else user.first_name
    user_id = str(user.id)
    
    tabchi_count = len(tabchi_data.get(user_id, []))
    
    text = f"""
🤖 **ربات مدیریت تبلیغات تلگرام**

👋 سلام *{mention}* گرامی

به ربات مدیریت تبلیغات تلگرام خوش آمدید.

📊 *آمار حساب کاربری شما:*
🔹 تعداد تبچی‌های فعال: *{tabchi_count}*

📌 لطفاً یکی از گزینه‌های زیر را انتخاب کنید:
"""
    
    keyboard = [
        [InlineKeyboardButton("➕ ایجاد تبچی جدید", callback_data="new_session")],
        [
            InlineKeyboardButton("📋 لیست تبچی‌ها", callback_data="list_tabchis"),
            InlineKeyboardButton("📤 ارسال تبلیغ", callback_data="manual_ad")
        ],
        [
            InlineKeyboardButton("👤 شناسایی مالک گروه", callback_data="show_owners")
        ]
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

# ============ دکمه ساخت تبچی ============
async def new_session(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    await clear_user_session(user_id)
    user_sessions[user_id] = {"step": "phone"}
    
    text = """
➕ *ایجاد تبچی جدید - مرحله ۱*

📱 لطفاً *شماره تلفن* را وارد کنید.

📌 *مثال:* `989123456789`
(با کد کشور، بدون علامت +)
"""
    
    keyboard = [[InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back")]]
    
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
        await update.message.reply_text("❌ لطفاً از دکمه ساخت تبچی استفاده کنید.", parse_mode='Markdown')
        return
    
    phone = re.sub(r'[^0-9+]', '', text)
    
    if not is_valid_phone(phone):
        await update.message.reply_text(
            "❌ شماره نامعتبر!\n\n📌 مثال: `989123456789`",
            parse_mode='Markdown'
        )
        return
    
    user_sessions[user_id]['phone'] = phone
    user_sessions[user_id]['step'] = "api_id"
    
    text = f"""
✅ شماره `{phone}` با موفقیت ثبت شد.

🔑 *مرحله ۲:* لطفاً *API ID* را وارد کنید.

💡 از سایت my.telegram.org دریافت کنید.
"""
    
    keyboard = [[InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back")]]
    
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
        await update.message.reply_text("❌ لطفاً از دکمه ساخت تبچی استفاده کنید.", parse_mode='Markdown')
        return
    
    if not text.isdigit():
        await update.message.reply_text("❌ API ID باید عدد باشد.", parse_mode='Markdown')
        return
    
    user_sessions[user_id]['api_id'] = int(text)
    user_sessions[user_id]['step'] = "api_hash"
    
    text = f"""
✅ API ID `{text}` با موفقیت ثبت شد.

🔐 *مرحله ۳:* لطفاً *API Hash* را وارد کنید.

💡 از سایت my.telegram.org دریافت کنید.
"""
    
    keyboard = [[InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back")]]
    
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
        await update.message.reply_text("❌ لطفاً از دکمه ساخت تبچی استفاده کنید.", parse_mode='Markdown')
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

📝 لطفاً کد ۵ رقمی دریافت شده را وارد کنید.

📌 *مثال:* `12345` یا `1.2.3.4.5`
"""
        
        keyboard = [[InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back")]]
        
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
        await update.message.reply_text("❌ لطفاً از دکمه ساخت تبچی استفاده کنید.", parse_mode='Markdown')
        return
    
    code = clean_code(raw_code)
    
    if not code.isdigit() or len(code) != 5:
        await update.message.reply_text(
            "❌ کد باید ۵ رقم باشد.\n\n📌 مثال: `12345`",
            parse_mode='Markdown'
        )
        return
    
    data = user_sessions[user_id]
    client = data.get('client')
    
    if not client:
        await update.message.reply_text("❌ اتصال معتبر نیست. لطفاً دوباره تلاش کنید.", parse_mode='Markdown')
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
        if user_id_str not in tabchi_data:
            tabchi_data[user_id_str] = []
        
        tabchi_data[user_id_str].append({
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
✅ *تبچی با موفقیت ایجاد شد!*

📱 *شماره:* `{phone}`
🔑 *شناسه جلسه:* `{mask_string(session_string, 10)}`

🎯 تبچی به لیست شما اضافه شد.
"""
        
        keyboard = [
            [InlineKeyboardButton("➕ ایجاد تبچی جدید", callback_data="new_session")],
            [InlineKeyboardButton("📋 لیست تبچی‌ها", callback_data="list_tabchis")],
            [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back")]
        ]
        
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    except SessionPasswordNeededError:
        user_sessions[user_id]['step'] = "password"
        text = """
🔐 *حساب کاربری شما دارای رمز عبور دو مرحله‌ای است.*

📝 لطفاً *رمز عبور* خود را وارد کنید.
"""
        keyboard = [[InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back")]]
        
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    except PhoneCodeExpiredError:
        await client.send_code_request(phone)
        await update.message.reply_text(
            "🔄 کد قبلی منقضی شد. کد جدید ارسال گردید.\n\n📝 لطفاً کد جدید را وارد کنید:",
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
        await update.message.reply_text("❌ لطفاً از دکمه ساخت تبچی استفاده کنید.", parse_mode='Markdown')
        return
    
    data = user_sessions[user_id]
    client = data.get('client')
    
    if not client:
        await update.message.reply_text("❌ اتصال معتبر نیست. لطفاً دوباره تلاش کنید.", parse_mode='Markdown')
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
        if user_id_str not in tabchi_data:
            tabchi_data[user_id_str] = []
        
        tabchi_data[user_id_str].append({
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
✅ *تبچی با موفقیت ایجاد شد!*

📱 *شماره:* `{data['phone']}`
🔑 *شناسه جلسه:* `{mask_string(session_string, 10)}`

🎯 تبچی به لیست شما اضافه شد.
"""
        
        keyboard = [
            [InlineKeyboardButton("➕ ایجاد تبچی جدید", callback_data="new_session")],
            [InlineKeyboardButton("📋 لیست تبچی‌ها", callback_data="list_tabchis")],
            [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back")]
        ]
        
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        await update.message.reply_text(
            f"❌ رمز عبور اشتباه است.\n\n{str(e)[:100]}\n\n📝 لطفاً دوباره وارد کنید:",
            parse_mode='Markdown'
        )

# ============ ارسال تبلیغ ============
async def manual_ad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    tabchis = tabchi_data.get(user_id, [])
    active_tabchis = [t for t in tabchis if t.get('active', True)]
    
    if not active_tabchis:
        text = """
❌ *شما هیچ تبچی فعالی ندارید.*

🔑 لطفاً ابتدا یک تبچی ایجاد کنید.
"""
        keyboard = [[InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        return
    
    ad_data[query.from_user.id] = {"links": [], "step": "link", "mode": "ad"}
    
    text = """
📤 *ارسال تبلیغ - مرحله ۱*

📎 لطفاً لینک گروه مورد نظر را ارسال کنید.

💡 می‌توانید *چندین لینک* ارسال کنید.
✅ پس از اتمام، دکمه زیر را فشار دهید.

📌 *مثال:*
`https://t.me/your_group`
"""
    
    keyboard = [
        [InlineKeyboardButton("✅ اتمام ارسال لینک‌ها", callback_data="done_links")]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

# ============ دریافت لینک تبلیغ ============
async def handle_ad_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    if user_id not in ad_data or ad_data[user_id].get("step") != "link":
        await update.message.reply_text("❌ لطفاً از دکمه ارسال تبلیغ استفاده کنید.", parse_mode='Markdown')
        return
    
    if not text.startswith("https://t.me/") and not text.startswith("t.me/"):
        await update.message.reply_text(
            "❌ لینک نامعتبر است.\n\n📌 مثال: `https://t.me/your_group`",
            parse_mode='Markdown'
        )
        return
    
    ad_data[user_id]["links"].append(text)
    
    await update.message.reply_text(
        f"✅ لینک با موفقیت دریافت شد.\n\n📊 تعداد لینک‌ها: *{len(ad_data[user_id]['links'])}*",
        parse_mode='Markdown'
    )

# ============ اتمام لینک‌ها ============
async def done_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if user_id not in ad_data:
        await query.edit_message_text("❌ خطا! لطفاً دوباره شروع کنید.", parse_mode='Markdown')
        return
    
    links = ad_data[user_id].get("links", [])
    
    if not links:
        text = """
❌ *هیچ لینکی وارد نشده است.*

📌 لطفاً حداقل یک لینک گروه ارسال کنید.
"""
        keyboard = [[InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        return
    
    ad_data[user_id]["step"] = "text"
    
    text = f"""
✅ *{len(links)} لینک با موفقیت ذخیره شد.*

🔗 *لینک‌های ثبت شده:*
{chr(10).join([f'• {l}' for l in links])}

📤 *مرحله ۲:*
📝 لطفاً *متن تبلیغی* خود را ارسال کنید.
"""
    
    keyboard = [[InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back")]]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

# ============ دریافت متن تبلیغ ============
async def handle_ad_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    if user_id not in ad_data or ad_data[user_id].get("step") != "text":
        await update.message.reply_text("❌ لطفاً از دکمه ارسال تبلیغ استفاده کنید.", parse_mode='Markdown')
        return
    
    if not text:
        await update.message.reply_text("❌ متن تبلیغ نمی‌تواند خالی باشد.", parse_mode='Markdown')
        return
    
    ad_data[user_id]["text"] = text
    
    await start_sending_ad(update, context, user_id)

# ============ شروع ارسال تبلیغ ============
async def start_sending_ad(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id):
    data = ad_data.get(user_id, {})
    links = data.get("links", [])
    ad_text = data.get("text", "")
    
    user_id_str = str(user_id)
    tabchis = tabchi_data.get(user_id_str, [])
    active_tabchis = [t for t in tabchis if t.get('active', True)]
    
    await update.message.reply_text(
        f"""
🚀 *شروع ارسال تبلیغ*

📊 *آمار:*
• تعداد تبچی‌ها: *{len(active_tabchis)}*
• تعداد گروه‌ها: *{len(links)}*

⏳ در حال ارسال...
""",
        parse_mode='Markdown'
    )
    
    success_count = 0
    fail_count = 0
    
    for tabchi in active_tabchis:
        try:
            client = TelegramClient(
                tabchi.get('session'),
                tabchi.get('api_id'),
                tabchi.get('api_hash')
            )
            await client.connect()
            
            if not await client.is_user_authorized():
                continue
            
            for link in links:
                try:
                    group = await client.get_entity(link)
                    await client.join_channel(group)
                    await client.send_message(group, ad_text)
                    success_count += 1
                    await asyncio.sleep(2)
                except Exception as e:
                    fail_count += 1
                    logger.error(f"Error in group {link}: {e}")
            
            await client.disconnect()
            
        except Exception as e:
            logger.error(f"Error with tabchi: {e}")
    
    if user_id in ad_data:
        del ad_data[user_id]
    
    await update.message.reply_text(
        f"""
✅ *ارسال تبلیغ با موفقیت انجام شد.*

📊 *نتیجه نهایی:*
• ✅ موفق: *{success_count}*
• ❌ ناموفق: *{fail_count}*

🔥 برای ارسال تبلیغ جدید از منوی اصلی استفاده کنید.
""",
        parse_mode='Markdown'
    )

# ============ شناسایی مالک گروه ============
async def show_owners(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    tabchis = tabchi_data.get(user_id, [])
    active_tabchis = [t for t in tabchis if t.get('active', True)]
    
    if not active_tabchis:
        text = """
👤 *شناسایی مالک گروه*

❌ شما هیچ تبچی فعالی ندارید.

🔑 لطفاً ابتدا یک تبچی ایجاد کنید.
"""
        keyboard = [[InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        return
    
    ad_data[query.from_user.id] = {"mode": "owner", "step": "link"}
    
    text = """
👤 *شناسایی مالک گروه*

📎 لطفاً لینک گروه مورد نظر را ارسال کنید.

📌 *مثال:*
`https://t.me/your_group`
"""
    
    keyboard = [[InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back")]]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

# ============ دریافت لینک مالک ============
async def handle_owner_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    link = update.message.text.strip()
    
    if user_id not in ad_data or ad_data[user_id].get("mode") != "owner":
        await update.message.reply_text("❌ لطفاً از دکمه شناسایی مالک استفاده کنید.", parse_mode='Markdown')
        return
    
    if not link.startswith("https://t.me/") and not link.startswith("t.me/"):
        await update.message.reply_text(
            "❌ لینک نامعتبر است.\n\n📌 مثال: `https://t.me/your_group`",
            parse_mode='Markdown'
        )
        return
    
    await update.message.reply_text("⏳ *در حال بررسی گروه...*", parse_mode='Markdown')
    
    user_id_str = str(user_id)
    tabchis = tabchi_data.get(user_id_str, [])
    active_tabchis = [t for t in tabchis if t.get('active', True)]
    
    owners = []
    
    for tabchi in active_tabchis:
        try:
            client = TelegramClient(
                tabchi.get('session'),
                tabchi.get('api_id'),
                tabchi.get('api_hash')
            )
            await client.connect()
            
            if not await client.is_user_authorized():
                continue
            
            try:
                group = await client.get_entity(link)
                admins = await client.get_participants(group, filter=0)
                
                for admin in admins:
                    if admin.participant.is_creator:
                        owner_name = admin.first_name or "نامشخص"
                        if admin.username:
                            owner_name = f"@{admin.username}"
                        owners.append({
                            "name": owner_name,
                            "id": admin.id,
                            "phone": tabchi.get('phone')
                        })
                        break
            except Exception as e:
                logger.error(f"Error getting group info: {e}")
            
            await client.disconnect()
            
        except Exception as e:
            logger.error(f"Error with tabchi: {e}")
    
    if owners:
        text = f"""
👤 *مالکین گروه*

🔗 *لینک:* {link}

*مالکین پیدا شده:*
"""
        for owner in owners:
            text += f"""
• *نام:* {owner['name']}
• *آیدی:* `{owner['id']}`
• *شماره:* {owner['phone']}
"""
    else:
        text = f"""
👤 *مالکین گروه*

🔗 *لینک:* {link}

❌ *هیچ مالکی پیدا نشد.*

💡 ممکن است گروه خصوصی باشد یا تبچی‌ها معتبر نباشند.
"""
    
    if user_id in ad_data:
        del ad_data[user_id]
    
    keyboard = [[InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back")]]
    
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

# ============ لیست تبچی‌ها ============
async def list_tabchis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    tabchis = tabchi_data.get(user_id, [])
    
    if not tabchis:
        text = """
📋 *لیست تبچی‌ها*

❌ شما هیچ تبچی‌ای ندارید.

➕ از گزینه *"ایجاد تبچی جدید"* استفاده کنید.
"""
    else:
        text = f"""
📋 *لیست تبچی‌ها ({len(tabchis)})*

"""
        for i, tabchi in enumerate(tabchis, 1):
            status = "✅ فعال" if tabchi.get('active', True) else "❌ غیرفعال"
            text += f"{i}. 📱 شماره: `{mask_string(tabchi.get('phone', 'نامشخص'))}`\n"
            text += f"   • وضعیت: {status}\n"
            text += f"   • شناسه جلسه: `{mask_string(tabchi.get('session', ''), 8)}`\n\n"
    
    keyboard = [
        [InlineKeyboardButton("➕ ایجاد تبچی جدید", callback_data="new_session")],
        [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back")]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

# ============ بازگشت به منوی اصلی ============
async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    await clear_user_session(user_id)
    if user_id in ad_data:
        del ad_data[user_id]
    
    await main_menu(update, context, edit=True)

# ============ دستور start ============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await main_menu(update, context)

# ============ هندلر پیام‌ها ============
async def handle_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # ساخت تبچی
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
    
    # ارسال تبلیغ
    if user_id in ad_data:
        mode = ad_data[user_id].get("mode", "ad")
        step = ad_data[user_id].get("step")
        
        if mode == "ad" or mode == "manual_ad":
            if step == "link":
                await handle_ad_link(update, context)
            elif step == "text":
                await handle_ad_text(update, context)
        elif mode == "owner":
            if step == "link":
                await handle_owner_link(update, context)
        return
    
    await update.message.reply_text("❌ لطفاً از دکمه‌های منو استفاده کنید.", parse_mode='Markdown')

# ============ اجرا ============
def main():
    try:
        delete_webhook()
        
        print("=" * 60)
        print("🤖 ربات مدیریت تبلیغات تلگرام")
        print("=" * 60)
        print(f"📌 توکن: {TOKEN[:10]}...{TOKEN[-5:]}")
        print("=" * 60)
        
        application = Application.builder().token(TOKEN).build()
        
        # دکمه‌ها
        application.add_handler(CallbackQueryHandler(new_session, pattern="^new_session$"))
        application.add_handler(CallbackQueryHandler(manual_ad, pattern="^manual_ad$"))
        application.add_handler(CallbackQueryHandler(show_owners, pattern="^show_owners$"))
        application.add_handler(CallbackQueryHandler(list_tabchis, pattern="^list_tabchis$"))
        application.add_handler(CallbackQueryHandler(done_links, pattern="^done_links$"))
        application.add_handler(CallbackQueryHandler(back_to_menu, pattern="^back$"))
        
        # دستور start
        application.add_handler(CommandHandler("start", start))
        
        # هندلر پیام‌ها (برای همه پیام‌های متنی)
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_messages))
        
        print("✅ ربات با موفقیت راه‌اندازی شد.")
        print("💡 برای شروع از /start استفاده کنید.")
        print("=" * 60)
        
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )
        
    except Exception as e:
        print(f"❌ خطا: {e}")

if __name__ == "__main__":
    main()
