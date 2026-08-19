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

schedules = {}

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
            InlineKeyboardButton("⏰ تنظیم زمان", callback_data="set_time"),
            InlineKeyboardButton("📋 وضعیت زمان", callback_data="view_time")
        ],
        [
            InlineKeyboardButton("🗑 حذف زمان‌بندی", callback_data="remove_time"),
            InlineKeyboardButton("📊 آمار", callback_data="dashboard")
        ]
    ]

# ============ منوی اصلی ============
async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, edit=False):
    user = update.effective_user
    chat = update.effective_chat
    mention = user_mention(user)
    
    text = f"""
<b>🤖 ربات زمان‌بندی دیجیاتالی</b>
━━━━━━━━━━━━━━

<b>خوش اومدی</b> {mention} 👋

<b>نوع چت:</b> {get_chat_type(chat)}

<b>⚡️ منو:</b>
"""
    
    if edit:
        await update.callback_query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(main_menu_keyboard()),
            parse_mode='HTML'
        )
        await update.callback_query.answer("🔙 به منو برگشتی!")
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
        if chat_member.new_chat_member.status == "member" or chat_member.new_chat_member.status == "administrator":
            chat_type = get_chat_type(chat)
            chat_title = chat.title or "بدون نام"
            chat_id = chat.id
            chat_link = f"https://t.me/{chat.username}" if chat.username else "لینک عمومی ندارد"
            member_count = 0
            
            # تعداد اعضا
            try:
                member_count = await context.bot.get_chat_members_count(chat_id)
            except:
                member_count = "نامشخص"
            
            # پیام گزارش
            report_text = f"""
<b>✅ ربات به {chat_type} اضافه شد!</b>
━━━━━━━━━━━━━━

<b>📌 نام:</b> {chat_title}
<b>🆔 آیدی:</b> <code>{chat_id}</code>
<b>🔗 لینک:</b> {chat_link}
<b>👥 تعداد اعضا:</b> {member_count}
<b>⏰ زمان:</b> {now_tehran().strftime('%Y/%m/%d %H:%M')}

<i>ربات آماده استفاده است!</i>
"""
            
            # ارسال گزارش به ادمین (همون چت)
            try:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=report_text,
                    parse_mode='HTML'
                )
                logger.info(f"✅ Bot joined {chat_type}: {chat_title} ({chat_id})")
            except Exception as e:
                logger.error(f"❌ Error sending join report: {e}")

# ============ تنظیم زمان ============
async def set_time_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = """
<b>⏰ تنظیم زمان</b>
━━━━━━━━━━━━━━

ساعت رو انتخاب کن:
"""
    
    keyboard = []
    row = []
    for hour in range(0, 24):
        row.append(InlineKeyboardButton(f"{hour:02d}", callback_data=f"hour_{hour}"))
        if len(row) == 6:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton("🔙 برگشت", callback_data="back")])
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def select_hour(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    hour = int(query.data.split("_")[1])
    context.user_data['selected_hour'] = hour
    
    text = f"""
<b>⏰ تنظیم زمان</b>
━━━━━━━━━━━━━━

ساعت <b>{hour:02d}</b> انتخاب شد

دقیقه رو انتخاب کن:
"""
    
    keyboard = []
    row = []
    for minute in range(0, 60, 5):
        row.append(InlineKeyboardButton(f"{minute:02d}", callback_data=f"minute_{hour}_{minute}"))
        if len(row) == 6:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton("🔙 برگشت به ساعت", callback_data="set_time")])
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def select_minute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split("_")
    hour = int(parts[1])
    minute = int(parts[2])
    time_str = f"{hour:02d}:{minute:02d}"
    
    chat = update.effective_chat
    chat_id = str(chat.id)
    user = update.effective_user
    mention = user_mention(user)
    
    schedules[chat_id] = {
        "time": time_str,
        "enabled": True,
        "chat_type": get_chat_type(chat),
        "chat_title": chat.title or chat_id,
        "set_by": mention,
        "set_by_id": user.id,
        "created_at": now_tehran().strftime("%Y/%m/%d %H:%M")
    }
    
    text = f"""
<b>✅ زمان تنظیم شد!</b>
━━━━━━━━━━━━━━

<b>تنظیم کننده:</b> {mention}
<b>🕐 ساعت:</b> <code>{time_str}</code>
<b>📌 وضعیت:</b> ✅ فعال

ربات هر روز <b>{time_str}</b> پیام می‌فرسته.
"""
    
    keyboard = [[InlineKeyboardButton("🔙 برگشت", callback_data="back")]]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )
    
    logger.info(f"Time set for {chat_id}: {time_str} by {user.id}")

