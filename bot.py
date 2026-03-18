import os
import logging
import requests
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from groq import Groq

# ========== НАСТРОЙКИ ==========
TELEGRAM_TOKEN = "8400598291:AAEVNpAlCr2Egwxv0QZWbUf6fBu-DHbSIlE"  # Вставь свой токен
GROQ_API_KEY = "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"          # Вставь свой Groq ключ
# ================================

logging.basicConfig(level=logging.INFO)
client = Groq(api_key=GROQ_API_KEY)

def parse_page(url: str) -> str:
    """Парсит текст со страницы по ссылке"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # Убираем скрипты и стили
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        text = soup.get_text(separator="\n", strip=True)

        # Ограничиваем размер текста
        if len(text) > 8000:
            text = text[:8000] + "\n...(текст обрезан)"

        return text
    except Exception as e:
        return f"Ошибка при загрузке страницы: {e}"


def solve_with_groq(task_text: str) -> str:
    """Отправляет задание в Groq и получает решение"""
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Ты помощник по выполнению домашних заданий. "
                        "Тебе дают текст страницы с заданием (ЦДЗ/ДЗ). "
                        "Твоя задача — найти задания и дать чёткие, правильные ответы. "
                        "Отвечай по-русски. Структурируй ответы: Задание 1 — ответ, Задание 2 — ответ и т.д."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Вот содержимое страницы с домашним заданием:\n\n{task_text}\n\nПожалуйста, реши все задания и дай ответы.",
                },
            ],
            model="llama-3.3-70b-versatile",
            max_tokens=2048,
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        return f"Ошибка при обращении к AI: {e}"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Я бот для решения ЦДЗ.\n\n"
        "📎 Просто отправь мне ссылку на задание — и я пришлю ответы!\n\n"
        "Пример: https://uchebnik.mos.ru/..."
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if not text.startswith("http"):
        await update.message.reply_text("🔗 Пожалуйста, отправь ссылку на задание (начинается с http)")
        return

    await update.message.reply_text("⏳ Загружаю задание, подожди немного...")

    page_text = parse_page(text)

    if "Ошибка" in page_text:
        await update.message.reply_text(f"❌ {page_text}\n\nВозможно, сайт требует авторизацию.")
        return

    await update.message.reply_text("🤖 Решаю задание...")

    answer = solve_with_groq(page_text)

    # Telegram ограничивает сообщения до 4096 символов
    if len(answer) > 4000:
        parts = [answer[i:i+4000] for i in range(0, len(answer), 4000)]
        for part in parts:
            await update.message.reply_text(part)
    else:
        await update.message.reply_text(f"✅ Ответы:\n\n{answer}")


def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Бот запущен!")
    app.run_polling()


if __name__ == "__main__":
    main()
