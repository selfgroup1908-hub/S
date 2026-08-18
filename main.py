import asyncio
import logging
from datetime import datetime
from pytz import timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import re

# ============ تنظیمات ============
# 🔴 توکن جدیدت رو اینجا بذار (بعد از ریست کردن)
TOKEN = "توکن_جدید_خودت_اینجا"  # <--- عوض کن

TEHRAN_TZ = timezone('Asia/Tehran')

# فعال کردن لاگ برای دیباگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# دیکشنری برای ذخیره زمان‌بندی‌ها
schedules = {"groups": {}, "channels": {}}

# ============ دستورات ============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پیام خوشامدگویی"""
    try:
        user = update.effective_user
        chat = update.effective_chat
        chat_type = "کانال" if chat.type == "channel" else "گروه"
        
        text = f"""
✨ **به ربات هوشمند زمان‌بندی خوش آمدید!** ✨

سلام {user.first_name} 👋

من یه **ربات پیشرفته ساعت‌گذاری گروه و کانال** هستم.

⏰ **دستورات:**
/set_time HH:MM - تنظیم ساعت ارسال
/view_schedule - مشاهده زمان‌بندی
/remove_schedule - حذف زمان‌بندی
/status - وضعیت ربات
/start - پیام خوشامد

📌 نوع چت فعلی: {chat_type}
"""
        keyboard = [
            [InlineKeyboardButton("⏰ تنظیم زمان", callback_data="set_time")],
            [InlineKeyboardButton("📋 مشاهده برنامه", callback_data="view_schedule")],
            [InlineKeyboardButton("❓ راهنما", callback_data="help")]
        ]
        
        await update.message.reply_text(
            text, 
            reply_markup=InlineKeyboardMarkup(keyboard), 
            parse_mode='Markdown'
        )
        logger.info(f"User {user.id} started the bot")
    except Exception as e:
        logger.error(f"Error in start: {e}")
        await update.message.reply_text("❌ خطایی رخ داد. دوباره تلاش کنید.")

async def set_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تنظیم زمان ارسال"""
    try:
        chat = update.effective_chat
        chat_id = str(chat.id)
        chat_type = "channels" if chat.type == "channel" else "groups"
        
        if not context.args:
            await update.message.reply_text(
                "⏰ لطفاً زمان را وارد کنید:\n"
                "مثال: `/set_time 14:30`\n"
                "مثال: `/set_time 09:00`",
                parse_mode='Markdown'
            )
            return
        
        time_str = context.args[0]
        
        # اعتبارسنجی زمان
        if not re.match(r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$', time_str):
            await update.message.reply_text(
                "❌ فرمت زمان اشتباه!\n"
                "از فرمت HH:MM استفاده کنید.\n"
                "مثال: 14:30 یا 09:00"
            )
            return
        
        # ذخیره زمان
        schedules[chat_type][chat_id] = {"time": time_str, "enabled": True}
        
        await update.message.reply_text(
            f"✅ زمان با موفقیت تنظیم شد!\n"
            f"🕐 ساعت: {time_str}\n"
            f"📌 نوع: {chat_type}\n"
            f"ربات هر روز در این ساعت پیام ارسال می‌کند."
        )
        logger.info(f"Time set for {chat_id}: {time_str}")
        
    except Exception as e:
        logger.error(f"Error in set_time: {e}")
        await update.message.reply_text("❌ خطا در تنظیم زمان!")

async def view_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مشاهده زمان‌بندی فعلی"""
    try:
        chat = update.effective_chat
        chat_id = str(chat.id)
        chat_type = "channels" if chat.type == "channel" else "groups"
        
        if chat_id in schedules[chat_type]:
            s = schedules[chat_type][chat_id]
            status = "✅ فعال" if s["enabled"] else "❌ غیرفعال"
            await update.message.reply_text(
                f"📋 **زمان‌بندی فعلی**\n"
                f"🕐 ساعت: {s['time']}\n"
                f"📊 وضعیت: {status}\n"
                f"📌 نوع: {chat_type}"
            )
        else:
            await update.message.reply_text(
                f"❌ هیچ زمان‌بندی برای این {chat_type} تنظیم نشده.\n"
                "با دستور /set_time زمان را تنظیم کنید."
            )
    except Exception as e:
        logger.error(f"Error in view_schedule: {e}")
        await update.message.reply_text("❌ خطا!")

