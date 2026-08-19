import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import re
import os

# ============ تنظیمات ============
TOKEN = "8724156247:AAH26WN2k9dlI-K3PFgj665F2r1aGRH4OMw"  # توکن جدید بذار

# زمان تهران (UTC+3:30)
TEHRAN = timedelta(hours=3, minutes=30)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# دیکشنری زمان‌بندی‌ها
schedules = {}

# ============ توابع کمکی ============
def now_tehran():
    return datetime.utcnow() + TEHRAN

def get_chat_type(chat):
    if chat.type == "channel":
        return "کانال"
    elif chat.type in ["group", "supergroup"]:
        return "گروه"
    return "ناشناخته"

def is_valid_time(time_str):
    return bool(re.match(r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$', time_str))

# ============ دستورات ============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    chat_type = get_chat_type(chat)
    
    text = f"""
✨ به ربات هوشمند زمان‌بندی خوش آمدید! ✨

سلام {user.first_name} 👋

من یک ربات پیشرفته ساعت‌گذاری گروه و کانال هستم.

نوع چت فعلی: {chat_type}

دستورات:
/set_time HH:MM - تنظیم ساعت ارسال
/view - مشاهده زمان‌بندی فعلی
/remove - حذف زمان‌بندی
/status - وضعیت ربات
/help - راهنمای کامل

نکته: برای تنظیم زمان از فرمت ۲۴ ساعته استفاده کنید.
"""
    
    keyboard = [
        [
            InlineKeyboardButton("⏰ تنظیم زمان", callback_data="set"),
            InlineKeyboardButton("📋 مشاهده", callback_data="view")
        ],
        [
            InlineKeyboardButton("❌ حذف", callback_data="remove"),
            InlineKeyboardButton("📊 وضعیت", callback_data="status")
        ],
        [
            InlineKeyboardButton("❓ راهنما", callback_data="help")
        ]
    ]
    
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = """
📖 راهنمای کامل ربات

دستورات:
/start - نمایش پیام خوشامد
/set_time HH:MM - تنظیم ساعت ارسال
/view - مشاهده زمان تنظیم شده
/remove - حذف زمان‌بندی
/status - مشاهده وضعیت ربات
/help - نمایش این راهنما

نحوه استفاده:
1. ربات را به گروه یا کانال خود اضافه کنید
2. با دستور /set_time زمان را تنظیم کنید
3. ربات هر روز در ساعت مشخص پیام ارسال می‌کند

توجه:
- ربات باید در گروه/کانال ادمین باشد
- زمان به فرمت ۲۴ ساعته وارد شود
- مثال: /set_time 14:30
"""
    await update.message.reply_text(text)

async def set_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    chat_id = str(chat.id)
    chat_type = get_chat_type(chat)
    
    if not context.args:
        await update.message.reply_text(
            f"⏰ لطفاً زمان را به فرمت HH:MM وارد کنید.\n"
            f"مثال: /set_time 14:30\n\n"
            f"نوع چت: {chat_type}"
        )
        return
    
    time_str = context.args[0]
    
    if not is_valid_time(time_str):
        await update.message.reply_text(
            "❌ فرمت زمان نامعتبر!\n\n"
            "لطفاً از فرمت HH:MM استفاده کنید.\n"
            "مثال: 14:30 یا 09:00"
        )
        return
    
    schedules[chat_id] = {
        "time": time_str,
        "enabled": True,
        "chat_type": chat_type,
        "chat_title": chat.title or chat_id
    }
    
    await update.message.reply_text(
        f"✅ زمان با موفقیت تنظیم شد!\n\n"
        f"نوع: {chat_type}\n"
        f"ساعت ارسال: {time_str}\n"
        f"وضعیت: فعال\n\n"
        f"ربات هر روز در این ساعت پیام ارسال خواهد کرد."
    )
    
    logger.info(f"Time set for {chat_id}: {time_str}")

async def view_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    chat_id = str(chat.id)
    
    if chat_id not in schedules:
        await update.message.reply_text(
            "❌ هیچ زمان‌بندی تنظیم نشده است.\n\n"
            "با دستور /set_time HH:MM زمان را تنظیم کنید."
        )
        return
    
    data = schedules[chat_id]
    status = "✅ فعال" if data["enabled"] else "❌ غیرفعال"
    
    await update.message.reply_text(
        f"📋 زمان‌بندی فعلی\n\n"
        f"نوع: {data['chat_type']}\n"
        f"ساعت: {data['time']}\n"
        f"وضعیت: {status}"
    )

async def remove_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    chat_id = str(chat.id)
    
    if chat_id not in schedules:
        await update.message.reply_text("❌ هیچ زمان‌بندی برای حذف وجود ندارد.")
        return
    
    del schedules[chat_id]
    
    await update.message.reply_text("✅ زمان‌بندی با موفقیت حذف شد!")
    logger.info(f"Schedule removed for {chat_id}")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    now = now_tehran()
    total = len(schedules)
    active = sum(1 for s in schedules.values() if s["enabled"])
    
    await update.message.reply_text(
        f"📊 وضعیت ربات\n\n"
        f"⏰ زمان سرور: {now.strftime('%H:%M:%S')}\n"
        f"📅 تاریخ: {now.strftime('%Y/%m/%d')}\n\n"
        f"تعداد کل زمان‌بندی‌ها: {total}\n"
        f"فعال: {active}\n"
        f"غیرفعال: {total - active}\n\n"
        f"🟢 ربات در حال اجراست."
    )

# ============ مدیریت دکمه‌ها ============
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "set":
        await query.edit_message_text(
            "⏰ تنظیم زمان\n\n"
            "از دستور زیر استفاده کنید:\n"
            "/set_time HH:MM\n\n"
            "مثال: /set_time 18:30"
        )
    
    elif query.data == "view":
        chat_id = str(update.effective_chat.id)
        if chat_id in schedules:
            data = schedules[chat_id]
            status = "✅ فعال" if data["enabled"] else "❌ غیرفعال"
            text = f"📋 زمان‌بندی فعلی\n\nساعت: {data['time']}\nوضعیت: {status}"
        else:
            text = "❌ هیچ زمان‌بندی تنظیم نشده است."
        await query.edit_message_text(text)
    
    elif query.data == "remove":
        chat_id = str(update.effective_chat.id)
        if chat_id in schedules:
            del schedules[chat_id]
            await query.edit_message_text("✅ زمان‌بندی با موفقیت حذف شد!")
        else:
            await query.edit_message_text("❌ هیچ زمان‌بندی برای حذف وجود ندارد.")
    
    elif query.data == "status":
        now = now_tehran()
        total = len(schedules)
        active = sum(1 for s in schedules.values() if s["enabled"])
        await query.edit_message_text(
            f"📊 وضعیت ربات\n\n"
            f"⏰ زمان: {now.strftime('%H:%M:%S')}\n"
            f"کل تنظیمات: {total}\n"
            f"فعال: {active}"
        )
    
    elif query.data == "help":
        await query.edit_message_text(
            "📖 راهنمای سریع\n\n"
            "/start - پیام خوشامد\n"
            "/set_time - تنظیم ساعت\n"
            "/view - مشاهده زمان\n"
            "/remove - حذف زمان‌بندی\n"
            "/status - وضعیت ربات\n"
            "/help - راهنمای کامل"
        )

# ============ ارسال خودکار ============
async def auto_send_messages(context: ContextTypes.DEFAULT_TYPE):
    now = now_tehran()
    current_time = now.strftime("%H:%M")
    today = now.strftime("%Y/%m/%d")
    
    for chat_id, data in list(schedules.items()):
        if data["enabled"] and data["time"] == current_time:
            try:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"⏰ ساعت دیجیاتالی هوشمند\n\n"
                         f"زمان: {current_time}\n"
                         f"تاریخ: {today}\n\n"
                         f"این پیام به صورت خودکار ارسال شد."
                )
                logger.info(f"✅ Message sent to {chat_id}")
            except Exception as e:
                logger.error(f"❌ Error sending to {chat_id}: {e}")
                if "chat not found" in str(e) or "bot was blocked" in str(e):
                    data["enabled"] = False

# ============ اجرا ============
def main():
    try:
        print("=" * 50)
        print("🚀 راه‌اندازی ربات ساعت دیجیاتالی هوشمند")
        print("=" * 50)
        print(f"📌 توکن: {TOKEN[:10]}...{TOKEN[-5:]}")
        print("=" * 50)
        
        application = Application.builder().token(TOKEN).build()
        
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("set_time", set_time))
        application.add_handler(CommandHandler("view", view_schedule))
        application.add_handler(CommandHandler("remove", remove_schedule))
        application.add_handler(CommandHandler("status", status_command))
        application.add_handler(CallbackQueryHandler(button_callback))
        
        job_queue = application.job_queue
        if job_queue:
            job_queue.run_repeating(auto_send_messages, interval=60, first=10)
            print("✅ زمان‌بندی خودکار فعال شد")
        
        print("✅ ربات با موفقیت راه‌اندازی شد!")
        print("=" * 50)
        
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        print(f"❌ خطا در راه‌اندازی: {e}")

if __name__ == "__main__":
    main()
