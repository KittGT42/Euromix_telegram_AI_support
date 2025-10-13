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
    get_issue_status_by_issue_key,
    get_active_issue_for_user,
    update_user_department,
    update_user_balance_unit
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

START_CHAT, TAKE_SUMMARY, END_CHAT, PHONE, DEPARTAMENT_CHOOSE, BALANCE_UNIT, SERVICE, GROUP  = range(8)


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
                ],
                DEPARTAMENT_CHOOSE: [
                    MessageHandler(filters.TEXT, self.departament_choose)
                ],
                BALANCE_UNIT: [
                    MessageHandler(filters.TEXT, self.balance_unit_choose)
                ],
            },
            fallbacks=[CommandHandler('cancel', self.cancel)]
        )

        # Початок спілкування
        start_chat = ConversationHandler(
            entry_points=[
                CommandHandler('start_chat', self.service_app_name),
                MessageHandler(filters.Regex("^Почати діалог$"), self.service_app_name)
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
            create_user(telegram_id=user_id, telegram_name=full_name_user, phone=phone_user)
        else:
            await update.message.reply_text('Натисніть кнопку нижче Поділитися контактом')
            return PHONE

        # Список департаментів
        DEPARTAMENTS = [
            "Комерційний департамент",
            "Операційний департамент",
            "Бухгалтерія",
            "Відділ кадрів",
            "Департамент маркетинга",
            "ІТ департамент",
            "Департамент безпеки",
            "Фінансовий департамент",
            "Департамент персоналу",
            "Контрольно ревізійний відділ",
            "Юр. департамент"
        ]

        # Створюємо клавіатуру з департаментами (по 2 кнопки в ряд)
        keyboard = []
        for i in range(0, len(DEPARTAMENTS), 2):
            row = DEPARTAMENTS[i:i+2]
            keyboard.append(row)

        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

        await update.message.reply_text(
            f"✅ Авторизація успішна!\nВаш номер: {phone_user}\n\n"
            f"Оберіть ваш департамент:",
            reply_markup=reply_markup
        )

        return DEPARTAMENT_CHOOSE

    async def departament_choose(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обробка вибору департаменту"""
        user_id = update.effective_user.id
        selected_department = update.message.text

        DEPARTAMENTS = [
            "Комерційний департамент",
            "Операційний департамент",
            "Бухгалтерія",
            "Відділ кадрів",
            "Департамент маркетинга",
            "ІТ департамент",
            "Департамент безпеки",
            "Фінансовий департамент",
            "Департамент персоналу",
            "Контрольно ревізійний відділ",
            "Юр. департамент"
        ]

        # Перевіряємо чи вибраний департамент валідний
        if selected_department not in DEPARTAMENTS:
            # Якщо невалідний вибір, показуємо клавіатуру знову
            keyboard = []
            for i in range(0, len(DEPARTAMENTS), 2):
                row = DEPARTAMENTS[i:i+2]
                keyboard.append(row)

            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

            await update.message.reply_text(
                "❌ Будь ласка, оберіть департамент зі списку:",
                reply_markup=reply_markup
            )
            return DEPARTAMENT_CHOOSE

        # Зберігаємо обраний департамент
        update_user_department(user_id, selected_department)

        # Список баланс-юнітів
        BALANCE_UNITS = [
            "Вінниця",
            "PSC",
            "Полтава",
            "Київ",
            "Суми",
            "Харків",
            "Запоріжжя",
            "Кривий Ріг",
            "Офіс",
            "Одеса",
            "Біла Церква",
            "Львів",
            "Дніпро",
            "Черкаси",
            "Краматорськ",
            "Кропивницький",
            "Чернігів"
        ]

        # Створюємо клавіатуру з баланс-юнітами (по 2 кнопки в ряд)
        keyboard = []
        for i in range(0, len(BALANCE_UNITS), 2):
            row = BALANCE_UNITS[i:i+2]
            keyboard.append(row)

        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

        # Переходимо до вибору баланс-юніту
        await update.message.reply_text(
            f"✅ Департамент обрано: {selected_department}\n\n"
            "Тепер оберіть ваш підрозділ",
            reply_markup=reply_markup
        )

        return BALANCE_UNIT

    async def balance_unit_choose(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обробка вибору баланс-юніту"""
        user_id = update.effective_user.id
        selected_balance_unit = update.message.text

        BALANCE_UNITS = [
            "Вінниця",
            "PSC",
            "Полтава",
            "Київ",
            "Суми",
            "Харків",
            "Запоріжжя",
            "Кривий Ріг",
            "Офіс",
            "Одеса",
            "Біла Церква",
            "Львів",
            "Дніпро",
            "Черкаси",
            "Краматорськ",
            "Кропивницький",
            "Чернігів"
        ]

        # Перевіряємо чи вибраний баланс-юніт валідний
        if selected_balance_unit not in BALANCE_UNITS:
            # Якщо невалідний вибір, показуємо клавіатуру знову
            keyboard = []
            for i in range(0, len(BALANCE_UNITS), 2):
                row = BALANCE_UNITS[i:i+2]
                keyboard.append(row)

            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

            await update.message.reply_text(
                "❌ Будь ласка, оберіть баланс-юніт зі списку:",
                reply_markup=reply_markup
            )
            return BALANCE_UNIT

        # Зберігаємо обраний баланс-юніт
        update_user_balance_unit(user_id, selected_balance_unit)

        # Завершуємо реєстрацію
        keyboard = ReplyKeyboardMarkup([
            ["Почати діалог"],
        ], resize_keyboard=True, one_time_keyboard=True)

        await update.message.reply_text(
            f"✅ Реєстрація завершена!\n"
            f"Баланс-юніт: {selected_balance_unit}\n\n"
            "Тепер ви можете почати діалог з підтримкою.",
            reply_markup=keyboard
        )

        return ConversationHandler.END

    async def service_app_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Список баланс-юнітів
        app_names = [
            "E-mix 3.x"
        ]

        # Створюємо клавіатуру з баланс-юнітами (по 2 кнопки в ряд)
        keyboard = []
        for i in range(0, len(app_names), 2):
            row = app_names[i:i + 2]
            keyboard.append(row)

        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

        await update.message.reply_text(
            "Виберіть додаток з яким зявилось запитання",
            reply_markup=reply_markup
        )

        return TAKE_SUMMARY

    async def create_summary_jira_issue(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        app_names = [
            "E-mix 3.x"
        ]

        user_message = update.message.text

        if user_message in app_names:

            telegram_user_id_from_chat = update.effective_user.id
            user = get_user_by_telegram_id(telegram_user_id_from_chat)
            telegram_user_name_from_chat = update.effective_user.full_name
            telegram_user_phone_from_chat = user[3]
            telegram_user_link_from_chat = update.effective_user.link

            returned_issue_key =  create_issue(summary_from_user=user_message, description='', telegram_user_id=telegram_user_id_from_chat,
                         telegram_user_number=telegram_user_phone_from_chat, telegram_user_full_name=telegram_user_name_from_chat,
                         telegram_user_link=telegram_user_link_from_chat, service_app_name=user_message)

            # 5️⃣ Відправляємо відповідь користувачу
            await update.message.reply_text(text='Напишіть ваше запитання з яким вам допомогти у вирішенні')
            return START_CHAT

        else:
            # Створюємо клавіатуру (по 2 кнопки в ряд)
            keyboard = []
            for i in range(0, len(app_names), 2):
                row = app_names[i:i + 2]
                keyboard.append(row)

            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

            await update.message.reply_text(
                "Виберіть додаток з яким зявилось запитання",
                reply_markup=reply_markup
            )
            return TAKE_SUMMARY

    async def send_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):

        """Обробка повідомлень від користувача"""
        message_from_user = update.message.text
        user_id = update.effective_user.id
        user_data = get_user_by_telegram_id(user_id)

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

        # Перевіряємо чи не закритий тікет
        status_issue = get_issue_status_by_issue_key(active_issue_key)
        if status_issue == 'Done':
            keyboard = ReplyKeyboardMarkup([
                ["Почати діалог"],
            ], resize_keyboard=True, one_time_keyboard=True)

            await update.message.reply_text(
                f"✅ Ваш тікет {user_data[4]} вже оброблений\n"
                f"Що б створити новий натисніть кнопку Почати діалог",
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
        add_comment_to_issue(message=message_from_user, issue_key=active_issue_key)  # ✅

        history = get_chat_history(user_id, limit=10)

        ai_answer = ask_to_open_web_ui_agent(history)

        save_message(user_id, "assistant", ai_answer)
        add_comment_to_issue(message=ai_answer, issue_key=active_issue_key)  # ✅

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