async def remove_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """حذف زمان‌بندی"""
    try:
        chat = update.effective_chat
        chat_id = str(chat.id)
        chat_type = "channels" if chat.type == "channel" else "groups"
        
        if chat_id in schedules[chat_type]:
            del schedules[chat_type][chat_id]
            await update.message.reply_text("✅ زمان‌بندی با موفقیت حذف شد.")
            logger.info(f"Schedule removed for {chat_id}")
        else:
            await update.message.reply_text("❌ هیچ زمان‌بندی برای حذف وجود ندارد.")
    except Exception as e:
        logger.error(f"Error in remove_schedule: {e}")
        await update.message.reply_text("❌ خطا!")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """وضعیت ربات"""
    try:
        total_groups = len(schedules["groups"])
        total_channels = len(schedules["channels"])
        
        await update.message.reply_text(
            f"📊 **وضعیت ربات**\n\n"
            f"🔄 گروه‌های فعال: {total_groups}\n"
            f"📢 کانال‌های فعال: {total_channels}\n"
            f"⏰ مجموع: {total_groups + total_channels}\n\n"
            f"🟢 ربات در حال اجراست.",
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error in status: {e}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """راهنما"""
    text = """
📖 **راهنمای ربات**

🔹 **دستورات:**
/start - پیام خوشامد
/set_time HH:MM - تنظیم ساعت ارسال
/view_schedule - مشاهده زمان فعلی
/remove_schedule - حذف زمان‌بندی
/status - وضعیت ربات
/help - این پیام

💡 **نکته:** ربات باید در گروه یا کانال ادمین باشد.
"""
    await update.message.reply_text(text)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت دکمه‌ها"""
    query = update.callback_query
    await query.answer()
    
    try:
        if query.data == "set_time":
            await query.edit_message_text(
                "⏰ از دستور زیر استفاده کنید:\n"
                "`/set_time HH:MM`\n\n"
                "مثال: `/set_time 18:30`",
                parse_mode='Markdown'
            )
        elif query.data == "view_schedule":
            # اینجا باید view_schedule رو صدا بزنی ولی با callback
            await query.edit_message_text("📋 از دستور /view_schedule استفاده کنید.")
        elif query.data == "help":
            await help_command(update, context)
    except Exception as e:
        logger.error(f"Error in button_callback: {e}")

# ============ تابع ارسال خودکار ============
async def send_scheduled_messages(context: ContextTypes.DEFAULT_TYPE):
    """ارسال پیام‌های زمان‌بندی شده"""
    try:
        now = datetime.now(TEHRAN_TZ)
        current_time = now.strftime("%H:%M")
        
        # ارسال به گروه‌ها
        for chat_id, schedule in schedules["groups"].items():
            if schedule["enabled"] and schedule["time"] == current_time:
                try:
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=f"⏰ **ساعت دیجیاتالی هوشمند**\n\n"
                             f"🕐 زمان: {current_time}\n"
                             f"📅 تاریخ: {now.strftime('%Y/%m/%d')}\n\n"
                             f"این پیام به صورت خودکار ارسال شد.",
                        parse_mode='Markdown'
                    )
                    logger.info(f"Message sent to group {chat_id}")
                except Exception as e:
                    logger.error(f"Error sending to group {chat_id}: {e}")
        
        # ارسال به کانال‌ها
        for chat_id, schedule in schedules["channels"].items():
            if schedule["enabled"] and schedule["time"] == current_time:
                try:
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=f"📢 **پست خودکار کانال**\n\n"
                             f"🕐 ساعت: {current_time}\n"
                             f"📅 تاریخ: {now.strftime('%Y/%m/%d')}",
                        parse_mode='Markdown'
                    )
                    logger.info(f"Message sent to channel {chat_id}")
                except Exception as e:
                    logger.error(f"Error sending to channel {chat_id}: {e}")
                    
    except Exception as e:
        logger.error(f"Error in send_scheduled_messages: {e}")

# ============ تابع اصلی ============
def main():
    """راه‌اندازی ربات"""
    try:
        print("🚀 در حال راه‌اندازی ربات...")
        print(f"📌 توکن: {TOKEN[:10]}...")
        
        # ایجاد اپلیکیشن
        application = Application.builder().token(TOKEN).build()
        
        # اضافه کردن هندلرها
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("set_time", set_time))
        application.add_handler(CommandHandler("view_schedule", view_schedule))
        application.add_handler(CommandHandler("remove_schedule", remove_schedule))
        application.add_handler(CommandHandler("status", status_command))
        application.add_handler(CallbackQueryHandler(button_callback))
        
        # اضافه کردن Job برای چک کردن هر دقیقه
        job_queue = application.job_queue
        if job_queue:
            job_queue.run_repeating(send_scheduled_messages, interval=60, first=10)
            print("✅ زمان‌بندی خودکار فعال شد")
        else:
            print("⚠️ JobQueue در دسترس نیست!")
        
        # شروع ربات
        print("🤖 ربات روشن شد! منتظر پیام‌ها هستم...")
        print("💡 برای تست، به ربات /start بفرستید")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        print(f"❌ خطا در راه‌اندازی: {e}")
        print("\n🔍 راه‌حل‌ها:")
        print("1. مطمئن شوید توکن جدید و درست است")
        print("2. اینترنت خود را چک کنید")
        print("3. اگر خطا ادامه داشت، توکن را دوباره ریست کنید")

if __name__ == '__main__':
    main()
