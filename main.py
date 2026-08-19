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
    """ساخت منشن برای کاربر"""
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

# ============ دکمه‌ها ============
def main_menu_keyboard():
    return [
        [
            InlineKeyboardButton("📋 اطلاعات گروه", callback_data="group_info"),
            InlineKeyboardButton("👥 اعضا", callback_data="members")
        ],
        [
            InlineKeyboardButton("📊 آمار ربات", callback_data="stats"),
            InlineKeyboardButton("❓ راهنما", callback_data="help")
        ]
    ]

# ============ منوی اصلی ============
async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, edit=False):
    user = update.effective_user
    chat = update.effective_chat
    mention = user_mention(user)
    chat_type = get_chat_type(chat)
    
    text = f"""
<b>🤖 ربات دیجیاتالی</b>
━━━━━━━━━━━━━━

<b>خوش اومدی</b> {mention} 👋

<b>📌 نوع چت:</b> {chat_type}
<b>📅 تاریخ:</b> {now_tehran().strftime('%Y/%m/%d')}

<b>⚡️ منوی اصلی:</b>
"""
    
    if edit:
        await update.callback_query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(main_menu_keyboard()),
            parse_mode='HTML'
        )
        await update.callback_query.answer("🔙 به منوی اصلی برگشتی!")
    else:
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(main_menu_keyboard()),
            parse_mode='HTML'
        )

# ============ ورود به گروه/کانال ============
async def chat_member_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """گزارش ورود ربات به گروه یا کانال"""
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
            chat_link = f"https://t.me/{chat.username}" if chat.username else "لینک عمومی ندارد"
            
            # تعداد اعضا
            try:
                member_count = await context.bot.get_chat_members_count(chat_id)
            except:
                member_count = "نامشخص"
            
            # اطلاعات ادمین‌ها
            admins = []
            try:
                chat_admins = await context.bot.get_chat_administrators(chat_id)
                for admin in chat_admins[:5]:  # فقط ۵ تا اول
                    admins.append(admin.user.first_name)
                if len(chat_admins) > 5:
                    admins.append(f"... و {len(chat_admins) - 5} نفر دیگه")
            except:
                admins = ["نامشخص"]
            
            # پیام گزارش
            report_text = f"""
<b>✅ ربات به {chat_type} اضافه شد!</b>
━━━━━━━━━━━━━━

<b>📌 نام:</b> {chat_title}
<b>🆔 آیدی:</b> <code>{chat_id}</code>
<b>🔗 لینک:</b> {chat_link}
<b>👥 تعداد اعضا:</b> {member_count}
<b>👑 ادمین‌ها:</b> {', '.join(admins)}
<b>⏰ زمان:</b> {now_tehran().strftime('%Y/%m/%d %H:%M')}

<i>✅ ربات آماده استفاده است!</i>
"""
            
            # ارسال گزارش به همون چت
            try:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=report_text,
                    parse_mode='HTML'
                )
                logger.info(f"✅ Bot joined {chat_type}: {chat_title} ({chat_id})")
            except Exception as e:
                logger.error(f"❌ Error sending join report: {e}")

# ============ اطلاعات گروه ============
async def group_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    chat = update.effective_chat
    user = update.effective_user
    mention = user_mention(user)
    
    chat_type = get_chat_type(chat)
    chat_title = chat.title or "بدون نام"
    chat_id = chat.id
    chat_link = f"https://t.me/{chat.username}" if chat.username else "لینک عمومی ندارد"
    
    try:
        member_count = await context.bot.get_chat_members_count(chat_id)
    except:
        member_count = "نامشخص"
    
    text = f"""
<b>📋 اطلاعات {chat_type}</b>
━━━━━━━━━━━━━━

<b>📌 نام:</b> {chat_title}
<b>🆔 آیدی:</b> <code>{chat_id}</code>
<b>🔗 لینک:</b> {chat_link}
<b>👥 اعضا:</b> {member_count}
<b>👤 درخواست کننده:</b> {mention}
<b>⏰ زمان:</b> {now_tehran().strftime('%H:%M:%S')}
"""
    
    keyboard = [[InlineKeyboardButton("🔙 منوی اصلی", callback_data="back")]]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

