import logging
import random
from telegram import Update, InputMediaPhoto
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, ConversationHandler

# Görselleri, ayarları ve diğer bilgileri saklamak için global değişkenler
user_data = {}

# Yetkili kullanıcı ID'leri
AUTHORIZED_USER_IDS = [5532860568, 1234567890]  # İstediğiniz kadar ekleyebilirsiniz

# Konuşma durumları
GET_IMAGES, GET_INTERVAL, GET_GROUP, GET_RANGE, GET_DESCRIPTION = range(5)

# Yetkili kullanıcı kontrolü
def is_authorized_user(user_id: int) -> bool:
    return user_id in AUTHORIZED_USER_IDS

# /start komutu
def start(update: Update, context: CallbackContext) -> int:
    user_id = update.message.from_user.id
    if not is_authorized_user(user_id):
        update.message.reply_text("⛔ Bu botu kullanma yetkiniz yok!")
        return ConversationHandler.END

    update.message.reply_text("Merhaba! Lütfen toplu görsellerinizi gönderin. (Herhangi bir sayıda)")
    return GET_IMAGES

# Görselleri alma
def get_images(update: Update, context: CallbackContext) -> int:
    user_id = update.message.from_user.id
    if not is_authorized_user(user_id):
        update.message.reply_text("⛔ Bu botu kullanma yetkiniz yok!")
        return ConversationHandler.END

    if user_id not in user_data:
        user_data[user_id] = {"images": []}

    # Görselleri kaydet
    if update.message.photo:
        user_data[user_id]["images"].append(update.message.photo[-1].file_id)
        update.message.reply_text(f"{len(user_data[user_id]['images'])} görsel alındı. Devam edin veya /done yazarak bitirin.")
    else:
        update.message.reply_text("Lütfen geçerli bir görsel gönderin.")

    return GET_IMAGES

# /done komutu ile görsel göndermeyi bitirme
def done(update: Update, context: CallbackContext) -> int:
    user_id = update.message.from_user.id
    if not is_authorized_user(user_id):
        update.message.reply_text("⛔ Bu botu kullanma yetkiniz yok!")
        return ConversationHandler.END

    if user_id not in user_data or not user_data[user_id]["images"]:
        update.message.reply_text("Henüz hiç görsel göndermediniz.")
        return ConversationHandler.END

    update.message.reply_text("Görseller başarıyla alındı. Kaç saatte bir paylaşım yapılacak?")
    return GET_INTERVAL

# Paylaşım sıklığını alma
def get_interval(update: Update, context: CallbackContext) -> int:
    user_id = update.message.from_user.id
    if not is_authorized_user(user_id):
        update.message.reply_text("⛔ Bu botu kullanma yetkiniz yok!")
        return ConversationHandler.END

    try:
        interval = int(update.message.text)
        if interval <= 0:
            update.message.reply_text("Lütfen pozitif bir sayı girin.")
            return GET_INTERVAL
        user_data[user_id]["interval"] = interval
        update.message.reply_text("Paylaşım yapılacak grup bilgisini girin.")
        return GET_GROUP
    except ValueError:
        update.message.reply_text("Lütfen geçerli bir sayı girin.")
        return GET_INTERVAL

# Grup bilgisini alma
def get_group(update: Update, context: CallbackContext) -> int:
    user_id = update.message.from_user.id
    if not is_authorized_user(user_id):
        update.message.reply_text("⛔ Bu botu kullanma yetkiniz yok!")
        return ConversationHandler.END

    user_data[user_id]["group"] = update.message.text
    update.message.reply_text("Paylaşım için rastgele sayı aralığını girin (örn: 3-50).")
    return GET_RANGE

# Sayı aralığını alma
def get_range(update: Update, context: CallbackContext) -> int:
    user_id = update.message.from_user.id
    if not is_authorized_user(user_id):
        update.message.reply_text("⛔ Bu botu kullanma yetkiniz yok!")
        return ConversationHandler.END

    try:
        min_val, max_val = map(int, update.message.text.split("-"))
        if min_val >= max_val or min_val < 0 or max_val < 0:
            update.message.reply_text("Lütfen geçerli bir aralık girin (örn: 3-50).")
            return GET_RANGE
        user_data[user_id]["range"] = (min_val, max_val)
        update.message.reply_text("Paylaşım için bir açıklama girin.")
        return GET_DESCRIPTION
    except (ValueError, IndexError):
        update.message.reply_text("Lütfen geçerli bir aralık girin (örn: 3-50).")
        return GET_RANGE

# Açıklamayı alma ve paylaşımı başlatma
def get_description(update: Update, context: CallbackContext) -> int:
    user_id = update.message.from_user.id
    if not is_authorized_user(user_id):
        update.message.reply_text("⛔ Bu botu kullanma yetkiniz yok!")
        return ConversationHandler.END

    user_data[user_id]["description"] = update.message.text

    # Paylaşımı başlat
    context.job_queue.run_repeating(
        share_images,
        interval=user_data[user_id]["interval"] * 3600,
        first=0,
        context=user_id,
    )

    update.message.reply_text("Paylaşım başlatıldı!")
    return ConversationHandler.END

# Görselleri paylaşma
def share_images(context: CallbackContext):
    user_id = context.job.context
    images = user_data[user_id]["images"]
    min_val, max_val = user_data[user_id]["range"]
    description = user_data[user_id]["description"]

    # Rastgele sayı ekle
    random_number = random.randint(min_val, max_val)
    final_description = f"{description}\nRastgele Sayı: {random_number}"

    # Görselleri gruplayarak paylaş (her seferinde 10 görsel)
    for i in range(0, len(images), 10):
        media_group = [InputMediaPhoto(media=image, caption=final_description if j == 0 else "") for j, image in enumerate(images[i:i + 10])]
        context.bot.send_media_group(chat_id=user_data[user_id]["group"], media=media_group)

    # Tüm görseller paylaşıldı, işlemi durdur
    context.job_queue.stop()

# Hata durumunda
def cancel(update: Update, context: CallbackContext) -> int:
    user_id = update.message.from_user.id
    if not is_authorized_user(user_id):
        update.message.reply_text("⛔ Bu botu kullanma yetkiniz yok!")
        return ConversationHandler.END

    update.message.reply_text("İşlem iptal edildi.")
    return ConversationHandler.END

def main():
    # Botun API Token'ını buraya ekleyin
    token = "7095271918:AAFDLxzi1VFR9nk7b61oW5i_PKnDnM7afB4"
    updater = Updater(token, use_context=True)

    # Konuşma işleyicisi
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            GET_IMAGES: [MessageHandler(Filters.photo, get_images), CommandHandler("done", done)],
            GET_INTERVAL: [MessageHandler(Filters.text & ~Filters.command, get_interval)],
            GET_GROUP: [MessageHandler(Filters.text & ~Filters.command, get_group)],
            GET_RANGE: [MessageHandler(Filters.text & ~Filters.command, get_range)],
            GET_DESCRIPTION: [MessageHandler(Filters.text & ~Filters.command, get_description)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    updater.dispatcher.add_handler(conv_handler)

    # Botu başlat
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()