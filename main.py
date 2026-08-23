```python
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
🔥 <b>ربات سلطان تبلیغات</b> 🔥
━━━━━━━━━━━━━━━━━━━━━━━━━

👑 <b>سلام</b> {mention} عزیز!

به <b>قدرتمندترین</b> ربات تبلیغاتی تلگرام خوش اومدی! 🚀

📊 <b>آمار شما:</b>
┏━━━━━━━━━━━━━━━━━━━┓
┃ 👤 تبچی‌ها: <b>{tabchi_count}</b>
┗━━━━━━━━━━━━━━━━━━━┛

⚡️ <b>منوی فرماندهی:</b>
"""
    
    keyboard = [
        [InlineKeyboardButton("🔑 ساخت تبچی جدید", callback_data="new_session")],
        [
            InlineKeyboardButton("📋 لیست تبچی‌ها", callback_data="list_tabchis"),
            InlineKeyboardButton("📢 تبلیغ دستی", callback_data="manual_ad")
        ],
        [
            InlineKeyboardButton("🤖 تبلیغ خودکار", callback_data="auto_ad")
        ],
        [
            InlineKeyboardButton("👑 نمایش مالکین گروه‌ها", callback_data="show_owners")
        ]
    ]
    
    if edit and update.callback_query:
        await update.callback_query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
        await update.callback_query.answer("🔙 بازگشت به منوی اصلی ✅")
    else:
        msg = await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
        user_messages[user.id] = msg.message_id

# ============ تبلیغ خودکار ============
async def auto_ad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = """
🤖 <b>تبلیغ خودکار</b>
━━━━━━━━━━━━━━━━━━━━━━━━━

🔧 <b>در دست ساخت...</b>

✨ <b>قابلیت‌های آینده:</b>
• ⏰ زمان‌بندی هوشمند
• 📊 مدیریت کمپین‌ها
• 🎯 هدف‌گیری دقیق

🔙 به منوی اصلی برگرد.
"""
    
    keyboard = [[InlineKeyboardButton("🔙 منوی اصلی", callback_data="back")]]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
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
👑 <b>نمایش مالکین گروه‌ها</b>
━━━━━━━━━━━━━━━━━━━━━━━━━

❌ <b>هیچ تبچی فعالی ندارید!</b>

🔑 اول یه تبچی بساز!
"""
        keyboard = [[InlineKeyboardButton("🔙 منوی اصلی", callback_data="back")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
        return
    
    text = """
👑 <b>نمایش مالکین گروه‌ها</b>
━━━━━━━━━━━━━━━━━━━━━━━━━

⏳ <b>لینک گروه</b> رو بفرست...

📌 مثال:
<code>https://t.me/your_group</code>
"""
    
    keyboard = [[InlineKeyboardButton("🔙 منوی اصلی", callback_data="back")]]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )
    
    # ذخیره وضعیت
    context.user_data['owner_check'] = True
    ad_data[query.from_user.id] = {"mode": "owner_check"}
    
    return WAITING_FOR_GROUP_LINK

# ============ تبلیغ دستی ============
async def manual_ad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    tabchis = tabchi_data.get(user_id, [])
    active_tabchis = [t for t in tabchis if t.get('active', True)]
    
    if not active_tabchis:
        text = """
📢 <b>تبلیغ دستی</b>
━━━━━━━━━━━━━━━━━━━━━━━━━

❌ <b>هیچ تبچی فعالی ندارید!</b>

🔑 اول یه تبچی بساز!
"""
        keyboard = [[InlineKeyboardButton("🔙 منوی اصلی", callback_data="back")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
        return
    
    text = """
📢 <b>تبلیغ دستی</b>
━━━━━━━━━━━━━━━━━━━━━━━━━

<b>مرحله ۱:</b> لینک گروه رو بفرست.

📌 مثال:
<code>https://t.me/your_group</code>

🔄 می‌تونی چندتا لینک بفرستی.
✅ وقتی تموم شد، دکمه پایین رو بزن.
"""
    
    keyboard = [
        [InlineKeyboardButton("✅ تموم شد، برو مرحله بعد", callback_data="no_more_links")]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )
    
    if query.from_user.id not in ad_data:
        ad_data[query.from_user.id] = {"links": [], "text": "", "mode": "manual_ad"}
    
    return WAITING_FOR_GROUP_LINK

# ============ دریافت لینک گروه ============
async def get_group_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    if user_id not in ad_data:
        await update.message.reply_text("❌ لطفاً از منو شروع کن!", parse_mode='HTML')
        return ConversationHandler.END
    
    if not text.startswith("https://t.me/") and not text.startswith("t.me/"):
        msg = await update.message.reply_text(
            "❌ لینک نامعتبر!\n\n"
            "لینک معتبر بفرست:\n"
            "<b>مثال:</b> <code>https://t.me/your_group</code>",
            parse_mode='HTML'
        )
        user_messages[user_id] = msg.message_id
        return WAITING_FOR_GROUP_LINK
    
    # چک کردن اینکه کاربر در حالت owner_check هست یا manual_ad
    mode = ad_data[user_id].get("mode", "manual_ad")
    
    if mode == "owner_check":
        # نمایش مالکین گروه
        return await show_group_owners(update, context)
    
    # تبلیغ دستی
    ad_data[user_id]["links"].append(text)
    
    text = f"""
✅ <b>لینک دریافت شد!</b>
━━━━━━━━━━━━━━━━━━━━━━━━━

🔗 {text}

📊 <b>تعداد لینک‌ها:</b> {len(ad_data[user_id]['links'])}

🔄 لینک بعدی رو بفرست یا دکمه زیر رو بزن.
"""
    
    keyboard = [
        [InlineKeyboardButton("✅ تموم شد، برو مرحله بعد", callback_data="no_more_links")]
    ]
    
    msg = await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )
    user_messages[user_id] = msg.message_id
    
    return WAITING_FOR_GROUP_LINK

# ============ بدون لینک بیشتر ============
async def no_more_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if user_id not in ad_data:
        await query.edit_message_text("❌ خطا! دوباره شروع کن.", parse_mode='HTML')
        return ConversationHandler.END
    
    links = ad_data[user_id].get("links", [])
    
    if not links:
        text = """
❌ <b>هیچ لینکی وارد نشده!</b>
━━━━━━━━━━━━━━━━━━━━━━━━━

حداقل یه لینک گروه بفرست.
"""
        keyboard = [[InlineKeyboardButton("🔙 منوی اصلی", callback_data="back")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
        return ConversationHandler.END
    
    text = f"""
✅ <b>{len(links)} لینک ذخیره شد!</b>
━━━━━━━━━━━━━━━━━━━━━━━━━

🔗 <b>لینک‌ها:</b>
{chr(10).join([f'• {l}' for l in links])}

━━━━━━━━━━━━━━━━━━━━━━━━━
<b>مرحله ۲:</b> متن تبلیغی رو بفرست.

📝 هرچی دوست داری توی گروه‌ها بفرستی...
"""
    
    keyboard = [[InlineKeyboardButton("🔙 منوی اصلی", callback_data="back")]]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )
    
    ad_data[user_id]["mode"] = "waiting_text"
    
    return WAITING_FOR_AD_TEXT

# ============ دریافت متن تبلیغ ============
async def get_ad_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    if user_id not in ad_data:
        await update.message.reply_text("❌ لطفاً از منو شروع کن!", parse_mode='HTML')
        return ConversationHandler.END
    
    if not text:
        msg = await update.message.reply_text(
            "❌ متن نمی‌تونه خالی باشه!\n\n"
            "متن تبلیغی رو بفرست:",
            parse_mode='HTML'
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
        await update.message.reply_text(
            "❌ خطا! لینک یا متن پیدا نشد.",
            parse_mode='HTML'
        )
        return
    
    user_id_str = str(user_id)
    tabchis = tabchi_data.get(user_id_str, [])
    active_tabchis = [t for t in tabchis if t.get('active', True)]
    
    if not active_tabchis:
        await update.message.reply_text(
            "❌ هیچ تبچی فعالی ندارید!",
            parse_mode='HTML'
        )
        return
    
    await update.message.reply_text(
        f"""
🚀 <b>شروع تبلیغ دستی...</b>
━━━━━━━━━━━━━━━━━━━━━━━━━

📊 <b>آمار:</b>
┏━━━━━━━━━━━━━━━━━━━┓
┃ 👤 تبچی‌ها: {len(active_tabchis)}
┃ 🔗 گروه‌ها: {len(links)}
┗━━━━━━━━━━━━━━━━━━━┛

📝 <b>متن:</b> {ad_text[:100]}{'...' if len(ad_text) > 100 else ''}

⏳ در حال ارسال...
""",
        parse_mode='HTML'
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
                    f"❌ تبچی {phone} معتبر نیست!",
                    parse_mode='HTML'
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
✅ <b>تبلیغ با موفقیت انجام شد!</b>
━━━━━━━━━━━━━━━━━━━━━━━━━

📊 <b>نتیجه نهایی:</b>
┏━━━━━━━━━━━━━━━━━━━┓
┃ ✅ موفق: {success_count}
┃ ❌ ناموفق: {fail_count}
┗━━━━━━━━━━━━━━━━━━━┛

🔥 برای تبلیغ جدید از منو استفاده کن!
""",
        parse_mode='HTML'
    )

# ============ نمایش مالکین گروه‌ها ============
async def show_group_owners(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    link = update.message.text.strip()
    
    if user_id not in ad_data:
        await update.message.reply_text("❌ لطفاً از منو شروع کن!", parse_mode='HTML')
        return ConversationHandler.END
    
    if not link.startswith("https://t.me/") and not link.startswith("t.me/"):
        msg = await update.message.reply_text(
            "❌ لینک نامعتبر!\n\n"
            "لینک معتبر بفرست:",
            parse_mode='HTML'
        )
        user_messages[user_id] = msg.message_id
        return WAITING_FOR_GROUP_LINK
    
    user_id_str = str(user_id)
    tabchis = tabchi_data.get(user_id_str, [])
    active_tabchis = [t for t in tabchis if t.get('active', True)]
    
    if not active_tabchis:
        await update.message.reply_text(
            "❌ هیچ تبچی فعالی ندارید!",
            parse_mode='HTML'
        )
        return ConversationHandler.END
    
    await update.message.reply_text(
        "⏳ در حال بررسی گروه...",
        parse_mode='HTML'
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
👑 <b>مالکین گروه</b>
━━━━━━━━━━━━━━━━━━━━━━━━━

🔗 <b>لینک:</b> {link}

<b>مالکین پیدا شده:</b>
"""
        for owner in owners:
            text += f"""
┏━━━━━━━━━━━━━━━━━━━┓
┃ 👤 {owner['name']}
┃ 🆔 <code>{owner['id']}</code>
┃ 📱 {owner['phone']}
┗━━━━━━━━━━━━━━━━━━━┛
"""
    else:
        text = f"""
👑 <b>مالکین گروه</b>
━━━━━━━━━━━━━━━━━━━━━━━━━

🔗 <b>لینک:</b> {link}

❌ <b>هیچ مالکی پیدا نشد!</b>

ممکنه گروه خصوصی باشه یا تبچی‌ها معتبر نباشن.
"""
    
    keyboard = [[InlineKeyboardButton("🔙 منوی اصلی", callback_data="back")]]
    
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
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
🔑 <b>ساخت تبچی جدید</b>
━━━━━━━━━━━━━━━━━━━━━━━━━

<b>مرحله ۱:</b> شماره تلفن رو وارد کن.

📱 <b>مثال:</b> <code>989123456789</code>
(با کد کشور، بدون +)
"""
    
    keyboard = [[InlineKeyboardButton("🔙 منوی اصلی", callback_data="back")]]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )
    
    return WAITING_FOR_PHONE

# ============ دریافت شماره ============
async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    if user_id not in user_sessions:
        await update.message.reply_text("❌ لطفاً از منو شروع کن!", parse_mode='HTML')
        return ConversationHandler.END
    
    phone = re.sub(r'[^0-9+]', '', text)
    
    if not is_valid_phone(phone):
        msg = await update.message.reply_text(
            "❌ شماره نامعتبر!\n\n"
            "با کد کشور وارد کن:\n"
            "<b>مثال:</b> <code>989123456789</code>",
            parse_mode='HTML'
        )
        user_messages[user_id] = msg.message_id
        return WAITING_FOR_PHONE
    
    user_sessions[user_id]['phone'] = phone
    
    text = f"""
✅ <b>شماره ذخیره شد!</b>
━━━━━━━━━━━━━━━━━━━━━━━━━

📱 <b>شماره:</b> <code>{phone}</code>

━━━━━━━━━━━━━━━━━━━━━━━━━
<b>مرحله ۲:</b> API ID رو وارد کن.

🔑 از <a href="https://my.telegram.org">my.telegram.org</a> بگیر.
"""
    
    keyboard = [[InlineKeyboardButton("🔙 منوی اصلی", callback_data="back")]]
    
    msg = await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML',
        disable_web_page_preview=True
    )
    user_messages[user_id] = msg.message_id
    
    return WAITING_FOR_API_ID

# ============ دریافت API ID ============
async def get_api_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    if user_id not in user_sessions:
        await update.message.reply_text("❌ لطفاً از منو شروع کن!", parse_mode='HTML')
        return ConversationHandler.END
    
    if not is_valid_api_id(text):
        msg = await update.message.reply_text(
            "❌ API ID باید عدد باشه!\n\n"
            "دوباره وارد کن:",
            parse_mode='HTML'
        )
        user_messages[user_id] = msg.message_id
        return WAITING_FOR_API_ID
    
    user_sessions[user_id]['api_id'] = int(text)
    
    text = f"""
✅ <b>API ID ذخیره شد!</b>
━━━━━━━━━━━━━━━━━━━━━━━━━

🔑 <b>API ID:</b> <code>{text}</code>

━━━━━━━━━━━━━━━━━━━━━━━━━
<b>مرحله ۳:</b> API Hash رو وارد کن.

🔐 از <a href="https://my.telegram.org">my.telegram.org</a> بگیر.
"""
    
    keyboard = [[InlineKeyboardButton("🔙 منوی اصلی", callback_data="back")]]
    
    msg = await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML',
        disable_web_page_preview=True
    )
    user_messages[user_id] = msg.message_id
    
    return WAITING_FOR_API_HASH

# ============ دریافت API Hash ============
async def get_api_hash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    if user_id not in user_sessions:
        await update.message.reply_text("❌ لطفاً از منو شروع کن!", parse_mode='HTML')
        return ConversationHandler.END
    
    if not is_valid_api_hash(text):
        msg = await update.message.reply_text(
            "❌ API Hash نامعتبر! (حداقل ۳۰ کاراکتر)\n\n"
            "دوباره وارد کن:",
            parse_mode='HTML'
        )
        user_messages[user_id] = msg.message_id
        return WAITING_FOR_API_HASH
    
    user_sessions[user_id]['api_hash'] = text
    
    msg = await update.message.reply_text(
        "⏳ در حال ارسال کد...",
        parse_mode='HTML'
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
✅ <b>کد تایید ارسال شد!</b>
━━━━━━━━━━━━━━━━━━━━━━━━━

📩 کد ۵ رقمی به <code>{phone}</code> ارسال شد.

کد رو وارد کن:
<b>مثال:</b> <code>12345</code> یا <code>1.2.3.4.5</code>
"""
        
        keyboard = [[InlineKeyboardButton("🔙 منوی اصلی", callback_data="back")]]
        
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=user_sessions[user_id]['message_id'],
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
        
        return WAITING_FOR_CODE
        
    except Exception as e:
        error = str(e)
        text = f"❌ خطا در ارسال کد: {error[:200]}"
        
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=user_sessions[user_id]['message_id'],
            text=text,
            parse_mode='HTML'
        )
        return ConversationHandler.END

# ============ دریافت کد ============
async def get_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    raw_code = update.message.text.strip()
    
    if user_id not in user_sessions:
        await update.message.reply_text("❌ لطفاً از منو شروع کن!", parse_mode='HTML')
        return ConversationHandler.END
    
    code = clean_code(raw_code)
    
    if not code.isdigit() or len(code) != 5:
        msg = await update.message.reply_text(
            "❌ کد باید ۵ رقم باشد!\n\n"
            "مثال: <code>12345</code> یا <code>1.2.3.4.5</code>",
            parse_mode='HTML'
        )
        user_messages[user_id] = msg.message_id
        return WAITING_FOR_CODE
    
    data = user_sessions[user_id]
    
    try:
        client = data.get('client')
        if not client:
            await update.message.reply_text(
                "❌ اتصال معتبر نیست! دوباره شروع کن.",
                parse_mode='HTML'
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
✅ <b>تبچی ساخته شد!</b>
━━━━━━━━━━━━━━━━━━━━━━━━━

📱 <b>شماره:</b> <code>{phone}</code>
🔑 <b>سشن:</b> <code>{mask_string(session_string, 10)}</code>

🔥 تبچی به لیست اضافه شد!
"""
            
            keyboard = [
                [InlineKeyboardButton("🔑 ساخت تبچی جدید", callback_data="new_session")],
                [InlineKeyboardButton("📋 لیست تبچی‌ها", callback_data="list_tabchis")],
                [InlineKeyboardButton("🔙 منوی اصلی", callback_data="back")]
            ]
            
            if user_id in user_messages:
                try:
                    await context.bot.edit_message_text(
                        chat_id=update.effective_chat.id,
                        message_id=user_messages[user_id],
                        text=result_text,
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode='HTML'
                    )
                except:
                    await update.message.reply_text(
                        result_text,
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode='HTML'
                    )
            else:
                await update.message.reply_text(
                    result_text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='HTML'
                )
            
            if user_id in user_sessions:
                del user_sessions[user_id]
            if user_id in user_messages:
                del user_messages[user_id]
            
            return ConversationHandler.END
            
        except PhoneCodeExpiredError:
            await client.send_code_request(phone)
            
            text = f"""
🔄 <b>کد جدید ارسال شد!</b>
━━━━━━━━━━━━━━━━━━━━━━━━━

کد قبلی <b>منقضی</b> شده بود.

📩 کد جدید به <code>{phone}</code> ارسال شد.

کد جدید رو وارد کن:
"""
            
            keyboard = [[InlineKeyboardButton("🔙 منوی اصلی", callback_data="back")]]
            
            msg = await update.message.reply_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='HTML'
            )
            user_messages[user_id] = msg.message_id
            
            return WAITING_FOR_CODE
            
        except SessionPasswordNeededError:
            text = f"""
🔐 <b>نیاز به پسورد دو مرحله‌ای!</b>
━━━━━━━━━━━━━━━━━━━━━━━━━

اکانتت <b>پسورد دو مرحله‌ای</b> داره.

پسورد رو وارد کن:
"""
            
            keyboard = [[InlineKeyboardButton("🔙 منوی اصلی", callback_data="back")]]
            
            msg = await update.message.reply_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='HTML'
            )
            user_messages[user_id] = msg.message_id
            
            return WAITING_FOR_PASSWORD
            
        except Exception as e:
            await update.message.reply_text(
                f"❌ خطا: {str(e)[:200]}",
                parse_mode='HTML'
            )
            return ConversationHandler.END
            
    except Exception as e:
        await update.message.reply_text(
            f"❌ خطا: {str(e)[:200]}",
            parse_mode='HTML'
        )
        return ConversationHandler.END

# ============ دریافت پسورد ============
async def get_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    password = update.message.text.strip()
    
    if user_id not in user_sessions:
        await update.message.reply_text("❌ لطفاً از منو شروع کن!", parse_mode='HTML')
        return ConversationHandler.END
    
    data = user_sessions[user_id]
    
    try:
        client = data.get('client')
        if not client:
            await update.message.reply_text(
                "❌ اتصال معتبر نیست! دوباره شروع کن.",
                parse_mode='HTML'
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
✅ <b>تبچی ساخته شد!</b>
━━━━━━━━━━━━━━━━━━━━━━━━━

📱 <b>شماره:</b> <code>{data['phone']}</code>
🔑 <b>سشن:</b> <code>{mask_string(session_string, 10)}</code>

🔥 تبچی به لیست اضافه شد!
"""
        
        keyboard = [
            [InlineKeyboardButton("🔑 ساخت تبچی جدید", callback_data="new_session")],
            [InlineKeyboardButton("📋 لیست تبچی‌ها", callback_data="list_tabchis")],
            [InlineKeyboardButton("🔙 منوی اصلی", callback_data="back")]
        ]
        
        if user_id in user_messages:
            try:
                await context.bot.edit_message_text(
                    chat_id=update.effective_chat.id,
                    message_id=user_messages[user_id],
                    text=result_text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='HTML'
                )
            except:
                await update.message.reply_text(
                    result_text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='HTML'
                )
        else:
            await update.message.reply_text(
                result_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='HTML'
            )
        
        if user_id in user_sessions:
            del user_sessions[user_id]
        if user_id in user_messages:
            del user_messages[user_id]
        
        return ConversationHandler.END
        
    except Exception as e:
        msg = await update.message.reply_text(
            f"❌ پسورد اشتباه! {str(e)[:100]}\n\n"
            "دوباره پسورد رو وارد کن:",
            parse_mode='HTML'
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
📋 <b>لیست تبچی‌ها</b>
━━━━━━━━━━━━━━━━━━━━━━━━━

<i>هیچ تبچی‌ای نداری!</i>

🔑 از گزینه <b>ساخت تبچی جدید</b> استفاده کن.
"""
    else:
        text = f"""
📋 <b>لیست تبچی‌ها ({len(tabchis)})</b>
━━━━━━━━━━━━━━━━━━━━━━━━━

"""
        for i, tabchi in enumerate(tabchis, 1):
            status = "✅ فعال" if tabchi.get('active', True) else "❌ غیرفعال"
            text += f"{i}. 📱 <code>{mask_string(tabchi.get('phone', 'نامشخص'))}</code>\n"
            text += f"   وضعیت: {status}\n"
            text += f"   سشن: <code>{mask_string(tabchi.get('session', ''), 8)}</code>\n\n"
    
    keyboard = [
        [InlineKeyboardButton("🔑 ساخت تبچی جدید", callback_data="new_session")],
        [InlineKeyboardButton("🔙 منوی اصلی", callback_data="back")]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
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
    if 'owner_check' in context.user_data:
        del context.user_data['owner_check']
    
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
        "❌ عملیات لغو شد!\n\n"
        "برای شروع دوباره از /start استفاده کن.",
        parse_mode='HTML'
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
        print("🔥 ربات سلطان تبلیغات")
        print("=" * 60)
        print(f"📌 توکن: {TOKEN[:10]}...{TOKEN[-5:]}")
        print("=" * 60)
        
        application = Application.builder().token(TOKEN).build()
        
        # ConversationHandler با entry_points
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
            },
            fallbacks=[
                CommandHandler("cancel", cancel),
                CallbackQueryHandler(back_to_menu, pattern="^back$"),
            ],
            name="main_handler",
            persistent=False
        )
        
        application.add_handler(conv_handler)
        
        # هندلرهای دکمه‌های دیگه (خارج از ConversationHandler)
        application.add_handler(CallbackQueryHandler(manual_ad, pattern="^manual_ad$"))
        application.add_handler(CallbackQueryHandler(auto_ad, pattern="^auto_ad$"))
        application.add_handler(CallbackQueryHandler(show_owners, pattern="^show_owners$"))
        application.add_handler(CallbackQueryHandler(no_more_links, pattern="^no_more_links$"))
        application.add_handler(CallbackQueryHandler(list_tabchis, pattern="^list_tabchis$"))
        application.add_handler(CommandHandler("start", start))
        
        print("✅ ربات روشن شد!")
        print("💡 برای شروع /start بفرست")
        print("=" * 60)
        
        application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)
        
    except Exception as e:
        print(f"❌ خطا: {e}")

if __name__ == "__main__":
    main()
```
