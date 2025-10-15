from flask import Flask, request
import json
from Telegram_support.database.crud import update_jira_issue_status

app = Flask(__name__)


@app.route('/webhook_comment', methods=['POST'])
def webhook_comment():
    # Отримуємо дані
    data = request.json

    # Виводимо в консоль
    print("=== WEBHOOK RECEIVED ===")
    print(json.dumps(data, indent=2, ensure_ascii=False))
    print("========================")

    return "OK"

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

