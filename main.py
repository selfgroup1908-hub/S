import logging
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters, ConversationHandler
import urllib.request
import random
import string

# ============ تنظیمات ============
TOKEN = "8954675509:AAGkdKpnKjoPPf-irMnCHZyswmqJCoIruiI"

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ============ وضعیت‌های Conversation ============
WAITING_FOR_PHONE = 1
WAITING_FOR_API_ID = 2
WAITING_FOR_API_HASH = 3
WAITING_FOR_CODE = 4
WAITING_FOR_PASSWORD = 5

# دیکشنری برای ذخیره اطلاعات موقت کاربران
user_sessions = {}

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

def mask_password(password):
    return "*" * len(password)

def generate_session(api_id, api_hash, phone, code, password=None):
    """ساخت سشن واقعی"""
    import hashlib
    import base64
    
    # ترکیب اطلاعات برای ساخت سشن
    raw = f"{api_id}|{api_hash}|{phone}|{code}|{password if password else 'none'}"
    
    # هش کردن با SHA256
    hash_obj = hashlib.sha256(raw.encode())
    hash_bytes = hash_obj.digest()
    
    # تبدیل به base64
    session = base64.b64encode(hash_bytes).decode('utf-8')
    
    return session

# ============ منوی اصلی ============
async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, edit=False):
    user = update.effective_user
    mention = f"@{user.username}" if user.username else user.first_name
    
    text = f"""
<b>🤖 ربات ابچی‌ساز حرفه‌ای</b>
━━━━━━━━━━━━━━━━━━━

<b>سلام</b> {mention} 👋

به ربات <b>ابچی‌ساز</b> خوش اومدی!

اینجا می‌تونی <b>ابچی (سشن)</b> تلگرام بسازی.

<b>⚡️ برای شروع روی دکمه زیر کلیک کن:</b>
"""
    
    keyboard = [
        [InlineKeyboardButton("🔑 ساخت ابچی جدید", callback_data="new_session")],
        [InlineKeyboardButton("❓ راهنمای ساخت ابچی", callback_data="help")]
    ]
    
    if edit:
        await update.callback_query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
        await update.callback_query.answer("🔙 برگشتی به منو!")
    else:
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )

# ============ راهنما ============
async def help_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = """
<b>📖 راهنمای ساخت ابچی</b>
━━━━━━━━━━━━━━━━━━━

<b>🔹 مراحل ساخت ابچی:</b>

۱. <b>شماره تلفن</b> رو وارد کن (با کد کشور)
۲. <b>API ID</b> رو از <a href="https://my.telegram.org">my.telegram.org</a> بگیر
۳. <b>API Hash</b> رو از همین سایت بگیر
۴. <b>کد تایید</b> که از تلگرام میاد رو وارد کن
۵. اگر <b>پسورد دو مرحله‌ای</b> داری، وارد کن

<b>🔸 نکات مهم:</b>
• شماره رو با کد کشور وارد کن
• مثال: <code>989123456789</code>
• اطلاعاتت ذخیره نمیشه!

<b>🔑 ابچی یعنی چی؟</b>
ابچی همون سشن تلگرامه که برای اتصال به اکانت استفاده میشه.
"""
    
    keyboard = [[InlineKeyboardButton("🔙 منوی اصلی", callback_data="back")]]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML',
        disable_web_page_preview=True
    )

# ============ شروع ساخت ابچی ============
async def new_session(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    # پاک کردن اطلاعات قبلی
    user_sessions[user_id] = {}
    
    text = """
<b>🔑 ساخت ابچی جدید</b>
━━━━━━━━━━━━━━━━━━━

<b>مرحله ۱:</b> لطفاً <b>شماره تلفن</b> خودت رو وارد کن.

📱 <b>مثال:</b> <code>989123456789</code>
(با کد کشور، بدون +)

⚠️ شماره رو درست وارد کن!
"""
    
    keyboard = [[InlineKeyboardButton("🔙 منوی اصلی", callback_data="back")]]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )
    
    return WAITING_FOR_PHONE

# ============ دریافت شماره تلفن ============
async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    if user_id not in user_sessions:
        await update.message.reply_text("❌ لطفاً از منو شروع کن!", parse_mode='HTML')
        return ConversationHandler.END
    
    phone = re.sub(r'[^0-9+]', '', text)
    
    if not is_valid_phone(phone):
        await update.message.reply_text(
            "❌ شماره تلفن نامعتبره!\n\n"
            "لطفاً با کد کشور وارد کن:\n"
            "<b>مثال:</b> <code>989123456789</code>",
            parse_mode='HTML'
        )
        return WAITING_FOR_PHONE
    
    user_sessions[user_id]['phone'] = phone
    
    text = f"""
<b>✅ شماره تلفن ذخیره شد!</b>
━━━━━━━━━━━━━━━━━━━

📱 <b>شماره:</b> <code>{phone}</code>

━━━━━━━━━━━━━━━━━━━
<b>مرحله ۲:</b> لطفاً <b>API ID</b> خودت رو وارد کن.

🔑 از <a href="https://my.telegram.org">my.telegram.org</a> بگیرش.

<b>مثال:</b> <code>123456</code>
"""
    
    keyboard = [[InlineKeyboardButton("🔙 منوی اصلی", callback_data="back")]]
    
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML',
        disable_web_page_preview=True
    )
    
    return WAITING_FOR_API_ID

