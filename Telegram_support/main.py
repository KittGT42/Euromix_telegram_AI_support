from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler
)

from Telegram_support.database.crud import (
    create_user,
    get_user_by_telegram_id,
    save_message,
    get_chat_history,
    clear_chat_history,
    get_chat_history_count,
    get_active_issue_for_user,
    update_erp_user_token

)

from Telegram_support.utils.jira import create_issue, add_comment_to_issue

from database.engine import create_all_tables

from configs.base_config import settings
from dotenv import load_dotenv
import requests
import logging

load_dotenv()

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

START_CHAT, TAKE_SUMMARY, END_CHAT, PHONE  = range(4)
part_of_url_data_base = settings.PART_OF_URL_DATABASE



def ask_to_open_web_ui_agent(messages_array):
    """
    Відправляє масив повідомлень в OpenWebUI API.

    Args:
        messages_array: List[dict] у форматі [{"role": "user", "content": "..."}]
    """
    response = requests.post(
        "https://ai.euromix.in.ua/api/chat/completions",
        headers={
            "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjhjOWQ2ZTBkLWRmYzMtNDNmNy1hZjcxLWFjMjJlNWI1NWNkOSJ9.H3aCuXDzE7iYr1INXbbkFzMZbCux2BFc7wwPSiAxzUI",
            "Content-Type": "application/json"
        },
        json={
            "model": "euromixsupportagent",
            "messages": messages_array,
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

def get_user_token(phone_number):
    data_response = requests.post(f"https://mobile.euromix.in.ua/{part_of_url_data_base}/hs/ex3/sign_in",
                                  json={"identity": {"phone": phone_number}})
    data_response_json = data_response.json()
    if data_response.status_code == 401:
        return False
    user_token = data_response_json['data']['access_token']
    return user_token

def get_user_data(user_token):
    url = f'https://mobile.euromix.in.ua/{part_of_url_data_base}/hs/ex3/profile'
    headers = {
        'Accept': '*/*',
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {user_token}',
    }

    response = requests.get(url, headers=headers)
    status_response = response.status_code

    return response, status_response

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
                PHONE: [
                    MessageHandler(filters.CONTACT, self.phone_received),
                    MessageHandler(filters.TEXT, self.confirm_phone)
                ]
            },
            fallbacks=[CommandHandler('cancel', self.cancel)]
        )

        # Початок спілкування
        start_chat = ConversationHandler(
            entry_points=[
                CommandHandler('start_chat', self.send_message),
                MessageHandler(filters.Regex("^Почати діалог$"), self.send_message)
            ],
            states={
                TAKE_SUMMARY: [
                    MessageHandler(filters.TEXT, self.create_summary_jira_issue)
                ],
                START_CHAT: [
                    MessageHandler(filters.TEXT, self.send_message),
                    MessageHandler(filters.TEXT, self.confirm_phone),
                ]
            },
            fallbacks=[CommandHandler('cancel', self.cancel)]
        )

        self.application.add_handler(auth_handler)
        self.application.add_handler(start_chat)
        self.application.add_handler(CommandHandler('clear_history', self.clear_history))
        self.application.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND & ~filters.Regex("^Почати діалог$"),
                self.send_message
            )
        )

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Початок авторизації"""
        user_id = update.effective_user.id
        user_db = get_user_by_telegram_id(user_id)

        if user_db:
            await update.message.reply_text(
                f"Ви вже авторизовані! 📱\nВаш номер: {user_db[3]}\n\n"
                "Доступні команди:\n"
                "/start_chat - Почати діалог\n"
                "/clear_history - Очистити історію"
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
            "Натисніть кнопку нижче 'Поділитися телефоном'",
            reply_markup=keyboard
        )
        return PHONE

    async def phone_received(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обробка отриманого номера телефону"""
        user_id = update.effective_user.id
        full_name_user = update.effective_user.full_name

        if update.message.contact:
            phone_user = update.message.contact.phone_number
            erp_user_token = get_user_token(phone_user)

            if erp_user_token:
                # Збереження користувача
                create_user(telegram_id=user_id, telegram_name=full_name_user, phone=phone_user, erp_user_token=erp_user_token)
            else:
                button = KeyboardButton("📱 Поділитися номером", request_contact=True)
                keyboard = ReplyKeyboardMarkup([[button]], resize_keyboard=True, one_time_keyboard=True)

                await update.message.reply_text(
                    """
                    ❗☎️ Номери відрізняються!\n\n🔎 Перевірте номер телефону, який ви надсилаєте — він повинен повністю збігатися з номером телефона вашого аккаунта в Euromix.\n\n🆘 Зверніться до підтримки що б вирішити питання з номером телефона
                    """,
                    reply_markup=keyboard
                )
                return PHONE


        else:
            button = KeyboardButton("📱 Поділитися номером", request_contact=True)
            keyboard = ReplyKeyboardMarkup([[button]], resize_keyboard=True, one_time_keyboard=True)

            await update.message.reply_text('Натисніть кнопку нижче Поділитися контактом',
                                            reply_markup=keyboard)
            return PHONE

        button = KeyboardButton("Почати діалог")
        keyboard = ReplyKeyboardMarkup([[button]], resize_keyboard=True, one_time_keyboard=True)
        await update.message.reply_text(
            f"✅ Авторизація успішна!\nВаш номер: {phone_user}\n\n"
            f"Що б почати звернення, натисніть кнопку Почати діалог",
            reply_markup=keyboard
        )
        return START_CHAT

    async def create_summary_jira_issue(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        telegram_user_id_from_chat = update.effective_user.id
        user_data = get_user_by_telegram_id(telegram_user_id_from_chat)

        response, status_response = get_user_data(user_data[4])
        if status_response != 200:
            user_token = get_user_token(user_data[3])
            update_token = update_erp_user_token(user_data[1], user_token)
            response, status_response = get_user_data(user_data[4])
        else:
            pass

        user_full_name = response.json()['fullName']
        departament = response.json()['departmentJiraId']
        balance_unit = response.json()['balanceUnitJiraId']
        user_login = response.json()['login']


        user_message = update.message.text
        telegram_user_name = update.effective_user.username

        returned_issue_key = create_issue(summary_from_user=user_message, description='',
                                          telegram_user_id=telegram_user_id_from_chat,
                                          departament_id=departament, balance_unit_id=balance_unit,
                                          telegram_user_name=telegram_user_name,
                                          user_fio=user_full_name,
                                          user_login=user_login,
                                          )

        save_message(telegram_user_id_from_chat, "user", user_message)
        add_comment_to_issue(sender='telegram_user' ,message=user_message, issue_key=returned_issue_key)

        # 3️⃣ Відправляємо всю історію в OpenWebUI API
        ai_answer = ask_to_open_web_ui_agent([{"role": "user", "content": user_message}])

        # 4️⃣ Зберігаємо відповідь асистента
        save_message(telegram_user_id_from_chat, "assistant", ai_answer)
        add_comment_to_issue(sender='ai_response' ,message=ai_answer, issue_key=returned_issue_key)

        # 5️⃣ Відправляємо відповідь користувачу
        await update.message.reply_text(ai_answer)
        return START_CHAT

    async def send_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обробка повідомлень від користувача"""
        message_from_user = update.message.text
        user_id = update.effective_user.id
        user_data = get_user_by_telegram_id(user_id)

        if message_from_user == 'Почати діалог' or message_from_user == '/start_chat':
            await update.message.reply_text(
                "Напишіть ваше запитання і ми вам надамо відповідь"
            )
            return TAKE_SUMMARY

        # Отримуємо активний issue користувача
        active_issue_key = get_active_issue_for_user(user_id)

        # Якщо немає активного issue - пропонуємо створити новий
        if not active_issue_key:
            keyboard = ReplyKeyboardMarkup([
                ["Почати діалог"],
            ], resize_keyboard=True, one_time_keyboard=True)

            await update.message.reply_text(
                f"✅ У вас немає активних тікетів\n"
                f"Щоб створити новий, натисніть кнопку 'Почати діалог'",
                reply_markup=keyboard
            )
            return ConversationHandler.END

        # Перевіряємо чи користувач існує
        user_db = get_user_by_telegram_id(user_id)
        if not user_db:
            await update.message.reply_text(
                "❌ Спочатку авторизуйтесь через /start"
            )
            return ConversationHandler.END

        save_message(user_id, "user", message_from_user)
        add_comment_to_issue(sender='telegram_user', message=message_from_user, issue_key=active_issue_key)  # ✅

        history = get_chat_history(user_id, limit=10)

        ai_answer = ask_to_open_web_ui_agent(history)

        save_message(user_id, "assistant", ai_answer)
        add_comment_to_issue(sender='ai_response', message=ai_answer, issue_key=active_issue_key)  # ✅

        # 5️⃣ Відправляємо відповідь користувачу
        await update.message.reply_text(ai_answer)

        return START_CHAT

    async def clear_history(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Очищення історії діалогу"""
        user_id = update.effective_user.id

        # Дізнаємось скільки повідомлень було
        count = get_chat_history_count(user_id)

        if clear_chat_history(user_id):
            await update.message.reply_text(
                f"✅ Історію діалогу очищено!\n"
                f"Видалено повідомлень: {count}"
            )
        else:
            await update.message.reply_text("❌ Помилка при очищенні історії")

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
    # 1️⃣ Створюємо таблиці в БД (якщо їх ще немає)
    print("🔄 Створення таблиць у базі даних...")
    create_all_tables()
    print("✅ Таблиці готові!")

    # 2️⃣ Запускаємо бота
    BOT_TOKEN = settings.TELEGRAM_BOT_TOKEN
    bot = SupportAiAgent(BOT_TOKEN)
    bot.run()