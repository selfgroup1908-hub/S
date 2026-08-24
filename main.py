import logging
import re
import asyncio
import os
import json
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters, ConversationHandler
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

# ============ وضعیت‌ها ============
WAITING_FOR_PHONE = 1
WAITING_FOR_API_ID = 2
WAITING_FOR_API_HASH = 3
WAITING_FOR_CODE = 4
WAITING_FOR_PASSWORD = 5
WAITING_FOR_GROUP_LINK = 6
WAITING_FOR_AD_TEXT = 7
WAITING_FOR_OWNER_LINK = 8

user_sessions = {}
user_messages = {}
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
            InlineKeyboardButton("🤖 تبلیغ خودکار", callback_data="auto_ad")
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
        msg = await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        user_messages[user.id] = msg.message_id

# ============ تبلیغ خودکار ============
async def auto_ad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = """
🤖 *تبلیغ خودکار*

🔧 این قابلیت در حال توسعه می‌باشد.

✨ *قابلیت‌های آینده:*
• ⏰ زمان‌بندی هوشمند ارسال
• 📊 مدیریت کمپین‌های تبلیغاتی
• 🎯 هدف‌گیری دقیق مخاطبان

🔙 برای بازگشت به منوی اصلی از دکمه زیر استفاده کنید.
"""
    
    keyboard = [[InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back")]]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

# ============ نمایش مالکین گروه‌ها ============
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
    
    ad_data[query.from_user.id] = {"mode": "owner_check"}
    
    return WAITING_FOR_OWNER_LINK

# ============ تبلیغ دستی ============
async def manual_ad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    tabchis = tabchi_data.get(user_id, [])
    active_tabchis = [t for t in tabchis if t.get('active', True)]
    
    if not active_tabchis:
        text = """
📤 *ارسال تبلیغ*

❌ شما هیچ تبچی فعالی ندارید.

🔑 لطفاً ابتدا یک تبچی ایجاد کنید.
"""
        keyboard = [[InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        return
    
    text = """
📤 *ارسال تبلیغ - مرحله ۱*

📎 لطفاً لینک گروه‌های مورد نظر برای ارسال تبلیغ را ارسال کنید.

💡 می‌توانید *چندین لینک* ارسال کنید.
✅ پس از اتمام، دکمه زیر را فشار دهید.

📌 *مثال:*
`https://t.me/your_group`
"""
    
    keyboard = [
        [InlineKeyboardButton("✅ اتمام ارسال لینک‌ها", callback_data="no_more_links")]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    
    if query.from_user.id not in ad_data:
        ad_data[query.from_user.id] = {"links": [], "text": "", "mode": "manual_ad"}
    
    return WAITING_FOR_GROUP_LINK

# ============ دریافت لینک گروه ============
async def get_group_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    if user_id not in ad_data:
        await update.message.reply_text("❌ لطفاً از منوی اصلی شروع کنید.", parse_mode='Markdown')
        return ConversationHandler.END
    
    if not text.startswith("https://t.me/") and not text.startswith("t.me/"):
        msg = await update.message.reply_text(
            "❌ لینک نامعتبر است.\n\n📌 لطفاً یک لینک معتبر ارسال کنید:\n`https://t.me/your_group`",
            parse_mode='Markdown'
        )
        user_messages[user_id] = msg.message_id
        return WAITING_FOR_GROUP_LINK
    
    mode = ad_data[user_id].get("mode", "manual_ad")
    
    if mode == "owner_check":
        return await show_group_owners(update, context)
    
    ad_data[user_id]["links"].append(text)
    
    text_msg = f"""
✅ *لینک با موفقیت دریافت شد.*

🔗 *لینک:* {text}
📊 *تعداد لینک‌ها:* {len(ad_data[user_id]['links'])}

🔄 می‌توانید لینک بعدی را ارسال کنید یا دکمه زیر را فشار دهید.
"""
    
    keyboard = [
        [InlineKeyboardButton("✅ اتمام ارسال لینک‌ها", callback_data="no_more_links")]
    ]
    
    msg = await update.message.reply_text(
        text_msg,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    user_messages[user_id] = msg.message_id
    
    return WAITING_FOR_GROUP_LINK

# ============ بدون لینک بیشتر ============
async def no_more_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if user_id not in ad_data:
        await query.edit_message_text("❌ خطا! لطفاً دوباره شروع کنید.", parse_mode='Markdown')
        return ConversationHandler.END
    
    links = ad_data[user_id].get("links", [])
    
    if not links:
        text = """
❌ *هیچ لینکی وارد نشده است.*

📌 لطفاً حداقل یک لینک گروه ارسال کنید.
"""
        keyboard = [[InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        return ConversationHandler.END
    
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
    
    ad_data[user_id]["mode"] = "waiting_text"
    
    return WAITING_FOR_AD_TEXT

# ============ دریافت متن تبلیغ ============
async def get_ad_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    if user_id not in ad_data:
        await update.message.reply_text("❌ لطفاً از منوی اصلی شروع کنید.", parse_mode='Markdown')
        return ConversationHandler.END
    
    if not text:
        msg = await update.message.reply_text(
            "❌ متن تبلیغ نمی‌تواند خالی باشد.\n\n📝 لطفاً متن خود را ارسال کنید.",
            parse_mode='Markdown'
        )
        user_messages[user_id] = msg.message_id
        return WAITING_FOR_AD_TEXT
    
    ad_data[user_id]["text"] = text
    
    await start_manual_advertising(update, context, user_id)
    
    return ConversationHandler.END

# ============ تبلیغ دستی ============
async def start_manual_advertising(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id):
    data = ad_data.get(user_id, {})
    links = data.get("links", [])
    ad_text = data.get("text", "")
    
    if not links or not ad_text:
        await update.message.reply_text("❌ خطا! لینک یا متن پیدا نشد.", parse_mode='Markdown')
        return
    
    user_id_str = str(user_id)
    tabchis = tabchi_data.get(user_id_str, [])
    active_tabchis = [t for t in tabchis if t.get('active', True)]
    
    if not active_tabchis:
        await update.message.reply_text("❌ شما هیچ تبچی فعالی ندارید.", parse_mode='Markdown')
        return
    
    msg = await update.message.reply_text(
        f"""
🚀 *شروع ارسال تبلیغ*

📊 *آمار:*
• تعداد تبچی‌ها: *{len(active_tabchis)}*
• تعداد گروه‌ها: *{len(links)}*
• متن: *{ad_text[:100]}{'...' if len(ad_text) > 100 else ''}*

⏳ در حال ارسال...
""",
        parse_mode='Markdown'
    )
    
    success_count = 0
    fail_count = 0
    
    for tabchi in active_tabchis:
        try:
            session_str = tabchi.get('session')
            api_id = tabchi.get('api_id')
            api_hash = tabchi.get('api_hash')
            phone = tabchi.get('phone')
            
            client = TelegramClient(session_str, api_id, api_hash)
            await client.connect()
            
            if not await client.is_user_authorized():
                await update.message.reply_text(
                    f"⚠️ تبچی شماره {phone} معتبر نیست.",
                    parse_mode='Markdown'
                )
                continue
            
            for link in links:
                try:
                    group = await client.get_entity(link)
                    await client.join_channel(group)
                    await client.send_message(group, ad_text)
                    success_count += 1
                    await asyncio.sleep(3)
                    
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

# ============ نمایش مالکین گروه‌ها ============
async def show_group_owners(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    link = update.message.text.strip()
    
    if user_id not in ad_data:
        await update.message.reply_text("❌ لطفاً از منوی اصلی شروع کنید.", parse_mode='Markdown')
        return ConversationHandler.END
    
    if not link.startswith("https://t.me/") and not link.startswith("t.me/"):
        msg = await update.message.reply_text(
            "❌ لینک نامعتبر است.\n\n📌 لطفاً یک لینک معتبر ارسال کنید:",
            parse_mode='Markdown'
        )
        user_messages[user_id] = msg.message_id
        return WAITING_FOR_OWNER_LINK
    
    user_id_str = str(user_id)
    tabchis = tabchi_data.get(user_id_str, [])
    active_tabchis = [t for t in tabchis if t.get('active', True)]
    
    if not active_tabchis:
        await update.message.reply_text("❌ شما هیچ تبچی فعالی ندارید.", parse_mode='Markdown')
        return ConversationHandler.END
    
    await update.message.reply_text(
        "⏳ *در حال بررسی گروه...*",
        parse_mode='Markdown'
    )
    
    owners = []
    
    for tabchi in active_tabchis:
        try:
            session_str = tabchi.get('session')
            api_id = tabchi.get('api_id')
            api_hash = tabchi.get('api_hash')
            
            client = TelegramClient(session_str, api_id, api_hash)
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
                        owner_id = admin.id
                        owners.append({
                            "name": owner_name,
                            "id": owner_id,
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
    
    keyboard = [[InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back")]]
    
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    
    if user_id in ad_data:
        del ad_data[user_id]
    
    return ConversationHandler.END

# ============ ساخت تبچی ============
async def new_session(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_sessions[user_id] = {}
    
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
    
    return WAITING_FOR_PHONE

# ============ دریافت شماره ============
async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    if user_id not in user_sessions:
        await update.message.reply_text("❌ لطفاً از منوی اصلی شروع کنید.", parse_mode='Markdown')
        return ConversationHandler.END
    
    phone = re.sub(r'[^0-9+]', '', text)
    
    if not is_valid_phone(phone):
        msg = await update.message.reply_text(
            "❌ شماره تلفن نامعتبر است.\n\n📌 لطفاً با کد کشور وارد کنید:\n`989123456789`",
            parse_mode='Markdown'
        )
        user_messages[user_id] = msg.message_id
        return WAITING_FOR_PHONE
    
    user_sessions[user_id]['phone'] = phone
    
    text = f"""
✅ *شماره تلفن با موفقیت ثبت شد.*

📱 *شماره:* `{phone}`

🔑 *مرحله ۲:*
📌 لطفاً *API ID* را وارد کنید.

💡 از سایت my.telegram.org دریافت کنید.
"""
    
    keyboard = [[InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back")]]
    
    msg = await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown',
        disable_web_page_preview=True
    )
    user_messages[user_id] = msg.message_id
    
    return WAITING_FOR_API_ID

# ============ دریافت API ID ============
async def get_api_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    if user_id not in user_sessions:
        await update.message.reply_text("❌ لطفاً از منوی اصلی شروع کنید.", parse_mode='Markdown')
        return ConversationHandler.END
    
    if not is_valid_api_id(text):
        msg = await update.message.reply_text(
            "❌ API ID باید عدد باشد.\n\n📌 لطفاً دوباره وارد کنید:",
            parse_mode='Markdown'
        )
        user_messages[user_id] = msg.message_id
        return WAITING_FOR_API_ID
    
    user_sessions[user_id]['api_id'] = int(text)
    
    text = f"""
✅ *API ID با موفقیت ثبت شد.*

🔑 *API ID:* `{text}`

🔐 *مرحله ۳:*
📌 لطفاً *API Hash* را وارد کنید.

💡 از سایت my.telegram.org دریافت کنید.
"""
    
    keyboard = [[InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back")]]
    
    msg = await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown',
        disable_web_page_preview=True
    )
    user_messages[user_id] = msg.message_id
    
    return WAITING_FOR_API_HASH

# ============ دریافت API Hash ============
async def get_api_hash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    if user_id not in user_sessions:
        await update.message.reply_text("❌ لطفاً از منوی اصلی شروع کنید.", parse_mode='Markdown')
        return ConversationHandler.END
    
    if not is_valid_api_hash(text):
        msg = await update.message.reply_text(
            "❌ API Hash نامعتبر است (حداقل 30 کاراکتر).\n\n📌 لطفاً دوباره وارد کنید:",
            parse_mode='Markdown'
        )
        user_messages[user_id] = msg.message_id
        return WAITING_FOR_API_HASH
    
    user_sessions[user_id]['api_hash'] = text
    
    msg = await update.message.reply_text(
        "⏳ *در حال ارسال کد تایید...*",
        parse_mode='Markdown'
    )
    user_messages[user_id] = msg.message_id
    user_sessions[user_id]['message_id'] = msg.message_id
    
    try:
        from telethon import TelegramClient
        
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
        
        text = f"""
✅ *کد تایید ارسال شد.*

📩 کد ۵ رقمی به شماره `{phone}` ارسال شد.

📝 لطفاً کد دریافت شده را وارد کنید.

📌 *مثال:* `12345` یا `1.2.3.4.5`
"""
        
        keyboard = [[InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back")]]
        
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=user_sessions[user_id]['message_id'],
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
        return WAITING_FOR_CODE
        
    except Exception as e:
        error = str(e)
        text = f"❌ خطا در ارسال کد: {error[:200]}"
        
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=user_sessions[user_id]['message_id'],
            text=text,
            parse_mode='Markdown'
        )
        return ConversationHandler.END

# ============ دریافت کد ============
async def get_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    raw_code = update.message.text.strip()
    
    if user_id not in user_sessions:
        await update.message.reply_text("❌ لطفاً از منوی اصلی شروع کنید.", parse_mode='Markdown')
        return ConversationHandler.END
    
    code = clean_code(raw_code)
    
    if not code.isdigit() or len(code) != 5:
        msg = await update.message.reply_text(
            "❌ کد باید ۵ رقم باشد.\n\n📌 *مثال:* `12345` یا `1.2.3.4.5`",
            parse_mode='Markdown'
        )
        user_messages[user_id] = msg.message_id
        return WAITING_FOR_CODE
    
    data = user_sessions[user_id]
    
    try:
        client = data.get('client')
        if not client:
            await update.message.reply_text(
                "❌ اتصال معتبر نیست. لطفاً دوباره شروع کنید.",
                parse_mode='Markdown'
            )
            return ConversationHandler.END
        
        phone = data['phone']
        api_id = data['api_id']
        api_hash = data['api_hash']
        
        try:
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
            
            result_text = f"""
✅ *تبچی با موفقیت ایجاد شد.*

📱 *شماره:* `{phone}`
🔑 *شناسه جلسه:* `{mask_string(session_string, 10)}`

🎯 تبچی به لیست شما اضافه شد.
"""
            
            keyboard = [
                [InlineKeyboardButton("➕ ایجاد تبچی جدید", callback_data="new_session")],
                [InlineKeyboardButton("📋 لیست تبچی‌ها", callback_data="list_tabchis")],
                [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back")]
            ]
            
            if user_id in user_messages:
                try:
                    await context.bot.edit_message_text(
                        chat_id=update.effective_chat.id,
                        message_id=user_messages[user_id],
                        text=result_text,
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode='Markdown'
                    )
                except:
                    await update.message.reply_text(
                        result_text,
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode='Markdown'
                    )
            else:
                await update.message.reply_text(
                    result_text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )
            
            if user_id in user_sessions:
                del user_sessions[user_id]
            if user_id in user_messages:
                del user_messages[user_id]
            
            return ConversationHandler.END
            
        except PhoneCodeExpiredError:
            await client.send_code_request(phone)
            
            text = f"""
🔄 *کد قبلی منقضی شده بود.*

📩 کد جدید به شماره `{phone}` ارسال شد.

📝 لطفاً کد جدید را وارد کنید.
"""
            
            keyboard = [[InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back")]]
            
            msg = await update.message.reply_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            user_messages[user_id] = msg.message_id
            
            return WAITING_FOR_CODE
            
        except SessionPasswordNeededError:
            text = """
🔐 *حساب کاربری شما دارای رمز عبور دو مرحله‌ای است.*

📝 لطفاً *رمز عبور* خود را وارد کنید.
"""
            
            keyboard = [[InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back")]]
            
            msg = await update.message.reply_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            user_messages[user_id] = msg.message_id
            
            return WAITING_FOR_PASSWORD
            
        except Exception as e:
            await update.message.reply_text(
                f"❌ خطا: {str(e)[:200]}",
                parse_mode='Markdown'
            )
            return ConversationHandler.END
            
    except Exception as e:
        await update.message.reply_text(
            f"❌ خطا: {str(e)[:200]}",
            parse_mode='Markdown'
        )
        return ConversationHandler.END

# ============ دریافت پسورد ============
async def get_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    password = update.message.text.strip()
    
    if user_id not in user_sessions:
        await update.message.reply_text("❌ لطفاً از منوی اصلی شروع کنید.", parse_mode='Markdown')
        return ConversationHandler.END
    
    data = user_sessions[user_id]
    
    try:
        client = data.get('client')
        if not client:
            await update.message.reply_text(
                "❌ اتصال معتبر نیست. لطفاً دوباره شروع کنید.",
                parse_mode='Markdown'
            )
            return ConversationHandler.END
        
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
        
        result_text = f"""
✅ *تبچی با موفقیت ایجاد شد.*

📱 *شماره:* `{data['phone']}`
🔑 *شناسه جلسه:* `{mask_string(session_string, 10)}`

🎯 تبچی به لیست شما اضافه شد.
"""
        
        keyboard = [
            [InlineKeyboardButton("➕ ایجاد تبچی جدید", callback_data="new_session")],
            [InlineKeyboardButton("📋 لیست تبچی‌ها", callback_data="list_tabchis")],
            [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back")]
        ]
        
        if user_id in user_messages:
            try:
                await context.bot.edit_message_text(
                    chat_id=update.effective_chat.id,
                    message_id=user_messages[user_id],
                    text=result_text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )
            except:
                await update.message.reply_text(
                    result_text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )
        else:
            await update.message.reply_text(
                result_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        
        if user_id in user_sessions:
            del user_sessions[user_id]
        if user_id in user_messages:
            del user_messages[user_id]
        
        return ConversationHandler.END
        
    except Exception as e:
        msg = await update.message.reply_text(
            f"❌ رمز عبور اشتباه است. {str(e)[:100]}\n\n📝 لطفاً دوباره وارد کنید:",
            parse_mode='Markdown'
        )
        user_messages[user_id] = msg.message_id
        return WAITING_FOR_PASSWORD

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

# ============ دکمه برگشت ============
async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if user_id in user_sessions:
        try:
            client = user_sessions[user_id].get('client')
            if client:
                await client.disconnect()
        except:
            pass
        del user_sessions[user_id]
    if user_id in user_messages:
        del user_messages[user_id]
    if user_id in ad_data:
        del ad_data[user_id]
    
    await main_menu(update, context, edit=True)

# ============ لغو ============
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id in user_sessions:
        try:
            client = user_sessions[user_id].get('client')
            if client:
                await client.disconnect()
        except:
            pass
        del user_sessions[user_id]
    if user_id in user_messages:
        del user_messages[user_id]
    if user_id in ad_data:
        del ad_data[user_id]
    
    await update.message.reply_text(
        "❌ عملیات لغو شد.\n\n🔄 برای شروع مجدد از /start استفاده کنید.",
        parse_mode='Markdown'
    )
    return ConversationHandler.END

# ============ start ============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await main_menu(update, context)

# ============ اجرا ============
def main():
    try:
        delete_webhook()
        
        print("=" * 60)
        print("🤖 ربات مدیریت تبلیغات")
        print("=" * 60)
        print(f"📌 توکن: {TOKEN[:10]}...{TOKEN[-5:]}")
        print("=" * 60)
        
        application = Application.builder().token(TOKEN).build()
        
        conv_handler = ConversationHandler(
            entry_points=[
                CallbackQueryHandler(new_session, pattern="^new_session$"),
            ],
            states={
                WAITING_FOR_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
                WAITING_FOR_API_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_api_id)],
                WAITING_FOR_API_HASH: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_api_hash)],
                WAITING_FOR_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_code)],
                WAITING_FOR_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_password)],
                WAITING_FOR_GROUP_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_group_link)],
                WAITING_FOR_AD_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_ad_text)],
                WAITING_FOR_OWNER_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_group_link)],
            },
            fallbacks=[
                CommandHandler("cancel", cancel),
                CallbackQueryHandler(back_to_menu, pattern="^back$"),
            ],
            name="main_handler",
            persistent=False
        )
        
        application.add_handler(conv_handler)
        
        application.add_handler(CallbackQueryHandler(manual_ad, pattern="^manual_ad$"))
        application.add_handler(CallbackQueryHandler(auto_ad, pattern="^auto_ad$"))
        application.add_handler(CallbackQueryHandler(show_owners, pattern="^show_owners$"))
        application.add_handler(CallbackQueryHandler(no_more_links, pattern="^no_more_links$"))
        application.add_handler(CallbackQueryHandler(list_tabchis, pattern="^list_tabchis$"))
        application.add_handler(CallbackQueryHandler(back_to_menu, pattern="^back$"))
        application.add_handler(CommandHandler("start", start))
        
        print("✅ ربات با موفقیت راه‌اندازی شد.")
        print("💡 برای شروع از /start استفاده کنید.")
        print("=" * 60)
        
        application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)
        
    except Exception as e:
        print(f"❌ خطا: {e}")

if __name__ == "__main__":
    main()
