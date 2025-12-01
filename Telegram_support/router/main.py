from flask import Flask, request
import json
from Telegram_support.database.crud import (update_jira_issue_status, get_telegram_user_id_by_issue,
                                            update_jira_issue_ai_work_status, get_chat_history_by_issue,
                                            get_jira_issue_status)
from Telegram_support.utils.open_web_ui_agents_requests import summary_agent, description_agent
from Telegram_support.utils.jira import update_jira_issue, parse_jira_comment, download_jira_attachment
from Telegram_support.utils.main import format_conversation_to_string

from Telegram_support.main import send_telegram_message, send_telegram_photo, send_jira_images_as_album

from io import BytesIO
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)


@app.route('/webhook_jira_issue_comment', methods=['POST'])
def webhook_jira_comment():
    """
    Обробляє коментарі від Jira і відправляє їх користувачу в Telegram
    """
    try:
        skip_technical_account = ['712020:253569d1-370f-4872-823a-1467b196c19b', '712020:7f143a9c-5ce8-4a82-ae04-c1ab42bfba32']
        # Отримуємо дані
        data = request.json
        message_to_user = data['comment']['body']
        account_id = data['comment']['author']['accountId']
        issue_key = data['issue']['key']

        if 'stop' in message_to_user.lower():
            try:
                update_jira_issue_ai_work_status(issue_key, False)
            except Exception as e:
                print(f'Error updating jira issue ai work status: {e}')

            return "OK"

        if account_id in skip_technical_account:
            return "OK"

        result_parse_comment = parse_jira_comment(message_to_user)
        message_to_user = result_parse_comment.get('text')
        image_count = result_parse_comment.get('images_count')
        telegram_user_id = get_telegram_user_id_by_issue(issue_key)
        images_names = result_parse_comment.get('images')
        if image_count == 0:
            try:
                update_jira_issue_ai_work_status(issue_key, False)
            except Exception as e:
                print(f'Error updating jira issue ai work status: {e}')

            if telegram_user_id:
                send_telegram_message(
                    telegram_user_id=telegram_user_id,
                    message_text=message_to_user,
                    issue_key=issue_key
                )
                print(f"✅ Повідомлення відправлено користувачу {telegram_user_id}")
            else:
                print(f"⚠️ Не знайдено telegram_user_id для issue {issue_key}")

            return "OK"
        elif image_count == 1:
            attachment = download_jira_attachment(issue_key, images_names[0])
            if attachment:
                send_telegram_photo(
                    telegram_user_id=telegram_user_id,
                    photo_content=attachment['content'],
                    filename=attachment['filename'],
                    caption=message_to_user,  # Текст як підпис
                    issue_key=issue_key
                )
            return "OK"
        elif 2 <= image_count <= 10:
            try:
                # Підготовка media array
                media = []
                files_dict = {}

                for i, filename in enumerate(images_names):
                    attachment = download_jira_attachment(issue_key, filename)

                    if not attachment:
                        continue

                    # Унікальний ключ для кожного файлу
                    file_key = f"photo_{i}"

                    # Додаємо в files для upload
                    files_dict[file_key] = (
                        attachment['filename'],
                        BytesIO(attachment['content']),
                        attachment['mimetype']
                    )

                    # Формуємо media item
                    media_item = {
                        'type': 'photo',
                        'media': f'attach://{file_key}'
                    }

                    # Підпис тільки до першої картинки
                    if i == 0 and message_to_user:
                        media_item['caption'] = message_to_user
                        media_item['parse_mode'] = 'HTML'

                    media.append(media_item)

                send_jira_images_as_album(telegram_user_id=telegram_user_id,issue_key=issue_key,
                                          media=media, files_dict=files_dict, message_text=message_to_user)
                return "OK"
            except Exception as e:
                print(f"Error uploading images: {e}")
                return "ERROR", 500

        elif image_count > 10:
            if message_to_user:
                send_telegram_message(telegram_user_id=telegram_user_id,
                                      message_text=message_to_user,issue_key=issue_key)

            for i, filename in enumerate(images_names):
                # Завантажуємо attachment з Jira
                attachment = download_jira_attachment(issue_key, filename)

                if not attachment:
                    logger.warning(f"⚠️ Не знайдено attachment: {filename}")
                    continue

                try:
                    send_telegram_photo(
                        telegram_user_id=telegram_user_id,
                        photo_content=attachment['content'],
                        filename=attachment['filename'],
                        issue_key=issue_key
                    )
                except Exception as e:
                    logger.error(f"Error sending photo: {e}")

            return "OK"


    except Exception as e:
        print(f"❌ Помилка обробки webhook: {e}")
        return "ERROR", 500

@app.route('/webhook_jira_issue_status', methods=['POST'])
def webhook_jira_issue_status():
    """
    Обробляє зміну статусу Jira issue і оновлює дані при завершенні
    """
    try:
        # Отримуємо дані
        data = request.json

        # Перевіряємо наявність необхідних полів
        if not data or 'issue' not in data:
            print("⚠️ Отримано некоректні дані")
            return "ERROR: Invalid data", 400

        issue_key = data['issue']['key']
        status_issue = data['issue']['fields']['statusCategory']['key']

        status_issue_in_db = get_jira_issue_status(issue_key)

        # Обробляємо тільки статус 'done'
        if status_issue == 'done' and status_issue_in_db != 'Done':
            print(f"📝 Issue {issue_key} переведено в статус Done")

            # Оновлюємо статус в БД
            update_jira_issue_status(issue_key, 'Done')

            # Отримуємо історію діалогу
            dialog_content = get_chat_history_by_issue(issue_key=issue_key)
            convert_dialog_content_to_string = format_conversation_to_string(dialog_content)

            if dialog_content:
                # Генеруємо summary та description через AI агентів
                agent_response_for_summary = summary_agent(dialog_context=convert_dialog_content_to_string)
                agent_response_for_description = description_agent(dialog_context=convert_dialog_content_to_string)

                # Оновлюємо Jira issue
                update_jira_issue(
                    issue_key=issue_key,
                    description=agent_response_for_description,
                    summary=agent_response_for_summary
                )
                print(f"✅ Issue {issue_key} успішно оновлено")
            else:
                print(f"⚠️ Не знайдено історію діалогу для issue {issue_key}")

        return "OK"

    except KeyError as e:
        print(f"❌ Відсутнє поле в даних: {e}")
        return "ERROR: Missing field", 400
    except Exception as e:
        print(f"❌ Помилка обробки webhook статусу: {e}")
        return "ERROR", 500




@app.route('/article_to_barcode', methods=['POST'])
def article_to_barcode():
    # Отримуємо дані
    data = request.json



    return {'barcode': 'Штрихкод  00332255668899'}

@app.route('/webhook_file', methods=['POST'])
def webhook_file():
    # Отримуємо дані
    data = request.json

    # Виводимо в консоль
    print("=== WEBHOOK RECEIVED ===")
    print(json.dumps(data, indent=2, ensure_ascii=False))
    print("========================")

    return "OK"


@app.route('/', methods=['GET'])
def home():
    return "Webhook server працює!"


if __name__ == '__main__':
    print("Сервер запущено на http://localhost:8080")
    print("Webhook URL: http://localhost:8080/webhook")
    app.run(host='0.0.0.0', port=8080, debug=True)

