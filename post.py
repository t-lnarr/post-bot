import os
import asyncio
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID"))
CHANNEL_ID = os.environ.get("CHANNEL_ID")

post_data = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    await update.message.reply_text(
        "Merhaba admin 😎\n"
        "/post <dakika> yazarak otomatik post başlatabilirsin."
    )

async def post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    if not context.args:
        await update.message.reply_text("Örnek kullanım: /post 10")
        return

    minutes = int(context.args[0])
    post_data["interval"] = minutes * 60

    await update.message.reply_text(
        "Şimdi gönderilecek mesajı at.\n"
        "(Fotoğraflı veya normal mesaj olabilir)"
    )

async def get_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    post_data["message"] = update.message

    if not post_data.get("running"):
        post_data["running"] = True
        asyncio.create_task(auto_post(context))

    await update.message.reply_text("Otomatik post başladı 🚀")

async def auto_post(context: ContextTypes.DEFAULT_TYPE):
    while True:
        msg = post_data["message"]

        if msg.photo:
            await context.bot.send_photo(
                chat_id=CHANNEL_ID,
                photo=msg.photo[-1].file_id,
                caption=msg.caption
            )
        else:
            await context.bot.send_message(
                chat_id=CHANNEL_ID,
                text=msg.text
            )

        await asyncio.sleep(post_data["interval"])

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("post", post))
    app.add_handler(MessageHandler(filters.ALL, get_message))

    print("Bot Railway'de çalışıyor 🔥")
    app.run_polling()

if __name__ == "__main__":
    main()