# ============ مشاهده وضعیت ============
async def view_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    chat = update.effective_chat
    chat_id = str(chat.id)
    
    if chat_id not in schedules:
        text = """
<b>📋 وضعیت زمان‌بندی</b>
━━━━━━━━━━━━━━

❌ هیچ زمانی تنظیم نشده.
از منو <b>تنظیم زمان</b> رو بزن.
"""
    else:
        data = schedules[chat_id]
        status = "✅ فعال" if data["enabled"] else "❌ غیرفعال"
        
        text = f"""
<b>📋 وضعیت زمان‌بندی</b>
━━━━━━━━━━━━━━

<b>🕐 ساعت:</b> <code>{data['time']}</code>
<b>📊 وضعیت:</b> {status}
<b>👤 تنظیم کننده:</b> {data.get('set_by', 'نامشخص')}
<b>📅 تاریخ:</b> {data.get('created_at', 'نامشخص')}
"""
    
    keyboard = [[InlineKeyboardButton("🔙 برگشت", callback_data="back")]]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

# ============ حذف زمان‌بندی ============
async def remove_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    chat = update.effective_chat
    chat_id = str(chat.id)
    
    if chat_id not in schedules:
        text = """
<b>🗑 حذف زمان‌بندی</b>
━━━━━━━━━━━━━━

❌ زمانی برای حذف نیست.
"""
        keyboard = [[InlineKeyboardButton("🔙 برگشت", callback_data="back")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
        return
    
    data = schedules[chat_id]
    
    text = f"""
<b>🗑 حذف زمان‌بندی</b>
━━━━━━━━━━━━━━

<b>🕐 ساعت:</b> <code>{data['time']}</code>

مطمئنی؟ 
"""
    
    keyboard = [
        [
            InlineKeyboardButton("✅ آره حذف کن", callback_data="confirm_remove"),
            InlineKeyboardButton("❌ نه برگرد", callback_data="back")
        ]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def confirm_remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    chat = update.effective_chat
    chat_id = str(chat.id)
    
    if chat_id in schedules:
        data = schedules[chat_id]
        del schedules[chat_id]
        
        text = f"""
<b>✅ حذف شد!</b>
━━━━━━━━━━━━━━

ساعت <code>{data['time']}</code> حذف شد.
"""
    else:
        text = "❌ چیزی برای حذف نیست."
    
    keyboard = [[InlineKeyboardButton("🔙 برگشت", callback_data="back")]]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )
    
    logger.info(f"Schedule removed for {chat_id}")

# ============ آمار ============
async def dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    total = len(schedules)
    active = sum(1 for s in schedules.values() if s["enabled"])
    
    schedule_list = ""
    if schedules:
        for idx, (chat_id, data) in enumerate(list(schedules.items())[:10], 1):
            status_icon = "✅" if data["enabled"] else "❌"
            schedule_list += f"{idx}. {data['chat_type']} → <code>{data['time']}</code> {status_icon}\n"
        if len(schedules) > 10:
            schedule_list += f"\n... و {len(schedules) - 10} تا دیگه"
    else:
        schedule_list = "<i>هیچی نداریم!</i>"
    
    text = f"""
<b>📊 آمار</b>
━━━━━━━━━━━━━━

<b>⏰ زمان:</b> <code>{now_tehran().strftime('%H:%M:%S')}</code>

<b>📌 مجموع:</b> {total}
<b>✅ فعال:</b> {active}
<b>❌ غیرفعال:</b> {total - active}

<b>📋 لیست:</b>
{schedule_list}
"""
    
    keyboard = [[InlineKeyboardButton("🔙 برگشت", callback_data="back")]]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

# ============ دکمه برگشت ============
async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await main_menu(update, context, edit=True)

# ============ اجرا ============
def main():
    try:
        delete_webhook()
        
        print("=" * 50)
        print("🚀 ربات زمان‌بندی دیجیاتالی")
        print("=" * 50)
        print(f"📌 توکن: {TOKEN[:10]}...{TOKEN[-5:]}")
        print("=" * 50)
        
        application = Application.builder().token(TOKEN).build()
        
        # دستورات
        application.add_handler(CommandHandler("start", main_menu))
        
        # دکمه‌ها
        application.add_handler(CallbackQueryHandler(set_time_menu, pattern="^set_time$"))
        application.add_handler(CallbackQueryHandler(view_time, pattern="^view_time$"))
        application.add_handler(CallbackQueryHandler(remove_time, pattern="^remove_time$"))
        application.add_handler(CallbackQueryHandler(dashboard, pattern="^dashboard$"))
        
        # تنظیم زمان
        application.add_handler(CallbackQueryHandler(select_hour, pattern="^hour_"))
        application.add_handler(CallbackQueryHandler(select_minute, pattern="^minute_"))
        
        # حذف
        application.add_handler(CallbackQueryHandler(confirm_remove, pattern="^confirm_remove$"))
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
