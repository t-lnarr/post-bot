import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# Railway environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

# Global değişkenler
post_gorevi = None
son_mesaj_id = None
kaydedilen_mesaj = None
post_suresi = None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start komutu"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Bu botu sadece admin kullanabilir.")
        return
    
    keyboard = [[InlineKeyboardButton("📝 Post Oluştur", callback_data="yeni_post")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "Merhaba! Oto-post botuna hoş geldin.\n\n"
        "Kullanım:\n"
        "• Post Oluştur: Yeni oto-post başlat\n"
        "• /stop: Oto-postu durdur",
        reply_markup=reply_markup
    )

async def yeni_post_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Post oluşturma başlat"""
    query = update.callback_query
    await query.answer()
    
    context.user_data['adim'] = 'mesaj_bekle'
    await query.edit_message_text(
        "📩 Göndermek istediğin mesajı yaz veya görseli gönder:"
    )

async def mesaj_al(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kullanıcıdan mesaj al"""
    if update.effective_user.id != ADMIN_ID:
        return
    
    global kaydedilen_mesaj
    
    adim = context.user_data.get('adim')
    
    if adim == 'mesaj_bekle':
        # Mesajı kaydet
        kaydedilen_mesaj = update.message
        context.user_data['adim'] = 'sure_bekle'
        
        await update.message.reply_text(
            "✅ Mesaj kaydedildi!\n\n"
            "⏰ Kaç saniyede bir gönderilsin?\n"
            "Örnek: 300 (5 dakika)"
        )
    
    elif adim == 'sure_bekle':
        global post_suresi, post_gorevi
        
        try:
            post_suresi = int(update.message.text)
            
            if post_suresi < 10:
                await update.message.reply_text("❌ Süre en az 10 saniye olmalı!")
                return
            
            # Oto-post başlat
            post_gorevi = asyncio.create_task(oto_post_loop(context.application.bot))
            
            await update.message.reply_text(
                f"✅ Oto-post başlatıldı!\n\n"
                f"📊 Her {post_suresi} saniyede bir gönderilecek.\n"
                f"🛑 Durdurmak için /stop yaz."
            )
            
            context.user_data.clear()
            
        except ValueError:
            await update.message.reply_text("❌ Lütfen sadece sayı gir! Örnek: 300")

async def oto_post_loop(bot):
    """Oto-post döngüsü"""
    global son_mesaj_id
    
    while True:
        try:
            # Eski mesajı sil
            if son_mesaj_id:
                try:
                    await bot.delete_message(chat_id=CHANNEL_ID, message_id=son_mesaj_id)
                except:
                    pass
            
            # Yeni mesaj gönder
            if kaydedilen_mesaj.photo:
                sent = await bot.send_photo(
                    chat_id=CHANNEL_ID,
                    photo=kaydedilen_mesaj.photo[-1].file_id,
                    caption=kaydedilen_mesaj.caption
                )
            elif kaydedilen_mesaj.video:
                sent = await bot.send_video(
                    chat_id=CHANNEL_ID,
                    video=kaydedilen_mesaj.video.file_id,
                    caption=kaydedilen_mesaj.caption
                )
            elif kaydedilen_mesaj.document:
                sent = await bot.send_document(
                    chat_id=CHANNEL_ID,
                    document=kaydedilen_mesaj.document.file_id,
                    caption=kaydedilen_mesaj.caption
                )
            else:
                sent = await bot.send_message(
                    chat_id=CHANNEL_ID,
                    text=kaydedilen_mesaj.text
                )
            
            son_mesaj_id = sent.message_id
            print(f"✅ Mesaj gönderildi: {son_mesaj_id}")
            
        except Exception as e:
            print(f"❌ Hata: {e}")
        
        await asyncio.sleep(post_suresi)

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Oto-postu durdur"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Bu botu sadece admin kullanabilir.")
        return
    
    global post_gorevi, son_mesaj_id, kaydedilen_mesaj, post_suresi
    
    if post_gorevi:
        post_gorevi.cancel()
        post_gorevi = None
        
        # Son mesajı sil
        if son_mesaj_id:
            try:
                await context.bot.delete_message(chat_id=CHANNEL_ID, message_id=son_mesaj_id)
                son_mesaj_id = None
            except:
                pass
        
        kaydedilen_mesaj = None
        post_suresi = None
        
        keyboard = [[InlineKeyboardButton("📝 Yeni Post Oluştur", callback_data="yeni_post")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🛑 Oto-post durduruldu ve mesaj silindi!",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text("❌ Zaten aktif bir post yok!")

def main():
    """Botu başlat"""
    if not BOT_TOKEN or not CHANNEL_ID or not ADMIN_ID:
        print("❌ HATA: Environment variables eksik!")
        print("Gerekli: BOT_TOKEN, CHANNEL_ID, ADMIN_ID")
        return
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CallbackQueryHandler(yeni_post_callback, pattern="yeni_post"))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, mesaj_al))
    
    print("✅ Bot başlatıldı!")
    app.run_polling()

if __name__ == "__main__":
    main()
