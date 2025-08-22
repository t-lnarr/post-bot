from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import logging

# --- LOGGING ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# --- GLOBAL DEĞİŞKENLER ---
current_post = None
current_interval = None
last_message_id = None
channel_id = "@igro_store_tm"   # Kendi kanal @username sini buraya yaz

# --- /setpost KOMUTU ---
async def setpost(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global current_post, current_interval

    if len(context.args) < 2:
        await update.message.reply_text("Kullanım: /setpost <dakika> <mesaj>")
        return

    try:
        minutes = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Dakika bir sayı olmalı.")
        return

    text = " ".join(context.args[1:])

    current_post = text
    current_interval = minutes

    # Job reset
    job_queue = context.job_queue
    job_queue.jobs.clear()  # önceki işleri sil
    job_queue.run_repeating(send_post, interval=minutes * 60, first=0)

    await update.message.reply_text(
        f"✅ Yeni post ayarlandı.\nHer {minutes} dakikada bir şu post paylaşılacak:\n\n{text}"
    )

# --- PAYLAŞIM FONKSİYONU ---
async def send_post(context: ContextTypes.DEFAULT_TYPE):
    global last_message_id, current_post, channel_id

    # Eski mesajı sil
    if last_message_id:
        try:
            await context.bot.delete_message(chat_id=channel_id, message_id=last_message_id)
        except Exception as e:
            print("Silme hatası:", e)

    # Yeni mesaj gönder
    msg = await context.bot.send_message(chat_id=channel_id, text=current_post)
    last_message_id = msg.message_id

# --- MAIN ---
def main():
    TOKEN = "7530124206:AAEIzoQ7sKlGbybuqWh4Uq7IyGmW_6eDolM"

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("setpost", setpost))

    app.run_polling()

if __name__ == "__main__":
    main()