# ============ لیست اعضا ============
async def members_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    chat = update.effective_chat
    chat_id = chat.id
    
    text = f"""
<b>👥 لیست اعضا</b>
━━━━━━━━━━━━━━

<i>در حال دریافت اطلاعات...</i>
"""
    
    keyboard = [[InlineKeyboardButton("🔙 منوی اصلی", callback_data="back")]]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )
    
    # دریافت لیست اعضا (۵ تا اول)
    try:
        members = []
        async for member in context.bot.get_chat_members(chat_id, limit=10):
            if member.user.username:
                members.append(f"@{member.user.username}")
            else:
                members.append(member.user.first_name)
        
        if members:
            members_text = "\n".join([f"• {m}" for m in members[:10]])
            if len(members) > 10:
                members_text += f"\n... و {len(members) - 10} نفر دیگه"
            
            text = f"""
<b>👥 لیست اعضا</b>
━━━━━━━━━━━━━━

{members_text}

<b>📊 مجموع:</b> {len(members)} نفر
"""
        else:
            text = """
<b>👥 لیست اعضا</b>
━━━━━━━━━━━━━━

<i>هیچ عضوی پیدا نشد!</i>
"""
    except Exception as e:
        text = f"""
<b>👥 لیست اعضا</b>
━━━━━━━━━━━━━━

<i>خطا در دریافت لیست اعضا!</i>
"""
        logger.error(f"Error getting members: {e}")
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

# ============ آمار ربات ============
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    bot_info = await context.bot.get_me()
    bot_name = bot_info.first_name
    bot_username = f"@{bot_info.username}" if bot_info.username else "ندارد"
    
    text = f"""
<b>📊 آمار ربات</b>
━━━━━━━━━━━━━━

<b>🤖 نام:</b> {bot_name}
<b>🔗 یوزرنیم:</b> {bot_username}
<b>🆔 آیدی:</b> <code>{bot_info.id}</code>
<b>⏰ زمان سرور:</b> {now_tehran().strftime('%H:%M:%S')}
<b>📅 تاریخ:</b> {now_tehran().strftime('%Y/%m/%d')}

<b>🟢 وضعیت:</b> آنلاین ✅
"""
    
    keyboard = [[InlineKeyboardButton("🔙 منوی اصلی", callback_data="back")]]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

# ============ راهنما ============
async def help_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = """
<b>❓ راهنمای ربات</b>
━━━━━━━━━━━━━━

<b>🔹 قابلیت‌ها:</b>
• گزارش ورود به گروه/کانال
• نمایش اطلاعات گروه
• مشاهده لیست اعضا
• نمایش آمار ربات

<b>🔸 نحوه استفاده:</b>
ربات رو به گروه یا کانال اضافه کن
خودکار گزارش میده!

<b>⚡️ منو:</b>
از دکمه‌های زیر استفاده کن
"""
    
    keyboard = [[InlineKeyboardButton("🔙 منوی اصلی", callback_data="back")]]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

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
        
        print("=" * 50)
        print("🚀 ربات دیجیاتالی")
        print("=" * 50)
        print(f"📌 توکن: {TOKEN[:10]}...{TOKEN[-5:]}")
        print("=" * 50)
        
        application = Application.builder().token(TOKEN).build()
        
        # دستورات
        application.add_handler(CommandHandler("start", start))
        
        # دکمه‌ها
        application.add_handler(CallbackQueryHandler(group_info, pattern="^group_info$"))
        application.add_handler(CallbackQueryHandler(members_list, pattern="^members$"))
        application.add_handler(CallbackQueryHandler(stats, pattern="^stats$"))
        application.add_handler(CallbackQueryHandler(help_menu, pattern="^help$"))
        application.add_handler(CallbackQueryHandler(back_to_menu, pattern="^back$"))
        
        # گزارش ورود به گروه/کانال
        application.add_handler(ChatMemberHandler(chat_member_update, ChatMemberHandler.CHAT_MEMBER))
        
        print("✅ ربات روشن شد!")
        print("💡 /start بفرست")
        print("=" * 50)
        
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )
        
    except Exception as e:
        print(f"❌ خطا: {e}")

if __name__ == "__main__":
    main()
