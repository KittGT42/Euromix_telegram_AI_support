from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

from main_db import create_user, get_user_by_telegram_id

from configs.base_config import settings

from dotenv import load_dotenv
import os

import requests

load_dotenv()

SERVER_URL_WEBCAMERA: str = os.getenv("SERVER_URL_WEBCAMERA")


START_CHAT, END_CHAT, PHONE = range(3)


def ask_to_open_web_ui_agent(user_text):
    response = requests.post(
        "https://ai.euromix.in.ua/api/chat/completions",
        headers={
            "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjhjOWQ2ZTBkLWRmYzMtNDNmNy1hZjcxLWFjMjJlNWI1NWNkOSJ9.H3aCuXDzE7iYr1INXbbkFzMZbCux2BFc7wwPSiAxzUI",
            "Content-Type": "application/json"
        },
        json={
            "model": "euromixsupportagent",
            "messages": [{"role": "user", "content": f"{user_text}"}],
            "stream": False,
            "files": [
                {"type": "collection", "id": "ffc3373a-148f-49dc-947f-fd8db6e6d9cc"}
            ]
        }
    )

    ai_response = ""

    if response.status_code == 200:
        result = response.json()
        ai_response = result['choices'][0]['message']['content']

    return ai_response

class SupportAiAgent:
    def __init__(self, token):
        self.application = Application.builder().token(token).build()
        self.setup_handlers()

    def setup_handlers(self):
        """Налаштування обробників команд"""

        # Обробник авторизації
        auth_handler = ConversationHandler(
            entry_points=[CommandHandler('start', self.start)],
            states={
                PHONE: [MessageHandler(filters.CONTACT, self.phone_received),
                MessageHandler(filters.TEXT, self.confirm_phone)],
            },
            fallbacks=[CommandHandler('cancel', self.cancel)]
        )

        # Початок спілкування
        start_chat = ConversationHandler(
            entry_points=[CommandHandler('start_chat', self.start),
                          MessageHandler(filters.Regex("^Почати діалог$"), self.send_message)],
            states={
                START_CHAT: [MessageHandler(filters.TEXT, self.send_message),
                MessageHandler(filters.TEXT, self.confirm_phone),
            ]},
            fallbacks=[CommandHandler('cancel', self.cancel)]
        )

        # end_chat = ConversationHandler(
        #     entry_points=[CommandHandler('stop_chat', self.start_report),
        #                   MessageHandler(filters.Regex("^Закінчити діалог$"), self.start_report)],
        #     states={
        #         START_CHAT: [MessageHandler(filters.TEXT, self.car_type_received)],
        #     },
        #     fallbacks=[CommandHandler('cancel', self.cancel)]
        # )

        self.application.add_handler(auth_handler)
        self.application.add_handler(start_chat)
        # self.application.add_handler(end_chat)


    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Початок авторизації"""
        user_id = update.effective_user.id
        user_db = get_user_by_telegram_id(user_id)

        if user_db:
            await update.message.reply_text(
                f"Ви вже авторизовані! 📱\nВаш номер: {user_db[3]}\n\n"
                "Доступні команди:\n"
            )

            return ConversationHandler.END

        # Кнопка для відправки контакту
        button = KeyboardButton("📱 Поділитися номером", request_contact=True)
        keyboard = ReplyKeyboardMarkup([[button]], resize_keyboard=True, one_time_keyboard=True)

        await update.message.reply_text(
            "Вітаю! 👋\nДля авторизації поділіться своїм номером телефону:",
            reply_markup=keyboard
        )
        return PHONE


    async def confirm_phone(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        button = KeyboardButton("📱 Поділитися номером", request_contact=True)
        keyboard = ReplyKeyboardMarkup([[button]], resize_keyboard=True, one_time_keyboard=True)

        await update.message.reply_text(
            "Нажміть кнопку нижче 'Поділитися телефоном'",
            reply_markup=keyboard
        )
        return PHONE

    async def phone_received(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обробка отриманого номера телефону"""
        user_id = update.effective_user.id
        full_name_user = update.effective_user.full_name

        if update.message.contact:
            phone_user = update.message.contact.phone_number
            result_save_user = create_user(telegram_id=user_id, telegram_name=full_name_user, phone=phone_user)

        else:
            await update.message.reply_text('Нажміть кнопку нижче Поділитися контактом')
            return PHONE


        keyboard = ReplyKeyboardMarkup([
            ["Почати діалог"],
        ], resize_keyboard=True, one_time_keyboard=True)

        await update.message.reply_text(
            f"✅ Авторизація успішна!\nВаш номер: {phone_user}\n\n",
            reply_markup=keyboard
        )

        return ConversationHandler.END

    async def send_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        message_from_user = update.message.text
        if message_from_user == 'Почати діалог':
            await update.message.reply_text(
                "Напишіть ваше запитання і ми вам надамо відповідь"
            )
            return START_CHAT

        user_id = update.effective_user.id
        user_db = get_user_by_telegram_id(user_id)
        ai_answer = ask_to_open_web_ui_agent(message_from_user)

        await update.message.reply_text(ai_answer)
        return START_CHAT

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Скасування операції"""
        await update.message.reply_text(
            "❌ Операцію скасовано.\n"
            "Використайте /help для списку команд"
        )
        return ConversationHandler.END

    def run(self):
        """Запуск бота"""
        print("🤖 Бот запущено...")
        self.application.run_polling()



# Запуск бота
if __name__ == '__main__':

    BOT_TOKEN = settings.TELEGRAM_BOT_TOKEN
    bot = SupportAiAgent(BOT_TOKEN)
    bot.run()