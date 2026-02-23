import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Chat
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from telegram.error import TelegramError

# Railway ortam değişkenleri
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

# Global değişkenler: her kanal için ayrı görev
# Yapı: { channel_id: { 'gorev': Task, 'mesaj_id': int, 'kaydedilen_mesaj': Message, 'sure': int } }
kanal_verileri = {}

# ─────────────────────────────────────────────
# Yardımcı fonksiyonlar
# ─────────────────────────────────────────────

async def admin_kanallarini_getir(bot) -> list[dict]:
    """Botun admin olduğu kanalların listesini döndürür."""
    kanallar = []
    updates = await bot.get_updates(limit=100, timeout=0)
    
    # Bot'un bulunduğu chatleri bulmak için ChatMemberUpdated geçmişini kontrol ederiz.
    # Daha güvenilir yol: kullanıcının daha önce kaydettiği kanalları saklamak.
    # Telegram API'si direkt kanal listesi vermez; bu yüzden /kanallar_yenile ile
    # kullanıcı kanallarını manuel olarak ekleyebilir.
    return kanallar

# ─────────────────────────────────────────────
# /start komutu
# ─────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Bu botu sadece admin kullanabilir.")
        return

    keyboard = [
        [InlineKeyboardButton("📝 Yeni Post Oluştur", callback_data="yeni_post")],
        [InlineKeyboardButton("📋 Aktif Postları Gör", callback_data="aktif_postlar")],
    ]
    await update.message.reply_text(
        "👋 Oto-Post Botuna Hoş Geldin!\n\n"
        "📌 *Kullanım:*\n"
        "• Bot'u kanalına admin olarak ekle\n"
        "• *Yeni Post Oluştur* butonuna bas\n"
        "• Kanalını seç, içeriği gönder, süreyi belirt\n"
        "• /durdur <kanal\\_id> ile belirli kanalı durdur\n"
        "• /hepsini\\_durdur ile tümünü durdur",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

# ─────────────────────────────────────────────
# Kanal listesi alma (bot'un adminliğini kontrol eder)
# ─────────────────────────────────────────────

async def yeni_post_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if update.effective_user.id != ADMIN_ID:
        return

    # Kaydedilmiş kanal ID'lerini context.bot_data'dan al
    kayitli_kanallar: dict = context.bot_data.get("kanallar", {})

    if not kayitli_kanallar:
        await query.edit_message_text(
            "⚠️ Henüz kayıtlı kanal yok.\n\n"
            "Botun admin olduğu kanalın ID'sini şu şekilde ekle:\n"
            "`/kanal_ekle -100xxxxxxxxxx`\n\n"
            "Kanal ID'sini öğrenmek için @userinfobot'u kullanabilirsin.",
            parse_mode="Markdown",
        )
        return

    # Kanal seçim butonları
    butonlar = []
    for kanal_id, kanal_adi in kayitli_kanallar.items():
        durum = "🟢" if kanal_id in kanal_verileri else "⚫"
        butonlar.append([
            InlineKeyboardButton(
                f"{durum} {kanal_adi}",
                callback_data=f"kanal_sec:{kanal_id}"
            )
        ])
    butonlar.append([InlineKeyboardButton("❌ İptal", callback_data="iptal")])

    await query.edit_message_text(
        "📡 *Hangi kanala post atmak istiyorsun?*\n\n"
        "🟢 = Zaten aktif   ⚫ = Pasif",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(butonlar),
    )

# ─────────────────────────────────────────────
# Kanal seçimi
# ─────────────────────────────────────────────

async def kanal_sec_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if update.effective_user.id != ADMIN_ID:
        return

    kanal_id = query.data.split(":")[1]
    context.user_data["secilen_kanal"] = kanal_id
    context.user_data["adim"] = "mesaj_bekle"

    kayitli_kanallar = context.bot_data.get("kanallar", {})
    kanal_adi = kayitli_kanallar.get(kanal_id, kanal_id)

    await query.edit_message_text(
        f"✅ Seçilen kanal: *{kanal_adi}*\n\n"
        "📩 Şimdi göndermek istediğin mesajı, görseli veya videoyu gönder:",
        parse_mode="Markdown",
    )

# ─────────────────────────────────────────────
# Aktif postları göster
# ─────────────────────────────────────────────

async def aktif_postlar_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not kanal_verileri:
        await query.edit_message_text("📭 Şu an aktif post bulunmuyor.")
        return

    kayitli_kanallar = context.bot_data.get("kanallar", {})
    metin = "📊 *Aktif Postlar:*\n\n"
    butonlar = []

    for kanal_id, veri in kanal_verileri.items():
        kanal_adi = kayitli_kanallar.get(kanal_id, kanal_id)
        metin += f"• {kanal_adi} — Her *{veri['sure']}* saniyede bir\n"
        butonlar.append([
            InlineKeyboardButton(
                f"🛑 {kanal_adi} Durdur",
                callback_data=f"durdur:{kanal_id}"
            )
        ])

    butonlar.append([InlineKeyboardButton("🔙 Geri", callback_data="ana_menu")])
    await query.edit_message_text(
        metin,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(butonlar),
    )

# ─────────────────────────────────────────────
# Buton ile durdur
# ─────────────────────────────────────────────

async def durdur_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    kanal_id = query.data.split(":")[1]
    await _kanali_durdur(kanal_id, context.bot)

    kayitli_kanallar = context.bot_data.get("kanallar", {})
    kanal_adi = kayitli_kanallar.get(kanal_id, kanal_id)
    await query.edit_message_text(f"🛑 *{kanal_adi}* kanalındaki oto-post durduruldu ve son mesaj silindi.", parse_mode="Markdown")

async def ana_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("📝 Yeni Post Oluştur", callback_data="yeni_post")],
        [InlineKeyboardButton("📋 Aktif Postları Gör", callback_data="aktif_postlar")],
    ]
    await query.edit_message_text("Ana menü:", reply_markup=InlineKeyboardMarkup(keyboard))

