import logging
from datetime import datetime, timedelta, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import urllib.request

# ============ تنظیمات ============
TOKEN = "8724156247:AAH26WN2k9dlI-K3PFgj665F2r1aGRH4OMw"  # توکن جدید بذار

# زمان تهران (UTC+3:30)
TEHRAN_OFFSET = timedelta(hours=3, minutes=30)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# دیکشنری زمان‌بندی‌ها
schedules = {}

# ============ توابع کمکی ============
def now_tehran():
    return datetime.now(timezone.utc) + TEHRAN_OFFSET

def get_chat_type(chat):
    if chat.type == "channel":
        return "کانال"
    elif chat.type in ["group", "supergroup"]:
        return "گروه"
    return "ناشناخته"

def delete_webhook():
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/deleteWebhook"
        with urllib.request.urlopen(url) as response:
            return True
    except:
        return False

# ============ دکمه برگشت ============
def back_button():
    return InlineKeyboardButton("🔙 بازگشت", callback_data="back")

# ============ منوی اصلی ============
async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, edit=False):
    user = update.effective_user
    chat = update.effective_chat
    chat_type = get_chat_type(chat)
    
    text = f"""
<b>🤖 ربات هوشمند زمان‌بندی دیجیاتالی</b>

<b>👋 سلام</b> {user.first_name} عزیز

من یک <b>ربات پیشرفته</b> برای <b>ساعت‌گذاری خودکار</b> گروه‌ها و کانال‌ها هستم.

<b>📌 نوع چت فعلی:</b> {chat_type}

<b>⚙️ قابلیت‌ها:</b>
• تنظیم ساعت ارسال پیام‌های روزانه
• ارسال خودکار در زمان مشخص
• پشتیبانی از گروه و کانال

<b>💡 برای شروع یکی از گزینه‌های زیر را انتخاب کنید:</b>
"""
    
    keyboard = [
        [
            InlineKeyboardButton("⏰ تنظیم زمان", callback_data="set_time"),
            InlineKeyboardButton("📋 مشاهده زمان", callback_data="view_time")
        ],
        [
            InlineKeyboardButton("🗑 حذف زمان‌بندی", callback_data="remove_time"),
            InlineKeyboardButton("📊 وضعیت سیستم", callback_data="system_status")
        ],
        [
            InlineKeyboardButton("❓ راهنمای استفاده", callback_data="help_guide")
        ]
    ]
    
    if edit:
        await update.callback_query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
    else:
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )

# ============ دستور start ============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await main_menu(update, context)

# ============ تنظیم زمان (دکمه‌ای) ============
async def set_time_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = """
<b>⏰ تنظیم زمان ارسال</b>

ساعت مورد نظر را انتخاب کنید:
"""
    
    # ساعت‌ها از ۰ تا ۲۳
    keyboard = []
    row = []
    for hour in range(0, 24):
        row.append(InlineKeyboardButton(f"{hour:02d}", callback_data=f"hour_{hour}"))
        if len(row) == 6:  # ۶ دکمه در هر ردیف
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    keyboard.append([back_button()])
    
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
<b>⏰ تنظیم زمان ارسال</b>

ساعت: <b>{hour:02d}</b>

دقیقه مورد نظر را انتخاب کنید:
"""
    
    # دقیقه‌ها با فواصل ۵ دقیقه
    keyboard = []
    row = []
    for minute in range(0, 60, 5):
        row.append(InlineKeyboardButton(f"{minute:02d}", callback_data=f"minute_{hour}_{minute}"))
        if len(row) == 6:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton("🔙 بازگشت به ساعت", callback_data="set_time")])
    
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
    chat_type = get_chat_type(chat)
    
    # ذخیره زمان
    schedules[chat_id] = {
        "time": time_str,
        "enabled": True,
        "chat_type": chat_type,
        "chat_title": chat.title or chat_id
    }
    
    text = f"""
<b>✅ زمان با موفقیت تنظیم شد</b>

<b>📌 نوع:</b> {chat_type}
<b>🕐 ساعت ارسال:</b> <code>{time_str}</code>
<b>📊 وضعیت:</b> <b>فعال</b>

ربات هر روز در ساعت <b>{time_str}</b> پیام ارسال خواهد کرد.
"""
    
    keyboard = [[back_button()]]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )
    
    logger.info(f"Time set for {chat_id}: {time_str}")

# ============ مشاهده زمان ============
async def view_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    chat = update.effective_chat
    chat_id = str(chat.id)
    chat_type = get_chat_type(chat)
    
    if chat_id not in schedules:
        text = f"""
<b>📋 وضعیت زمان‌بندی</b>

<b>❌ هیچ زمان‌بندی</b> برای این {chat_type} تنظیم نشده است.

برای تنظیم زمان از گزینه <b>تنظیم زمان</b> استفاده کنید.
"""
    else:
        data = schedules[chat_id]
        status = "✅ <b>فعال</b>" if data["enabled"] else "❌ <b>غیرفعال</b>"
        
        text = f"""
<b>📋 جزئیات زمان‌بندی</b>

<b>📌 نوع:</b> {data['chat_type']}
<b>🕐 ساعت ارسال:</b> <code>{data['time']}</code>
<b>📊 وضعیت:</b> {status}

ربات هر روز در ساعت <b>{data['time']}</b> پیام ارسال می‌کند.
"""
    
    keyboard = [[back_button()]]
    
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
    chat_type = get_chat_type(chat)
    
    if chat_id not in schedules:
        text = f"""
<b>🗑 حذف زمان‌بندی</b>

<b>❌ هیچ زمان‌بندی</b> برای این {chat_type} وجود ندارد.
"""
    else:
        data = schedules[chat_id]
        del schedules[chat_id]
        
        text = f"""
