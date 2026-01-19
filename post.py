import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

# --- SABİT BİLGİLER ---
TOKEN = "7890738118:AAEsCMdlel_LzG06cgxeBGLDOIt0EKqANlM"
ADMIN_IDS = [7172270461]
CHANNEL_ID = "@igro_lab"

# --- LOGGING ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# --- GLOBAL DEĞİŞKENLER ---
current_post = None
current_photo_path = None
current_interval = None
last_message_id = None

WAITING_POST, WAITING_INTERVAL = range(2)

# --- /start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("📝 Yeni Post Oluştur", callback_data="new_post")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Hoş geldiniz! Aşağıdan işlemi seçin:",
        reply_markup=reply_markup
    )

# --- Düğme callback ---
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id not in ADMIN_IDS:
        await query.edit_message_text("❌ Bu işlemi yapamazsınız. Admin değilsiniz.")
        return ConversationHandler.END

    if query.data == "new_post":
        await query.edit_message_text(
            "📤 Lütfen göndermek istediğiniz mesajı yazın.\n"
            "İsterseniz fotoğraf + açıklama da gönderebilirsiniz."
        )
        return WAITING_POST

# --- Mesaj ve görsel alındı ---
async def receive_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global current_post, current_photo_path

    if update.message.photo:
        photo_file = await update.message.photo[-1].get_file()
        photo_path = f"temp_{photo_file.file_id}.jpg"
        await photo_file.download_to_drive(photo_path)
        current_photo_path = photo_path
        current_post = update.message.caption or ""
    else:
        current_photo_path = None
        current_post = update.message.text or ""

    await update.message.reply_text(
        "✅ Mesaj kaydedildi.\n"
        "⏱ Şimdi paylaşım süresini **dakika** cinsinden girin:"
    )
    return WAITING_INTERVAL

# --- Süre alındı ---
async def receive_interval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global current_interval

    try:
        minutes = int(update.message.text)
    except ValueError:
        await update.message.reply_text("❌ Lütfen geçerli bir sayı girin.")
        return WAITING_INTERVAL

    current_interval = minutes
    job_queue = context.application.job_queue

    # Önceki job'ları iptal et
    for job in job_queue.jobs():
        job.schedule_removal()

    job_queue.run_repeating(
        send_post,
        interval=minutes * 60,
        first=0
    )

    await update.message.reply_text(
        f"✅ Post ayarlandı!\n"
        f"📢 Her {minutes} dakikada bir kanala gönderilecek."
    )
    return ConversationHandler.END

# --- Post paylaşım ---
async def send_post(context: ContextTypes.DEFAULT_TYPE):
    global last_message_id, current_post, current_photo_path

    # Eski mesajı sil
    if last_message_id:
        try:
            await context.bot.delete_message(
                chat_id=CHANNEL_ID,
                message_id=last_message_id
            )
        except:
            pass

    try:
        if current_photo_path:
            with open(current_photo_path, "rb") as f:
                msg = await context.bot.send_photo(
                    chat_id=CHANNEL_ID,
                    photo=f,
                    caption=current_post
                )
        else:
            msg = await context.bot.send_message(
                chat_id=CHANNEL_ID,
                text=current_post
            )

        last_message_id = msg.message_id

    except Exception as e:
        logging.error(f"Post gönderilemedi: {e}")

# --- /stoppost ---
async def stoppost(update: Update, context: ContextTypes.DEFAULT_TYPE):
    job_queue = context.application.job_queue
    for job in job_queue.jobs():
        job.schedule_removal()

    await update.message.reply_text("⏹ Post paylaşımı durduruldu.")

# --- MAIN ---
def main():
    app = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CallbackQueryHandler(button)
        ],
        states={
            WAITING_POST: [
                MessageHandler(
                    (filters.TEXT | filters.PHOTO) & ~filters.COMMAND,
                    receive_post
                )
            ],
            WAITING_INTERVAL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_interval)
            ],
        },
        fallbacks=[CommandHandler("stoppost", stoppost)],
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("stoppost", stoppost))

    app.run_polling()

if __name__ == "__main__":
    main()