async def iptal_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data.clear()
    await query.edit_message_text("❌ İşlem iptal edildi.")

# ─────────────────────────────────────────────
# Mesaj & süre alma
# ─────────────────────────────────────────────

async def mesaj_al(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    adim = context.user_data.get("adim")

    if adim == "mesaj_bekle":
        context.user_data["kaydedilen_mesaj"] = update.message
        context.user_data["adim"] = "sure_bekle"

        await update.message.reply_text(
            "✅ İçerik kaydedildi!\n\n"
            "⏰ Kaç saniyede bir gönderilsin? (En az 10)\n"
            "Örnek: *300* (5 dakika)",
            parse_mode="Markdown",
        )

    elif adim == "sure_bekle":
        try:
            sure = int(update.message.text)
            if sure < 10:
                await update.message.reply_text("❌ Süre en az 10 saniye olmalı!")
                return

            kanal_id = context.user_data.get("secilen_kanal")
            kaydedilen_mesaj = context.user_data.get("kaydedilen_mesaj")

            if not kanal_id or not kaydedilen_mesaj:
                await update.message.reply_text("⚠️ Bir hata oluştu. Lütfen /start ile yeniden başla.")
                context.user_data.clear()
                return

            # Eğer bu kanal için zaten görev varsa durdur
            if kanal_id in kanal_verileri:
                await _kanali_durdur(kanal_id, context.bot)

            # Yeni görevi başlat
            gorev = asyncio.create_task(
                oto_post_loop(context.application.bot, kanal_id, kaydedilen_mesaj, sure)
            )
            kanal_verileri[kanal_id] = {
                "gorev": gorev,
                "mesaj_id": None,
                "sure": sure,
            }

            kayitli_kanallar = context.bot_data.get("kanallar", {})
            kanal_adi = kayitli_kanallar.get(kanal_id, kanal_id)

            await update.message.reply_text(
                f"🚀 Oto-post başlatıldı!\n\n"
                f"📡 Kanal: *{kanal_adi}*\n"
                f"⏱ Süre: Her *{sure}* saniyede bir\n\n"
                f"🛑 Durdurmak için: /durdur `{kanal_id}`",
                parse_mode="Markdown",
            )
            context.user_data.clear()

        except ValueError:
            await update.message.reply_text("❌ Lütfen sadece sayı gir! Örnek: 300")

# ─────────────────────────────────────────────
# Oto-post döngüsü
# ─────────────────────────────────────────────

async def oto_post_loop(bot, kanal_id: str, mesaj, sure: int):
    while True:
        try:
            # Eski mesajı sil
            eski_mesaj_id = kanal_verileri.get(kanal_id, {}).get("mesaj_id")
            if eski_mesaj_id:
                try:
                    await bot.delete_message(chat_id=kanal_id, message_id=eski_mesaj_id)
                except TelegramError:
                    pass

            # Yeni mesajı gönder
            sent = await _mesaj_gonder(bot, kanal_id, mesaj)

            if sent and kanal_id in kanal_verileri:
                kanal_verileri[kanal_id]["mesaj_id"] = sent.message_id
                print(f"✅ [{kanal_id}] Mesaj gönderildi: {sent.message_id}")

        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"❌ [{kanal_id}] Hata: {e}")

        await asyncio.sleep(sure)

