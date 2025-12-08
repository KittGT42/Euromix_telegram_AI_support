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
    get_chat_history_by_issue,
    clear_chat_history,
    get_chat_history_count,
    get_active_issue_for_user,
    update_erp_user_token,
    get_jira_issue_status,
    get_jira_issue_ai_work_status
)

from Telegram_support.utils.jira import create_issue, add_comment_to_issue, add_attachment_to_issue
from Telegram_support.utils.open_web_ui_agents_requests import ask_to_open_web_ui_agent, chat_with_image
from Telegram_support.utils.main import transcribe_voice

from database.engine import create_all_tables

from configs.base_config import settings
from dotenv import load_dotenv
import requests
import logging
from io import BytesIO
import json

load_dotenv()

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


def send_telegram_message(telegram_user_id: int, message_text: str, issue_key: str = None):
    """
    Відправляє повідомлення користувачу через Telegram Bot API
    і зберігає його в базу даних

    Args:
        telegram_user_id: ID користувача в Telegram
        message_text: текст повідомлення
        issue_key: ключ Jira issue (опціонально)

    Returns:
        bool: True якщо успішно, False якщо помилка
    """
    bot_token = settings.TELEGRAM_BOT_TOKEN
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    payload = {
        "chat_id": telegram_user_id,
        "text": message_text,
        "parse_mode": "HTML"
    }

    try:
        # Відправляємо повідомлення
        response = requests.post(url, json=payload)

        if response.status_code == 200:
            logger.info(f"✅ Повідомлення надіслано користувачу {telegram_user_id}")

            # Зберігаємо повідомлення в базу даних
            save_message(
                user_id=telegram_user_id,
                role="assistant",
                message=message_text,
                issue_key=issue_key
            )

            return True
        else:
            logger.error(f"❌ Помилка відправки: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        logger.error(f"❌ Помилка при відправці повідомлення: {e}")
        return False

START_CHAT, TAKE_SUMMARY, END_CHAT, PHONE  = range(4)
part_of_url_data_base = settings.PART_OF_URL_DATABASE


def send_telegram_photo(telegram_user_id: int, photo_content: bytes, filename: str, caption: str = None,
                        issue_key: str = None):
    """
    Відправляє фото в Telegram з bytes (не з файлу на диску)
    """
    bot_token = settings.TELEGRAM_BOT_TOKEN
    url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"

    try:
        # Створюємо file-like object з bytes
        files = {
            'photo': (filename, BytesIO(photo_content), 'image/png')
        }
        data = {
            'chat_id': telegram_user_id,
            'caption': caption or '',
            'parse_mode': 'HTML'
        }

        response = requests.post(url, data=data, files=files)

        if response.status_code == 200:
            logger.info(f"✅ Фото {filename} надіслано користувачу {telegram_user_id}")

            save_message(
                user_id=telegram_user_id,
                role="assistant",
                message=f"[Фото: {filename}]{' - ' + caption if caption else ''}",
                issue_key=issue_key
            )
            return True
        else:
            logger.error(f"❌ Помилка відправки: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        logger.error(f"❌ Помилка: {e}")
        return False


def send_telegram_video(telegram_user_id: int, video_content: bytes, filename: str, caption: str = None,
                        issue_key: str = None):
    """
    Відправляє відео в Telegram з bytes (не з файлу на диску)
    """
    bot_token = settings.TELEGRAM_BOT_TOKEN
    url = f"https://api.telegram.org/bot{bot_token}/sendVideo"

    try:
        # Створюємо file-like object з bytes
        files = {
            'video': (filename, BytesIO(video_content), 'video/mp4')
        }
        data = {
            'chat_id': telegram_user_id,
            'caption': caption or '',
            'parse_mode': 'HTML'
        }

        response = requests.post(url, data=data, files=files)

        if response.status_code == 200:
            logger.info(f"✅ Відео {filename} надіслано користувачу {telegram_user_id}")

            save_message(
                user_id=telegram_user_id,
                role="assistant",
                message=f"[Відео: {filename}]{' - ' + caption if caption else ''}",
                issue_key=issue_key
            )
            return True
        else:
            logger.error(f"❌ Помилка відправки відео: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        logger.error(f"❌ Помилка при відправці відео: {e}")
        return False


def send_jira_images_as_album(telegram_user_id: int, issue_key: str, media: list, files_dict: dict,  message_text: str = None):
    """
    Відправляє всі картинки одним альбомом (до 10 штук)
    """
    try:
        bot_token = settings.TELEGRAM_BOT_TOKEN
        url = f"https://api.telegram.org/bot{bot_token}/sendMediaGroup"

        data = {
            'chat_id': telegram_user_id,
            'media': json.dumps(media)
        }

        response = requests.post(url, data=data, files=files_dict)

        if response.status_code == 200:
            # Зберігаємо повідомлення в базу даних
            save_message(
                user_id=telegram_user_id,
                role="assistant",
                message=message_text,
                issue_key=issue_key
            )

            logger.info(f"✅ Альбом з {len(media)} фото надіслано")
            return True
        else:
            logger.error(f"❌ Помилка відправки альбому: {response.text}")
            return False
    except Exception as e:
        print(f'Error')


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
                    MessageHandler(filters.TEXT, self.create_summary_jira_issue),
                    MessageHandler(filters.PHOTO, self.handle_photo),
                    MessageHandler(filters.VOICE, self.handle_voice),
                    MessageHandler(filters.VIDEO, self.handle_video)
                ],
                START_CHAT: [
                    MessageHandler(filters.TEXT, self.send_message),
                    MessageHandler(filters.PHOTO, self.handle_photo),
                    MessageHandler(filters.VOICE, self.handle_voice),
                    MessageHandler(filters.VIDEO, self.handle_video),
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
        self.application.add_handler(MessageHandler(filters.PHOTO, self.handle_photo))
        self.application.add_handler(MessageHandler(filters.VOICE, self.handle_voice))
        self.application.add_handler(MessageHandler(filters.VIDEO, self.handle_video))

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


    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обробка фото від користувача"""
        user_id = update.effective_user.id
        user_db = get_user_by_telegram_id(user_id)

        if not user_db:
            await update.message.reply_text(
                "❌ Спочатку авторізуйтесь через /start"
            )
            return ConversationHandler.END

        # Отримуємо фото (беремо найбільший розмір)
        photo = update.message.photo[-1]
        photo_caption = update.message.caption or ""

        try:
            # Завантажуємо файл
            photo_file = await context.bot.get_file(photo.file_id)
            photo_bytes = await photo_file.download_as_bytearray()
            filename = f"photo_{photo.file_id}.jpg"

            # Отримуємо активний issue користувача
            active_issue_key = get_active_issue_for_user(user_id)


            # ВИПАДОК 1: Немає активного issue - створюємо новий (стан TAKE_SUMMARY)
            if not active_issue_key:
                # Отримуємо дані користувача з ERP
                response, status_response = get_user_data(user_db[4])
                if status_response != 200:
                    user_token = get_user_token(user_db[3])
                    update_erp_user_token(user_db[1], user_token)
                    response, status_response = get_user_data(user_db[4])

                user_full_name = response.json()['fullName']
                departament = response.json()['departmentJiraId']
                balance_unit = response.json()['balanceUnitJiraId']
                user_login = response.json()['login']
                telegram_user_name = update.effective_user.username

                # Створюємо summary з підпису або дефолтного тексту
                summary_text = photo_caption if photo_caption else "Фото від користувача"

                # Створюємо новий issue
                returned_issue_key = create_issue(
                    summary_from_user=summary_text,
                    description='',
                    telegram_user_id=user_id,
                    departament_id=departament,
                    balance_unit_id=balance_unit,
                    telegram_user_name=telegram_user_name,
                    user_fio=user_full_name,
                    user_login=user_login,
                )

                # Додаємо фото як attachment
                attachment_result = add_attachment_to_issue(
                    issue_key=returned_issue_key,
                    file_content=bytes(photo_bytes),
                    filename=filename
                )

                ai_work_status = get_jira_issue_ai_work_status(jira_issue_key=returned_issue_key)
                if photo_caption:
                    save_message(user_id, "user", photo_caption, issue_key=returned_issue_key)
                    history = get_chat_history_by_issue(returned_issue_key, limit=10)

                    # Створюємо коментар з фото
                    add_comment_to_issue(
                        sender='telegram_user',
                        message=summary_text,
                        issue_key=returned_issue_key,
                        attachment_filename=attachment_result.get('filename') if attachment_result.get('success') else None
                    )


                    if ai_work_status:
                        # Отримуємо відповідь від AI
                        ai_answer = chat_with_image(messages_array=history, image_bytes=bytes(photo_bytes))

                        save_message(user_id, "assistant", ai_answer, issue_key=returned_issue_key)
                        add_comment_to_issue(sender='ai_response', message=ai_answer, issue_key=returned_issue_key)

                        await update.message.reply_text(ai_answer)
                        return START_CHAT

                    return START_CHAT
                else:
                    # Якщо немає підпису - просто додаємо коментар з фото
                    if attachment_result.get('success'):
                        add_comment_to_issue(
                            sender='telegram_user',
                            message=None,
                            issue_key=returned_issue_key,
                            attachment_filename=attachment_result.get('filename')
                        )
                        if ai_work_status:
                            ai_answer = chat_with_image(messages_array=[{"role": "user", "content": 'що тут не так?'}], image_bytes=bytes(photo_bytes))

                            save_message(user_id, "assistant", ai_answer, issue_key=returned_issue_key)
                            add_comment_to_issue(sender='ai_response', message=ai_answer, issue_key=returned_issue_key)

                            await update.message.reply_text(ai_answer)
                            return START_CHAT

                    return START_CHAT

            # ВИПАДОК 2: Є активний issue - додаємо фото до нього (стан START_CHAT)
            issue_jira_status = get_jira_issue_status(active_issue_key)
            ai_work_status = get_jira_issue_ai_work_status(jira_issue_key=active_issue_key)
            if issue_jira_status == 'Done':
                keyboard = ReplyKeyboardMarkup([
                    ["Почати діалог"],
                ], resize_keyboard=True, one_time_keyboard=True)

                await update.message.reply_text(
                    f"У вас немає активних звернень"
                    f"Щоб створити нове звернення, натисніть кнопку 'Почати діалог'",
                    reply_markup=keyboard
                )
                return ConversationHandler.END

            # Додаємо attachment до існуючого issue
            attachment_result = add_attachment_to_issue(
                issue_key=active_issue_key,
                file_content=bytes(photo_bytes),
                filename=filename
            )

            if attachment_result.get('success'):
                message_text = None
                if photo_caption:
                    message_text = photo_caption

                if message_text:
                    save_message(user_id, "user", message_text, issue_key=active_issue_key)

                    # Створюємо коментар з фото
                    add_comment_to_issue(
                        sender='telegram_user',
                        message=message_text,
                        issue_key=active_issue_key,
                        attachment_filename=attachment_result.get('filename') if attachment_result.get('success') else None
                    )

                    if ai_work_status:
                        # Отримуємо відповідь від AI
                        history = get_chat_history_by_issue(active_issue_key, limit=10)
                        ai_answer = chat_with_image(messages_array=history, image_bytes=bytes(photo_bytes))

                        save_message(user_id, "assistant", ai_answer, issue_key=active_issue_key)
                        add_comment_to_issue(sender='ai_response', message=ai_answer, issue_key=active_issue_key)

                        await update.message.reply_text(ai_answer)
                        return START_CHAT

                    return START_CHAT
                else:
                    # Якщо немає підпису - просто додаємо коментар з фото
                    if attachment_result.get('success'):
                        add_comment_to_issue(
                            sender='telegram_user',
                            message=None,
                            issue_key=active_issue_key,
                            attachment_filename=attachment_result.get('filename')
                        )
                        if ai_work_status:
                            ai_answer = chat_with_image(messages_array=[{"role": "user", "content": 'що тут не так?'}], image_bytes=bytes(photo_bytes))

                            save_message(user_id, "assistant", ai_answer, issue_key=active_issue_key)
                            add_comment_to_issue(sender='ai_response', message=ai_answer, issue_key=active_issue_key)

                            await update.message.reply_text(ai_answer)
                            return START_CHAT

                    return START_CHAT
            else:
                await update.message.reply_text(
                    "❌ Помилка при завантаженні фото. Спробуйте ще раз"
                )
                return START_CHAT

        except Exception as e:
            logger.error(f"❌ Помилка при обробці фото: {e}")
            await update.message.reply_text(
                "❌ Помилка при обробці фото. Спробуйте ще раз"
            )

        return START_CHAT

    async def handle_voice(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обробка голосових повідомлень від користувача"""
        user_id = update.effective_user.id
        user_db = get_user_by_telegram_id(user_id)

        if not user_db:
            await update.message.reply_text(
                "❌ Спочатку авторізуйтесь через /start"
            )
            return ConversationHandler.END

        try:
            # Отримуємо голосове повідомлення
            voice = update.message.voice

            # Завантажуємо файл
            voice_file = await context.bot.get_file(voice.file_id)
            voice_bytes = await voice_file.download_as_bytearray()
            filename = f"voice_{voice.file_id}.ogg"

            # Конвертуємо голос в текст через OpenAI Whisper API
            transcribed_text = await transcribe_voice(bytes(voice_bytes))

            if not transcribed_text:
                await update.message.reply_text(
                    "❌ Не вдалося розпізнати голосове повідомлення. Спробуйте ще раз"
                )
                return START_CHAT

            # Отримуємо активний issue користувача
            active_issue_key = get_active_issue_for_user(user_id)

            # ВИПАДОК 1: Немає активного issue - створюємо новий (стан TAKE_SUMMARY)
            if not active_issue_key:
                # Отримуємо дані користувача з ERP
                response, status_response = get_user_data(user_db[4])
                if status_response != 200:
                    user_token = get_user_token(user_db[3])
                    update_erp_user_token(user_db[1], user_token)
                    response, status_response = get_user_data(user_db[4])

                user_full_name = response.json()['fullName']
                departament = response.json()['departmentJiraId']
                balance_unit = response.json()['balanceUnitJiraId']
                user_login = response.json()['login']
                telegram_user_name = update.effective_user.username

                # Створюємо новий issue з транскрибованим текстом
                returned_issue_key = create_issue(
                    summary_from_user=transcribed_text,
                    description='',
                    telegram_user_id=user_id,
                    departament_id=departament,
                    balance_unit_id=balance_unit,
                    telegram_user_name=telegram_user_name,
                    user_fio=user_full_name,
                    user_login=user_login,
                )

                # Додаємо голосове повідомлення як attachment
                attachment_result = add_attachment_to_issue(
                    issue_key=returned_issue_key,
                    file_content=bytes(voice_bytes),
                    filename=filename
                )

                # Зберігаємо транскрибований текст
                save_message(user_id, "user", f"[Голосове повідомлення]: {transcribed_text}", issue_key=returned_issue_key)

                # Створюємо коментар з транскрибованим текстом
                add_comment_to_issue(
                    sender='telegram_user',
                    message=f"Голосове повідомлення: {transcribed_text}",
                    issue_key=returned_issue_key,
                    attachment_filename=attachment_result.get('filename') if attachment_result.get('success') else None
                )

                ai_work_status = get_jira_issue_ai_work_status(jira_issue_key=returned_issue_key)
                if ai_work_status:
                    # Отримуємо відповідь від AI
                    ai_answer = ask_to_open_web_ui_agent([{"role": "user", "content": transcribed_text}])

                    save_message(user_id, "assistant", ai_answer, issue_key=returned_issue_key)
                    add_comment_to_issue(sender='ai_response', message=ai_answer, issue_key=returned_issue_key)

                    await update.message.reply_text(ai_answer)
                else:
                    await update.message.reply_text(f"📝 Розпізнано: {transcribed_text}")

                return START_CHAT

            # ВИПАДОК 2: Є активний issue - додаємо голосове повідомлення до нього (стан START_CHAT)
            issue_jira_status = get_jira_issue_status(active_issue_key)
            ai_work_status = get_jira_issue_ai_work_status(jira_issue_key=active_issue_key)

            if issue_jira_status == 'Done':
                keyboard = ReplyKeyboardMarkup([
                    ["Почати діалог"],
                ], resize_keyboard=True, one_time_keyboard=True)

                await update.message.reply_text(
                    f"У вас немає активних звернень"
                    f"Щоб створити нове звернення, натисніть кнопку 'Почати діалог'",
                    reply_markup=keyboard
                )
                return ConversationHandler.END

            # Додаємо attachment до існуючого issue
            attachment_result = add_attachment_to_issue(
                issue_key=active_issue_key,
                file_content=bytes(voice_bytes),
                filename=filename
            )

            # Зберігаємо транскрибований текст
            save_message(user_id, "user", f"[Голосове повідомлення]: {transcribed_text}", issue_key=active_issue_key)

            # Створюємо коментар з транскрибованим текстом
            add_comment_to_issue(
                sender='telegram_user',
                message=f"Голосове повідомлення: {transcribed_text}",
                issue_key=active_issue_key,
                attachment_filename=attachment_result.get('filename') if attachment_result.get('success') else None
            )

            if ai_work_status:
                # Отримуємо відповідь від AI
                history = get_chat_history_by_issue(active_issue_key, limit=10)
                ai_answer = ask_to_open_web_ui_agent(history)

                save_message(user_id, "assistant", ai_answer, issue_key=active_issue_key)
                add_comment_to_issue(sender='ai_response', message=ai_answer, issue_key=active_issue_key)

                await update.message.reply_text(ai_answer)
            else:
                await update.message.reply_text(transcribed_text)

            return START_CHAT

        except Exception as e:
            logger.error(f"❌ Помилка при обробці голосового повідомлення: {e}")
            await update.message.reply_text(
                "❌ Помилка при обробці голосового повідомлення. Спробуйте ще раз"
            )

        return START_CHAT

    async def handle_video(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обробка відео від користувача"""
        user_id = update.effective_user.id
        user_db = get_user_by_telegram_id(user_id)

        if not user_db:
            await update.message.reply_text(
                "❌ Спочатку авторізуйтесь через /start"
            )
            return ConversationHandler.END

        # Отримуємо відео
        video = update.message.video
        video_caption = update.message.caption or ""

        try:
            # Завантажуємо файл
            video_file = await context.bot.get_file(video.file_id)
            video_bytes = await video_file.download_as_bytearray()
            filename = f"video_{video.file_id}.mp4"

            # Отримуємо активний issue користувача
            active_issue_key = get_active_issue_for_user(user_id)

            # ВИПАДОК 1: Немає активного issue - створюємо новий (стан TAKE_SUMMARY)
            if not active_issue_key:
                # Отримуємо дані користувача з ERP
                response, status_response = get_user_data(user_db[4])
                if status_response != 200:
                    user_token = get_user_token(user_db[3])
                    update_erp_user_token(user_db[1], user_token)
                    response, status_response = get_user_data(user_db[4])

                user_full_name = response.json()['fullName']
                departament = response.json()['departmentJiraId']
                balance_unit = response.json()['balanceUnitJiraId']
                user_login = response.json()['login']
                telegram_user_name = update.effective_user.username

                # Створюємо summary з підпису або дефолтного тексту
                summary_text = video_caption if video_caption else "Відео користувача"

                # Створюємо новий issue
                returned_issue_key = create_issue(
                    summary_from_user=summary_text,
                    description='',
                    telegram_user_id=user_id,
                    departament_id=departament,
                    balance_unit_id=balance_unit,
                    telegram_user_name=telegram_user_name,
                    user_fio=user_full_name,
                    user_login=user_login,
                )

                # Додаємо відео як attachment
                attachment_result = add_attachment_to_issue(
                    issue_key=returned_issue_key,
                    file_content=bytes(video_bytes),
                    filename=filename
                )

                # Зберігаємо повідомлення
                if video_caption:
                    save_message(user_id, "user", f"[Відео]: {video_caption}", issue_key=returned_issue_key)
                    message_for_comment = video_caption
                else:
                    save_message(user_id, "user", "[Відео користувача]", issue_key=returned_issue_key)
                    message_for_comment = "Відео користувача"

                # Створюємо коментар з відео
                add_comment_to_issue(
                    sender='telegram_user',
                    message=message_for_comment,
                    issue_key=returned_issue_key,
                    attachment_filename=attachment_result.get('filename') if attachment_result.get('success') else None
                )

                await update.message.reply_text(f"✅ Відео додано до звернення {returned_issue_key}")
                return START_CHAT

            # ВИПАДОК 2: Є активний issue - додаємо відео до нього (стан START_CHAT)
            issue_jira_status = get_jira_issue_status(active_issue_key)

            if issue_jira_status == 'Done':
                keyboard = ReplyKeyboardMarkup([
                    ["Почати діалог"],
                ], resize_keyboard=True, one_time_keyboard=True)

                await update.message.reply_text(
                    f"У вас немає активних звернень"
                    f"Щоб створити нове звернення, натисніть кнопку 'Почати діалог'",
                    reply_markup=keyboard
                )
                return ConversationHandler.END

            # Додаємо attachment до існуючого issue
            attachment_result = add_attachment_to_issue(
                issue_key=active_issue_key,
                file_content=bytes(video_bytes),
                filename=filename
            )

            if attachment_result.get('success'):
                # Зберігаємо повідомлення
                if video_caption:
                    save_message(user_id, "user", f"[Відео]: {video_caption}", issue_key=active_issue_key)
                    message_for_comment = video_caption
                else:
                    save_message(user_id, "user", "[Відео користувача]", issue_key=active_issue_key)
                    message_for_comment = "Відео користувача"

                # Створюємо коментар з відео
                add_comment_to_issue(
                    sender='telegram_user',
                    message=message_for_comment,
                    issue_key=active_issue_key,
                    attachment_filename=attachment_result.get('filename')
                )

                await update.message.reply_text(f"✅ Відео додано до звернення {active_issue_key}")
                return START_CHAT
            else:
                await update.message.reply_text(
                    "❌ Помилка при завантаженні відео. Спробуйте ще раз"
                )
                return START_CHAT

        except Exception as e:
            logger.error(f"❌ Помилка при обробці відео: {e}")
            await update.message.reply_text(
                "❌ Помилка при обробці відео. Спробуйте ще раз"
            )

        return START_CHAT

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

        save_message(telegram_user_id_from_chat, "user", user_message, issue_key=returned_issue_key)
        add_comment_to_issue(sender='telegram_user' ,message=user_message, issue_key=returned_issue_key)

        # 3️⃣ Відправляємо всю історію в OpenWebUI API
        ai_answer = ask_to_open_web_ui_agent([{"role": "user", "content": user_message}])

        # 4️⃣ Зберігаємо відповідь асистента
        save_message(telegram_user_id_from_chat, "assistant", ai_answer, issue_key=returned_issue_key)
        add_comment_to_issue(sender='ai_response' ,message=ai_answer, issue_key=returned_issue_key)

        # 5️⃣ Відправляємо відповідь користувачу
        await update.message.reply_text(ai_answer)
        return START_CHAT

    async def send_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обробка повідомлень від користувача"""
        message_from_user = update.message.text
        user_id = update.effective_user.id
        # Перевіряємо чи користувач існує
        user_db = get_user_by_telegram_id(user_id)
        if not user_db:
            await update.message.reply_text(
                "❌ Спочатку авторизуйтесь через /start"
            )
            return ConversationHandler.END

        if message_from_user == 'Почати діалог' or message_from_user == '/start_chat':
            await update.message.reply_text(
                "Напишіть ваше запитання і ми вам надамо відповідь"
            )
            return TAKE_SUMMARY

        # Отримуємо активний issue користувача
        active_issue_key = get_active_issue_for_user(user_id)
        if active_issue_key:
            issue_jira_status = get_jira_issue_status(active_issue_key)
        else:
            issue_jira_status = None

        # Якщо немає активного issue - пропонуємо створити новий
        if not active_issue_key or issue_jira_status == 'Done':
            keyboard = ReplyKeyboardMarkup([
                ["Почати діалог"],
            ], resize_keyboard=True, one_time_keyboard=True)

            await update.message.reply_text(f"Натисніть кнопку 'Почати діалог''",
                reply_markup=keyboard)
            return ConversationHandler.END

        save_message(user_id, "user", message_from_user, issue_key=active_issue_key)
        add_comment_to_issue(sender='telegram_user', message=message_from_user, issue_key=active_issue_key)

        ia_work_status = get_jira_issue_ai_work_status(jira_issue_key=active_issue_key)
        if ia_work_status:
            # Отримуємо історію саме по цьому тікету
            history = get_chat_history_by_issue(active_issue_key, limit=10)

            ai_answer = ask_to_open_web_ui_agent(history)

            save_message(user_id, "assistant", ai_answer, issue_key=active_issue_key)
            add_comment_to_issue(sender='ai_response', message=ai_answer, issue_key=active_issue_key)

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