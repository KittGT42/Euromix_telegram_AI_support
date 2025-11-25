from flask import Flask, request
import json
from Telegram_support.database.crud import update_jira_issue_status, get_telegram_user_id_by_issue
from Telegram_support.main import send_telegram_message

app = Flask(__name__)


@app.route('/webhook_jira_comment', methods=['POST'])
def webhook_comment():
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
            return "OK"

        if account_id in skip_technical_account:
            return "OK"

        # Отримуємо telegram_user_id по issue_key
        telegram_user_id = get_telegram_user_id_by_issue(issue_key)

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

    except Exception as e:
        print(f"❌ Помилка обробки webhook: {e}")
        return "ERROR", 500

@app.route('/webhook_issue_status', methods=['POST'])
def webhook_issue_status():
    # Отримуємо дані
    data = request.json
    status_issue = data['issue']['fields']['status']['name']
    issue_key = data['issue']['key']
    update_jira_issue_status(issue_key, status_issue)

    # Виводимо в консоль
    print("=== WEBHOOK RECEIVED ===")
    print(json.dumps(data, indent=2, ensure_ascii=False))
    print("========================")

    return "OK"




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