async def _mesaj_gonder(bot, kanal_id: str, mesaj):
    """Mesaj tipine göre uygun gönderim yöntemini kullan."""
    caption = mesaj.caption
    parse_mode = "HTML"

    if mesaj.photo:
        return await bot.send_photo(
            chat_id=kanal_id,
            photo=mesaj.photo[-1].file_id,
            caption=caption,
            parse_mode=parse_mode if caption else None,
        )
    elif mesaj.video:
        return await bot.send_video(
            chat_id=kanal_id,
            video=mesaj.video.file_id,
            caption=caption,
            parse_mode=parse_mode if caption else None,
        )
    elif mesaj.animation:
        return await bot.send_animation(
            chat_id=kanal_id,
            animation=mesaj.animation.file_id,
            caption=caption,
            parse_mode=parse_mode if caption else None,
        )
    elif mesaj.document:
        return await bot.send_document(
            chat_id=kanal_id,
            document=mesaj.document.file_id,
            caption=caption,
            parse_mode=parse_mode if caption else None,
        )
    elif mesaj.audio:
        return await bot.send_audio(
            chat_id=kanal_id,
            audio=mesaj.audio.file_id,
            caption=caption,
            parse_mode=parse_mode if caption else None,
        )
    elif mesaj.voice:
        return await bot.send_voice(
            chat_id=kanal_id,
            voice=mesaj.voice.file_id,
            caption=caption,
            parse_mode=parse_mode if caption else None,
        )
    elif mesaj.sticker:
        return await bot.send_sticker(chat_id=kanal_id, sticker=mesaj.sticker.file_id)
    elif mesaj.text:
        return await bot.send_message(
            chat_id=kanal_id,
            text=mesaj.text,
            parse_mode=parse_mode,
            entities=mesaj.entities or None,
        )
    return None

# ─────────────────────────────────────────────
# Durdurma yardımcısı
# ─────────────────────────────────────────────

async def _kanali_durdur(kanal_id: str, bot):
    if kanal_id not in kanal_verileri:
        return

    veri = kanal_verileri.pop(kanal_id)
    veri["gorev"].cancel()

    if veri.get("mesaj_id"):
        try:
            await bot.delete_message(chat_id=kanal_id, message_id=veri["mesaj_id"])
        except TelegramError:
            pass

# ─────────────────────────────────────────────
# /durdur komutu
# ─────────────────────────────────────────────