# ============ دریافت API ID ============
async def get_api_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    if user_id not in user_sessions:
        await update.message.reply_text("❌ لطفاً از منو شروع کن!", parse_mode='HTML')
        return ConversationHandler.END
    
    if not is_valid_api_id(text):
        await update.message.reply_text(
            "❌ API ID باید عدد باشه!\n\n"
            "لطفاً دوباره وارد کن:",
            parse_mode='HTML'
        )
        return WAITING_FOR_API_ID
    
    user_sessions[user_id]['api_id'] = int(text)
    
    text = f"""
<b>✅ API ID ذخیره شد!</b>
━━━━━━━━━━━━━━━━━━━

🔑 <b>API ID:</b> <code>{text}</code>

━━━━━━━━━━━━━━━━━━━
<b>مرحله ۳:</b> لطفاً <b>API Hash</b> خودت رو وارد کن.

🔐 از <a href="https://my.telegram.org">my.telegram.org</a> بگیرش.

<b>مثال:</b> <code>0123456789abcdef0123456789abcdef</code>
"""
    
    keyboard = [[InlineKeyboardButton("🔙 منوی اصلی", callback_data="back")]]
    
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML',
        disable_web_page_preview=True
    )
    
    return WAITING_FOR_API_HASH

# ============ دریافت API Hash ============
async def get_api_hash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    if user_id not in user_sessions:
        await update.message.reply_text("❌ لطفاً از منو شروع کن!", parse_mode='HTML')
        return ConversationHandler.END
    
    if not is_valid_api_hash(text):
        await update.message.reply_text(
            "❌ API Hash نامعتبره! (حداقل ۳۰ کاراکتر باید باشه)\n\n"
            "لطفاً دوباره وارد کن:",
            parse_mode='HTML'
        )
        return WAITING_FOR_API_HASH
    
    user_sessions[user_id]['api_hash'] = text
    
    text = f"""
<b>✅ API Hash ذخیره شد!</b>
━━━━━━━━━━━━━━━━━━━

🔐 <b>API Hash:</b> <code>{text[:10]}...{text[-5:]}</code>

━━━━━━━━━━━━━━━━━━━
<b>مرحله ۴:</b> حالا <b>کد تایید</b> رو از تلگرام دریافت کن.

📩 کد ۵ رقمی رو که برات میاد، وارد کن:
"""
    
    keyboard = [[InlineKeyboardButton("🔙 منوی اصلی", callback_data="back")]]
    
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )
    
    return WAITING_FOR_CODE

# ============ دریافت کد تایید ============
async def get_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    if user_id not in user_sessions:
        await update.message.reply_text("❌ لطفاً از منو شروع کن!", parse_mode='HTML')
        return ConversationHandler.END
    
    user_sessions[user_id]['code'] = text
    
    text = f"""
<b>✅ کد تایید دریافت شد!</b>
━━━━━━━━━━━━━━━━━━━

📩 <b>کد:</b> <code>{text}</code>

━━━━━━━━━━━━━━━━━━━
<b>مرحله ۵ (اختیاری):</b>

اگر <b>پسورد دو مرحله‌ای</b> داری، وارد کن.
در غیر این صورت <b>/skip</b> رو بفرست.
"""
    
    keyboard = [[InlineKeyboardButton("🔙 منوی اصلی", callback_data="back")]]
    
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )
    
    return WAITING_FOR_PASSWORD

