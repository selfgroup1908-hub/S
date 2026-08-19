import logging
from datetime import datetime, timedelta, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, ChatMemberHandler
import urllib.request

# ============ تنظیمات ============
TOKEN = "8724156247:AAH26WN2k9dlI-K3PFgj665F2r1aGRH4OMw"  # توکن جدید بذار

TEHRAN_OFFSET = timedelta(hours=3, minutes=30)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# دیکشنری برای ذخیره کانال‌های تنظیم شده
channels = {}

# ============ توابع کمکی ============
def now_tehran():
    return datetime.now(timezone.utc) + TEHRAN_OFFSET

def get_chat_type(chat):
    if chat.type == "channel":
        return "📢 کانال"
    elif chat.type in ["group", "supergroup"]:
        return "👥 گروه"
    return "📌 ناشناخته"

def user_mention(user):
    if user.username:
        return f"@{user.username}"
    else:
        return f'<a href="tg://user?id={user.id}">{user.first_name}</a>'

def delete_webhook():
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/deleteWebhook"
        with urllib.request.urlopen(url) as response:
            return True
    except:
        return False

# ============ منوی اصلی ============
async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, edit=False):
    user = update.effective_user
    mention = user_mention(user)
    
    text = f"""
<b>🤖 ربات مدیریت کانال</b>
━━━━━━━━━━━━━━

<b>خوش اومدی</b> {mention} 👋

این ربات برای <b>مدیریت کانال‌ها</b> ساخته شده.

<b>⚡️ برای تنظیم کانال روی دکمه زیر کلیک کن:</b>
"""
    
    keyboard = [[InlineKeyboardButton("⚙️ تنظیم کانال", callback_data="setup_channel")]]
    
    if edit:
        await update.callback_query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
        await update.callback_query.answer("🔙 به منوی اصلی برگشتی!")
    else:
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )

# ============ تنظیم کانال ============
async def setup_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    chat = update.effective_chat
    chat_id = str(chat.id)
    chat_type = get_chat_type(chat)
    chat_title = chat.title or "بدون نام"
    
    # ذخیره کانال
    channels[chat_id] = {
        "name": chat_title,
        "type": chat_type,
        "id": chat_id,
        "username": chat.username,
        "setup_at": now_tehran().strftime("%Y/%m/%d %H:%M")
    }
    
    text = f"""
<b>✅ کانال با موفقیت تنظیم شد!</b>
━━━━━━━━━━━━━━

<b>📌 نام:</b> {chat_title}
<b>📌 نوع:</b> {chat_type}
<b>🆔 آیدی:</b> <code>{chat_id}</code>
<b>⏰ زمان:</b> {now_tehran().strftime('%H:%M:%S')}

ربات الان این {chat_type} رو مدیریت میکنه.
"""
    
    keyboard = [[InlineKeyboardButton("🔙 منوی اصلی", callback_data="back")]]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )
    
    logger.info(f"Channel setup: {chat_title} ({chat_id})")

# ============ ورود به کانال/گروه ============
async def chat_member_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """گزارش کامل ورود ربات به کانال یا گروه"""
    chat = update.effective_chat
    chat_member = update.chat_member
    
    if not chat_member:
        return
    
    # بررسی اینکه ربات خودش عضو شده
    if chat_member.new_chat_member.user.id == context.bot.id:
        if chat_member.new_chat_member.status in ["member", "administrator"]:
            chat_type = get_chat_type(chat)
            chat_title = chat.title or "بدون نام"
            chat_id = chat.id
            chat_username = chat.username
            chat_link = f"https://t.me/{chat_username}" if chat_username else "لینک عمومی ندارد"
            
            # دریافت تعداد اعضا
            try:
                member_count = await context.bot.get_chat_members_count(chat_id)
            except:
                member_count = "نامشخص"
            
            # دریافت لیست ادمین‌ها
            admins_list = []
            try:
                admins = await context.bot.get_chat_administrators(chat_id)
                for admin in admins[:5]:
                    if admin.user.username:
                        admins_list.append(f"@{admin.user.username}")
                    else:
                        admins_list.append(admin.user.first_name)
                if len(admins) > 5:
                    admins_list.append(f"... و {len(admins) - 5} نفر دیگه")
            except:
                admins_list = ["نامشخص"]
            
            admins_text = "، ".join(admins_list) if admins_list else "نامشخص"
            
            # دریافت توضیحات کانال (اگر کانال باشه)
            description = "ندارد"
            if chat.type == "channel":
                try:
                    chat_info = await context.bot.get_chat(chat_id)
                    if chat_info.description:
                        description = chat_info.description[:100] + "..." if len(chat_info.description) > 100 else chat_info.description
                except:
                    pass
            
            # پیام گزارش کامل
            report_text = f"""
<b>✅ ربات به {chat_type} اضافه شد!</b>
━━━━━━━━━━━━━━━━━━━

<b>📌 اطلاعات کلی:</b>
• <b>نام:</b> {chat_title}
• <b>نوع:</b> {chat_type}
• <b>🆔 آیدی:</b> <code>{chat_id}</code>
• <b>🔗 لینک:</b> {chat_link}

<b>👥 آمار اعضا:</b>
• <b>تعداد اعضا:</b> {member_count}

<b>👑 لیست ادمین‌ها:</b>
{admins_text}

<b>📝 توضیحات:</b>
{description}

<b>⏰ زمان ورود:</b> {now_tehran().strftime('%Y/%m/%d %H:%M:%S')}

━━━━━━━━━━━━━━━━━━━
<i>✅ ربات با موفقیت به {chat_type} اضافه شد!</i>
"""
            
            # ارسال گزارش به همون کانال/گروه
            try:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=report_text,
                    parse_mode='HTML'
                )
                logger.info(f"✅ Bot joined {chat_type}: {chat_title} ({chat_id})")
            except Exception as e:
                logger.error(f"❌ Error sending join report: {e}")

# ============ دکمه برگشت ============
async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await main_menu(update, context, edit=True)

# ============ دستور start ============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await main_menu(update, context)

# ============ اجرا ============
def main():
    try:
        delete_webhook()
        
        print("=" * 60)
        print("🚀 ربات مدیریت کانال دیجیاتالی")
        print("=" * 60)
        print(f"📌 توکن: {TOKEN[:10]}...{TOKEN[-5:]}")
        print("=" * 60)
        
        application = Application.builder().token(TOKEN).build()
        
        # دستورات
        application.add_handler(CommandHandler("start", start))
        
        # دکمه‌ها
        application.add_handler(CallbackQueryHandler(setup_channel, pattern="^setup_channel$"))
        application.add_handler(CallbackQueryHandler(back_to_menu, pattern="^back$"))
        
        # گزارش ورود به کانال/گروه
        application.add_handler(ChatMemberHandler(chat_member_update, ChatMemberHandler.CHAT_MEMBER))
        
        print("✅ ربات روشن شد!")
        print("💡 برای شروع /start بفرست")
        print("=" * 60)
        
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )
        
    except Exception as e:
        print(f"❌ خطا: {e}")

if __name__ == "__main__":
    main()