async def durdur(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Bu botu sadece admin kullanabilir.")
        return

    if not context.args:
        if not kanal_verileri:
            await update.message.reply_text("❌ Zaten aktif bir post yok!")
            return
        # Kanal listesi göster
        kayitli_kanallar = context.bot_data.get("kanallar", {})
        butonlar = []
        for k_id in kanal_verileri:
            k_adi = kayitli_kanallar.get(k_id, k_id)
            butonlar.append([InlineKeyboardButton(f"🛑 {k_adi}", callback_data=f"durdur:{k_id}")])
        await update.message.reply_text(
            "Hangi kanalı durdurmak istiyorsun?",
            reply_markup=InlineKeyboardMarkup(butonlar),
        )
        return

    kanal_id = context.args[0]
    if kanal_id not in kanal_verileri:
        await update.message.reply_text(f"❌ `{kanal_id}` için aktif post yok.", parse_mode="Markdown")
        return

    await _kanali_durdur(kanal_id, context.bot)
    await update.message.reply_text(f"🛑 `{kanal_id}` kanalındaki oto-post durduruldu.", parse_mode="Markdown")

# ─────────────────────────────────────────────
# /hepsini_durdur komutu
# ─────────────────────────────────────────────

async def hepsini_durdur(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Bu botu sadece admin kullanabilir.")
        return

    if not kanal_verileri:
        await update.message.reply_text("❌ Zaten aktif post yok!")
        return

    kanallar = list(kanal_verileri.keys())
    for k in kanallar:
        await _kanali_durdur(k, context.bot)

    await update.message.reply_text(f"🛑 {len(kanallar)} kanaldaki tüm oto-postlar durduruldu.")

# ─────────────────────────────────────────────
# /kanal_ekle komutu
# ─────────────────────────────────────────────

async def kanal_ekle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Bu botu sadece admin kullanabilir.")
        return

    if not context.args:
        await update.message.reply_text(
            "Kullanım: `/kanal_ekle -100xxxxxxxxxx`\n\n"
            "Kanal ID'sini öğrenmek için @userinfobot kullanabilirsin.",
            parse_mode="Markdown",
        )
        return

    kanal_id = context.args[0]

    # Bot'un o kanalda admin olup olmadığını kontrol et
    try:
        chat: Chat = await context.bot.get_chat(kanal_id)
        bot_uye = await context.bot.get_chat_member(kanal_id, (await context.bot.get_me()).id)

        if bot_uye.status not in ("administrator", "creator"):
            await update.message.reply_text(
                f"⚠️ Bot bu kanalda admin değil!\n"
                f"Lütfen botu *{chat.title}* kanalına admin olarak ekle.",
                parse_mode="Markdown",
            )
            return

        if "kanallar" not in context.bot_data:
            context.bot_data["kanallar"] = {}

        context.bot_data["kanallar"][kanal_id] = chat.title or kanal_id

        await update.message.reply_text(
            f"✅ Kanal eklendi: *{chat.title}* (`{kanal_id}`)",
            parse_mode="Markdown",
        )

    except TelegramError as e:
        await update.message.reply_text(f"❌ Hata: {e}\n\nKanal ID'sini doğru girdiğinden emin ol.")

# ─────────────────────────────────────────────
# /kanallar komutu
# ─────────────────────────────────────────────

async def kanallar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Bu botu sadece admin kullanabilir.")
        return

    kayitli_kanallar = context.bot_data.get("kanallar", {})
    if not kayitli_kanallar:
        await update.message.reply_text(
            "📭 Kayıtlı kanal yok.\n\nEklemek için: `/kanal_ekle -100xxxxxxxxxx`",
            parse_mode="Markdown",
        )
        return

    metin = "📡 *Kayıtlı Kanallar:*\n\n"
    for k_id, k_adi in kayitli_kanallar.items():
        durum = "🟢 Aktif" if k_id in kanal_verileri else "⚫ Pasif"
        metin += f"• {k_adi} — `{k_id}` {durum}\n"

    await update.message.reply_text(metin, parse_mode="Markdown")

# ─────────────────────────────────────────────
# /kanal_sil komutu
# ─────────────────────────────────────────────

async def kanal_sil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    if not context.args:
        await update.message.reply_text("Kullanım: `/kanal_sil -100xxxxxxxxxx`", parse_mode="Markdown")
        return

    kanal_id = context.args[0]
    kanallar_dict = context.bot_data.get("kanallar", {})

    if kanal_id not in kanallar_dict:
        await update.message.reply_text("❌ Bu kanal kayıtlı değil.")
        return

    if kanal_id in kanal_verileri:
        await _kanali_durdur(kanal_id, context.bot)

    del kanallar_dict[kanal_id]
    await update.message.reply_text(f"🗑 Kanal silindi: `{kanal_id}`", parse_mode="Markdown")

# ─────────────────────────────────────────────
# Ana fonksiyon
# ─────────────────────────────────────────────

def main():
    if not BOT_TOKEN or not ADMIN_ID:
        print("❌ HATA: Ortam değişkenleri eksik!")
        print("Gerekli: BOT_TOKEN, ADMIN_ID")
        return

    app = Application.builder().token(BOT_TOKEN).build()

    # Komutlar
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("durdur", durdur))
    app.add_handler(CommandHandler("hepsini_durdur", hepsini_durdur))
    app.add_handler(CommandHandler("kanal_ekle", kanal_ekle))
    app.add_handler(CommandHandler("kanal_sil", kanal_sil))
    app.add_handler(CommandHandler("kanallar", kanallar))

    # Callback butonlar
    app.add_handler(CallbackQueryHandler(yeni_post_callback, pattern="^yeni_post$"))
    app.add_handler(CallbackQueryHandler(aktif_postlar_callback, pattern="^aktif_postlar$"))
    app.add_handler(CallbackQueryHandler(kanal_sec_callback, pattern="^kanal_sec:"))
    app.add_handler(CallbackQueryHandler(durdur_callback, pattern="^durdur:"))
    app.add_handler(CallbackQueryHandler(ana_menu_callback, pattern="^ana_menu$"))
    app.add_handler(CallbackQueryHandler(iptal_callback, pattern="^iptal$"))

    # Mesaj handler (komut olmayan her şey)
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, mesaj_al))

    print("✅ Bot başlatıldı!")
    app.run_polling()

if __name__ == "__main__":
    main()