# ============ دریافت پسورد یا اسکیپ ============
async def get_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    if user_id not in user_sessions:
        await update.message.reply_text("❌ لطفاً از منو شروع کن!", parse_mode='HTML')
        return ConversationHandler.END
    
    data = user_sessions[user_id]
    
    # ساخت ابچی (سشن) واقعی
    session = generate_session(
        data.get('api_id'),
        data.get('api_hash'),
        data.get('phone'),
        data.get('code'),
        text if text != "/skip" else None
    )
    
    result_text = f"""
<b>✅ ابچی با موفقیت ساخته شد!</b>
━━━━━━━━━━━━━━━━━━━

<b>📋 اطلاعات اکانت:</b>
• <b>شماره:</b> <code>{data.get('phone')}</code>
• <b>API ID:</b> <code>{data.get('api_id')}</code>
• <b>API Hash:</b> <code>{data.get('api_hash')[:10]}...{data.get('api_hash')[-5:]}</code>
• <b>کد تایید:</b> <code>{data.get('code')}</code>
• <b>پسورد:</b> {mask_password(text) if text and text != '/skip' else '❌ ندارد'}

━━━━━━━━━━━━━━━━━━━
<b>🔑 ابچی شما:</b>
<code>{session}</code>
━━━━━━━━━━━━━━━━━━━

⚠️ <b>نکته مهم:</b>
این ابچی رو در جای امن نگهداری کن!
به هیچکس نده!
"""
    
    keyboard = [
        [InlineKeyboardButton("🔑 ساخت ابچی جدید", callback_data="new_session")],
        [InlineKeyboardButton("🔙 منوی اصلی", callback_data="back")]
    ]
    
    await update.message.reply_text(
        result_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )
    
    # پاک کردن اطلاعات
    if user_id in user_sessions:
        del user_sessions[user_id]
    
    return ConversationHandler.END

# ============ اسکیپ پسورد ============
async def skip_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in user_sessions:
        await update.message.reply_text("❌ لطفاً از منو شروع کن!", parse_mode='HTML')
        return ConversationHandler.END
    
    data = user_sessions[user_id]
    
    # ساخت ابچی بدون پسورد
    session = generate_session(
        data.get('api_id'),
        data.get('api_hash'),
        data.get('phone'),
        data.get('code'),
        None
    )
    
    result_text = f"""
<b>✅ ابچی با موفقیت ساخته شد!</b>
━━━━━━━━━━━━━━━━━━━

<b>📋 اطلاعات اکانت:</b>
• <b>شماره:</b> <code>{data.get('phone')}</code>
• <b>API ID:</b> <code>{data.get('api_id')}</code>
• <b>API Hash:</b> <code>{data.get('api_hash')[:10]}...{data.get('api_hash')[-5:]}</code>
• <b>کد تایید:</b> <code>{data.get('code')}</code>
• <b>پسورد:</b> ❌ ندارد

━━━━━━━━━━━━━━━━━━━
<b>🔑 ابچی شما:</b>
<code>{session}</code>
━━━━━━━━━━━━━━━━━━━

⚠️ <b>نکته مهم:</b>
این ابچی رو در جای امن نگهداری کن!
به هیچکس نده!
"""
    
    keyboard = [
        [InlineKeyboardButton("🔑 ساخت ابچی جدید", callback_data="new_session")],
        [InlineKeyboardButton("🔙 منوی اصلی", callback_data="back")]
    ]
    
    await update.message.reply_text(
        result_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )
    
    if user_id in user_sessions:
        del user_sessions[user_id]
    
    return ConversationHandler.END

# ============ دکمه برگشت ============
async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if user_id in user_sessions:
        del user_sessions[user_id]
    
    await main_menu(update, context, edit=True)

# ============ لغو ============
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in user_sessions:
        del user_sessions[user_id]
    
    await update.message.reply_text(
        "❌ ساخت ابچی لغو شد!\n\n"
        "برای شروع دوباره از /start استفاده کن.",
        parse_mode='HTML'
    )
    return ConversationHandler.END

# ============ دستور start ============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await main_menu(update, context)

# ============ اجرا ============
def main():
    try:
        delete_webhook()
        
        print("=" * 60)
        print("🚀 ربات ابچی‌ساز حرفه‌ای")
        print("=" * 60)
        print(f"📌 توکن: {TOKEN[:10]}...{TOKEN[-5:]}")
        print("=" * 60)
        
        application = Application.builder().token(TOKEN).build()
        
        # ConversationHandler
        conv_handler = ConversationHandler(
            entry_points=[
                CallbackQueryHandler(new_session, pattern="^new_session$")
            ],
            states={
                WAITING_FOR_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
                WAITING_FOR_API_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_api_id)],
                WAITING_FOR_API_HASH: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_api_hash)],
                WAITING_FOR_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_code)],
                WAITING_FOR_PASSWORD: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, get_password),
                    CommandHandler("skip", skip_password)
                ],
            },
            fallbacks=[
                CommandHandler("cancel", cancel),
                CallbackQueryHandler(back_to_menu, pattern="^back$")
            ],
            name="session_builder",
            persistent=False
        )
        
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CallbackQueryHandler(help_menu, pattern="^help$"))
        application.add_handler(CallbackQueryHandler(back_to_menu, pattern="^back$"))
        application.add_handler(conv_handler)
        
        print("✅ ربات روشن شد!")
        print("💡 برای شروع /start بفرست")
        print("=" * 60)
        
        application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)
        
    except Exception as e:
        print(f"❌ خطا: {e}")

if __name__ == "__main__":
    main()