<b>✅ زمان‌بندی با موفقیت حذف شد</b>

<b>📌 نوع:</b> {chat_type}
<b>🕐 ساعت حذف شده:</b> <code>{data['time']}</code>

زمان‌بندی این {chat_type} <b>غیرفعال</b> شد.
"""
        logger.info(f"Schedule removed for {chat_id}")
    
    keyboard = [[back_button()]]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

# ============ وضعیت سیستم ============
async def system_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    now = now_tehran()
    total = len(schedules)
    active = sum(1 for s in schedules.values() if s["enabled"])
    
    schedule_list = ""
    if schedules:
        for chat_id, data in list(schedules.items())[:5]:
            status_icon = "✅" if data["enabled"] else "❌"
            schedule_list += f"• {data['chat_type']}: <code>{data['time']}</code> {status_icon}\n"
        if len(schedules) > 5:
            schedule_list += f"... و {len(schedules) - 5} مورد دیگر"
    else:
        schedule_list = "<i>هیچ زمان‌بندی فعالی وجود ندارد</i>"
    
    text = f"""
<b>📊 وضعیت سیستم</b>

<b>⏰ زمان سرور:</b> <code>{now.strftime('%H:%M:%S')}</code>
<b>📅 تاریخ:</b> <code>{now.strftime('%Y/%m/%d')}</code>

<b>📌 آمار زمان‌بندی‌ها:</b>
• <b>کل:</b> {total}
• <b>فعال:</b> {active}
• <b>غیرفعال:</b> {total - active}

<b>📋 لیست زمان‌بندی‌ها:</b>
{schedule_list}

<b>🟢 وضعیت:</b> ربات در حال اجرا
"""
    
    keyboard = [[back_button()]]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

# ============ راهنما ============
async def help_guide(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = """
<b>❓ راهنمای استفاده از ربات</b>

<b>🔹 نحوه کار:</b>
۱. ربات را به <b>گروه</b> یا <b>کانال</b> خود اضافه کنید
۲. از گزینه <b>تنظیم زمان</b> استفاده کنید
۳. ربات هر روز در ساعت مشخص پیام ارسال می‌کند

<b>🔸 نکات مهم:</b>
• ربات باید در گروه/کانال <b>ادمین</b> باشد
• زمان به <b>فرمت ۲۴ ساعته</b> انتخاب می‌شود

<b>🔹 امکانات:</b>
✅ تنظیم زمان ارسال خودکار (دکمه‌ای)
✅ مشاهده زمان‌بندی فعلی
✅ حذف زمان‌بندی
✅ نمایش وضعیت سیستم

<b>⚡️ پشتیبانی:</b>
در صورت بروز مشکل با ادمین تماس بگیرید.
"""
    
    keyboard = [[back_button()]]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

# ============ دکمه برگشت ============
async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await main_menu(update, context, edit=True)

# ============ ارسال خودکار ============
async def auto_send_messages(context: ContextTypes.DEFAULT_TYPE):
    try:
        now = now_tehran()
        current_time = now.strftime("%H:%M")
        today = now.strftime("%Y/%m/%d")
        
        for chat_id, data in list(schedules.items()):
            if data["enabled"] and data["time"] == current_time:
                try:
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=f"""
<b>⏰ اعلان ساعت دیجیاتالی</b>

<b>🕐 زمان:</b> <code>{current_time}</code>
<b>📅 تاریخ:</b> <code>{today}</code>
<b>📌 نوع:</b> {data['chat_type']}

<i>این پیام به صورت خودکار ارسال شده است.</i>
""",
                        parse_mode='HTML'
                    )
                    logger.info(f"✅ Auto message sent to {chat_id}")
                except Exception as e:
                    logger.error(f"❌ Error sending to {chat_id}: {e}")
                    if "chat not found" in str(e) or "bot was blocked" in str(e):
                        data["enabled"] = False
    except Exception as e:
        logger.error(f"Error in auto_send: {e}")

# ============ اجرا ============
def main():
    try:
        delete_webhook()
        
        print("=" * 50)
        print("🚀 راه‌اندازی ربات ساعت دیجیاتالی هوشمند")
        print("=" * 50)
        print(f"📌 توکن: {TOKEN[:10]}...{TOKEN[-5:]}")
        print("=" * 50)
        
        application = Application.builder().token(TOKEN).build()
        
        # دستورات
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_guide))
        
        # دکمه‌ها
        application.add_handler(CallbackQueryHandler(set_time_menu, pattern="^set_time$"))
        application.add_handler(CallbackQueryHandler(select_hour, pattern="^hour_"))
        application.add_handler(CallbackQueryHandler(select_minute, pattern="^minute_"))
        application.add_handler(CallbackQueryHandler(view_time, pattern="^view_time$"))
        application.add_handler(CallbackQueryHandler(remove_time, pattern="^remove_time$"))
        application.add_handler(CallbackQueryHandler(system_status, pattern="^system_status$"))
        application.add_handler(CallbackQueryHandler(help_guide, pattern="^help_guide$"))
        application.add_handler(CallbackQueryHandler(back_to_menu, pattern="^back$"))
        
        # JobQueue
        job_queue = application.job_queue
        if job_queue:
            job_queue.run_repeating(auto_send_messages, interval=60, first=10)
            print("✅ زمان‌بندی خودکار فعال شد")
        
        print("✅ ربات با موفقیت راه‌اندازی شد!")
        print("=" * 50)
        
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )
        
    except Exception as e:
        print(f"❌ خطا در راه‌اندازی: {e}")

if __name__ == "__main__":
    main()
