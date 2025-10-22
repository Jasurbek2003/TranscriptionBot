from bot.config import settings


def get_welcome_message(user_name: str, balance: float, language: str = "en") -> str:
    """
    Get welcome message in user's language
    """
    messages = {
        "en": (
            f"👋 <b>Welcome, {user_name}!</b>\n\n"
            f"I'm your transcription assistant. Send me audio or video files, "
            f"and I'll convert them to text for you.\n\n"
            f"💰 Your balance: {balance:.2f} UZS\n\n"
            f"To get started:\n"
            f"1. Send me an audio or video file\n"
            f"2. Wait for transcription\n"
            f"3. Download your text file\n\n"
            f"Use /help for more information."
        ),
        "ru": (
            f"👋 <b>Добро пожаловать, {user_name}!</b>\n\n"
            f"Я ваш помощник по транскрипции. Отправьте мне аудио или видео файлы, "
            f"и я преобразую их в текст.\n\n"
            f"💰 Ваш баланс: {balance:.2f} UZS\n\n"
            f"Для начала:\n"
            f"1. Отправьте аудио или видео файл\n"
            f"2. Дождитесь транскрипции\n"
            f"3. Скачайте текстовый файл\n\n"
            f"Используйте /help для дополнительной информации."
        ),
        "uz": (
            f"👋 <b>Xush kelibsiz, {user_name}!</b>\n\n"
            f"Men sizning transkripsiya yordamchingizman. Menga audio yoki video fayllarni yuboring, "
            f"men ularni matn ko'rinishiga o'tkazaman.\n\n"
            f"💰 Sizning balansingiz: {balance:.2f} UZS\n\n"
            f"Boshlash uchun:\n"
            f"1. Audio yoki video fayl yuboring\n"
            f"2. Transkripsiyani kuting\n"
            f"3. Matn faylini yuklab oling\n\n"
            f"Qo'shimcha ma'lumot uchun /help buyrug'idan foydalaning."
        ),
    }

    return messages.get(language, messages["en"])


def get_help_message(language: str = "en") -> str:
    """
    Get help message in user's language
    """
    messages = {
        "en": (
            "ℹ️ <b>Help & Information</b>\n\n"
            "<b>How to use:</b>\n"
            "1. Send any audio or video file\n"
            "2. The bot will transcribe it to text\n"
            "3. Download the transcription as a .txt file\n\n"
            "<b>Pricing:</b>\n"
            f"• Audio: {settings.pricing.audio_price_per_min} UZS per minute\n"
            f"• Video: {settings.pricing.video_price_per_min} UZS per minute\n\n"
            "<b>Limits:</b>\n"
            f"• Max audio duration: {settings.ai.max_audio_duration_seconds // 60} minutes\n"
            f"• Max video duration: {settings.ai.max_video_duration_seconds // 60} minutes\n"
            f"• Max file size: {settings.ai.max_file_size_mb} MB\n\n"
            "<b>Commands:</b>\n"
            "/start - Start the bot\n"
            "/help - Show this message\n"
            "/balance - Check your balance\n"
            "/topup - Add funds to your account\n"
            "/history - View transaction history\n"
            "/settings - Bot settings\n\n"
            "<b>Support:</b>\n"
            "If you have any questions, contact @support"
        ),
        "ru": (
            "ℹ️ <b>Помощь и информация</b>\n\n"
            "<b>Как использовать:</b>\n"
            "1. Отправьте аудио или видео файл\n"
            "2. Бот преобразует его в текст\n"
            "3. Скачайте транскрипцию как .txt файл\n\n"
            "<b>Цены:</b>\n"
            f"• Аудио: {settings.pricing.audio_price_per_min} UZS за минуту\n"
            f"• Видео: {settings.pricing.video_price_per_min} UZS за минуту\n\n"
            "<b>Ограничения:</b>\n"
            f"• Макс. длительность аудио: {settings.ai.max_audio_duration_seconds // 60} минут\n"
            f"• Макс. длительность видео: {settings.ai.max_video_duration_seconds // 60} минут\n"
            f"• Макс. размер файла: {settings.ai.max_file_size_mb} МБ\n\n"
            "<b>Команды:</b>\n"
            "/start - Запустить бота\n"
            "/help - Показать это сообщение\n"
            "/balance - Проверить баланс\n"
            "/topup - Пополнить счет\n"
            "/history - История транзакций\n"
            "/settings - Настройки бота\n\n"
            "<b>Поддержка:</b>\n"
            "По всем вопросам обращайтесь @support"
        ),
        "uz": (
            "ℹ️ <b>Yordam va ma'lumot</b>\n\n"
            "<b>Qanday foydalanish:</b>\n"
            "1. Audio yoki video fayl yuboring\n"
            "2. Bot uni matnga aylantiradi\n"
            "3. Transkripsiyani .txt fayl sifatida yuklab oling\n\n"
            "<b>Narxlar:</b>\n"
            f"• Audio: {settings.pricing.audio_price_per_min} UZS daqiqasiga\n"
            f"• Video: {settings.pricing.video_price_per_min} UZS daqiqasiga\n\n"
            "<b>Cheklovlar:</b>\n"
            f"• Audio maksimal davomiyligi: {settings.ai.max_audio_duration_seconds // 60} daqiqa\n"
            f"• Video maksimal davomiyligi: {settings.ai.max_video_duration_seconds // 60} daqiqa\n"
            f"• Fayl maksimal hajmi: {settings.ai.max_file_size_mb} MB\n\n"
            "<b>Buyruqlar:</b>\n"
            "/start - Botni ishga tushirish\n"
            "/help - Ushbu xabarni ko'rsatish\n"
            "/balance - Balansni tekshirish\n"
            "/topup - Hisobni to'ldirish\n"
            "/history - Tranzaksiyalar tarixi\n"
            "/settings - Bot sozlamalari\n\n"
            "<b>Qo'llab-quvvatlash:</b>\n"
            "Savollar bo'lsa @support ga murojaat qiling"
        ),
    }

    return messages.get(language, messages["en"])
