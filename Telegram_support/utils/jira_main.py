import os
from dotenv import load_dotenv

import requests
from requests.auth import HTTPBasicAuth

import json

from Telegram_support.database.crud import save_jira_issue
import re

import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

HEADERS_MAIN = {
      "Accept": "application/json",
      "Content-Type": "application/json"
    }

AUTH_MAIN_KOSTROMSKIY = HTTPBasicAuth("Dmitriy.Kostromskiy@euromix.in.ua", os.getenv("JIRA_API_TOKEN"))
AUTH_MAIN_TG_BOT = HTTPBasicAuth("tgbot@euromix.in.ua", os.getenv("JIRA_API_TOKEN_TELEGRAM_USER"))
AUTH_MAIN_AI_TG_BOT = HTTPBasicAuth("aitgbot@euromix.in.ua", os.getenv("JIRA_API_TOKEN_TELEGRAM_AI"))

JIRA_EUROMIX_MAIN_URL = "https://euromix.atlassian.net"

def create_issue(summary_from_user: str, description: str, telegram_user_id, departament_id: str, balance_unit_id: str,
                 telegram_user_name: str, user_fio: str, user_login: str,
                 service_app_name: str = 'E-mix 3.x',project_key: str = "SD",
                 group: str = '10036', issue_type: str = '10139', reporter_id: str = '712020:253569d1-370f-4872-823a-1467b196c19b',
                 service_name_id: str = '10227'):

    url = "https://euromix.atlassian.net/rest/api/3/issue"

    auth = HTTPBasicAuth("Dmitriy.Kostromskiy@euromix.in.ua", os.getenv("JIRA_API_TOKEN"))
    # auth = HTTPBasicAuth("tgbot@euromix.in.ua", os.getenv("JIRA_API_TOKEN_TELEGRAM_USER"))

    headers = {
      "Accept": "application/json",
      "Content-Type": "application/json"
    }


    data = json.dumps({
        'fields': {
            'project': {
                'key': project_key
            },
            # "assignee": {
            #     "id": assignee_id
            # },
            'summary': summary_from_user,
            # 'customfield_10041': Group,
            'customfield_10041': {
                'id': group
            },
            # issuetype 10139 == Telegram
            'issuetype': {
                'id': issue_type
            },
            'description': {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {
                                "type": "text",
                                "text": description
                            }
                        ]
                    }
                ]
            },
            'reporter': {
                'id': reporter_id
            },
            # 'customfield_10065': 'DepartamentID',
            'customfield_10065': {
                'id': departament_id
            },
            'priority': {
                'id': '3'
            },
            # 'customfield_10145': telegram_user_id,
            'customfield_10145': str(telegram_user_id),
            # 'customfield_10068': 'E-mix 3.x', Service name
            'customfield_10068': {
                'id': service_name_id
            },
            #'customfield_10069': 'Балансова Одиниця (Підрозділ)'
            'customfield_10069': {
                'id': balance_unit_id
            },
            # 'customfield_10146': 'Telegram @username'
            'customfield_10146': telegram_user_name,
            # ФИО пользователя из ЕРП для ТГ тикетов
            'customfield_10244' : user_fio,
            #Логін пользователя Ємікс 3 из ЕРП
            'customfield_10245' : user_login,


        }
    })


    response = requests.request(
       "POST",
       url,
       data=data,
       headers=headers,
       auth=auth
    )
    issue_key = response.json()['key']

    save_jira_issue(telegram_user_id, issue_key, service_app_name=service_app_name)

    return response.json()['key']


def add_comment_to_issue(sender: str, message: str = None, issue_key: str = None, attachment_filename: str = None):
    """
    Додає коментар до Jira issue

    Args:
        sender: 'telegram_user' або 'ai_response'
        message: Текст коментаря
        issue_key: Ключ Jira issue
        attachment_filename: Ім'я файлу attachment для вставки в коментар (опціонально)
    """
    if sender == 'telegram_user':
        auth = HTTPBasicAuth("tgbot@euromix.in.ua", os.getenv("JIRA_API_TOKEN_TELEGRAM_USER"))
    else:
        auth = HTTPBasicAuth("aitgbot@euromix.in.ua", os.getenv("JIRA_API_TOKEN_TELEGRAM_AI"))

    # Якщо є attachment - використовуємо API v2 (підтримує Wiki markup)
    if attachment_filename:
        url = f"https://euromix.atlassian.net/rest/api/2/issue/{issue_key}/comment"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        # Формуємо текст коментаря з Jira image syntax
        comment_text = ""
        if message:
            comment_text = f"{message}\n\n"
        comment_text += f"!{attachment_filename}|thumbnail!"

        payload = json.dumps({
            "body": comment_text
        })
    else:
        # Без attachment - використовуємо API v3 (ADF формат)
        url = f"https://euromix.atlassian.net/rest/api/3/issue/{issue_key}/comment"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        content = []
        if message:
            content.append({
                "content": [
                    {
                        "text": f"{message}",
                        "type": "text"
                    }
                ],
                "type": "paragraph"
            })

        payload = json.dumps({
            "body": {
                "content": content,
                "type": "doc",
                "version": 1
            },
        })

    response = requests.request(
        "POST",
        url,
        data=payload,
        headers=headers,
        auth=auth
    )

    print(json.dumps(json.loads(response.text), sort_keys=True, indent=4, separators=(",", ": ")))
    return response

def update_jira_issue(summary: str, description: str, issue_key: str = None):
    url = f"https://euromix.atlassian.net/rest/api/3/issue/{issue_key}"

    auth = HTTPBasicAuth("Dmitriy.Kostromskiy@euromix.in.ua", os.getenv("JIRA_API_TOKEN"))

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    data = json.dumps({
        'fields': {
            'summary': summary,
            'description': {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {
                                "type": "text",
                                "text": description
                            }
                        ]
                    }
                ]
            }
        }
    })

    response = requests.request(
        "PUT",
        url,
        data=data,
        headers=headers,
        auth=auth
    )

    return response.status_code


def download_jira_attachment(issue_key, filename):
    """
    Завантажує attachment з Jira
    """
    auth = HTTPBasicAuth("Dmitriy.Kostromskiy@euromix.in.ua", os.getenv("JIRA_API_TOKEN"))

    url = f"https://euromix.atlassian.net/rest/api/2/issue/{issue_key}"

    response = requests.get(url, auth=auth)
    issue_data = response.json()

    # Шукаємо потрібний attachment
    attachments = issue_data.get('fields', {}).get('attachment', [])

    for attachment in attachments:
        if filename in attachment['filename']:
            # Завантажуємо файл
            file_url = attachment['content']
            file_response = requests.get(file_url, auth=auth)

            return {
                'content': file_response.content,
                'filename': attachment['filename'],
                'mimetype': attachment['mimeType']
            }

    return None


def get_attachment_type(issue_key, filename):
    """
    Визначає тип attachment (image або video) за mimetype

    Шукає attachment за ім'ям файлу (підтримує часткове співпадіння, бо Jira може додавати UUID)
    """
    auth = HTTPBasicAuth("Dmitriy.Kostromskiy@euromix.in.ua", os.getenv("JIRA_API_TOKEN"))
    url = f"https://euromix.atlassian.net/rest/api/2/issue/{issue_key}"

    try:
        response = requests.get(url, auth=auth)
        issue_data = response.json()

        attachments = issue_data.get('fields', {}).get('attachment', [])

        # Спочатку шукаємо точний збіг
        for attachment in attachments:
            if attachment['filename'] == filename:
                mimetype = attachment.get('mimeType', '')
                if mimetype.startswith('video/'):
                    return 'video'
                elif mimetype.startswith('image/'):
                    return 'image'

        # Якщо точного збігу немає, шукаємо часткове співпадіння
        # (корисно коли Jira додає UUID до імені файлу)
        for attachment in attachments:
            if filename in attachment['filename'] or attachment['filename'] in filename:
                mimetype = attachment.get('mimeType', '')
                if mimetype.startswith('video/'):
                    return 'video'
                elif mimetype.startswith('image/'):
                    return 'image'

    except Exception as e:
        print(f"❌ Помилка при отриманні типу attachment: {e}")

    return 'image'  # За замовчуванням вважаємо що це зображення


def parse_jira_comment(body, issue_key=None):
    """
    Розділяє Jira коментар на текст та інформацію про медіа файли (картинки та відео)

    Jira використовує різний синтаксис для різних типів attachments:
    - Зображення: !filename|parameters!
    - Відео та інші файли: [^filename]
    """
    # Regex для знаходження Jira image syntax: !filename|parameters!
    image_pattern = r'!([^|!]+)\|[^!]*!'

    # Regex для знаходження Jira attachment syntax: [^filename]
    attachment_pattern = r'\[\^([^\]]+)\]'

    # Знаходимо всі зображення
    image_files = re.findall(image_pattern, body)

    # Знаходимо всі attachments (відео, документи тощо)
    attachment_files = re.findall(attachment_pattern, body)

    # Видаляємо всі медіа файли з тексту
    clean_text = body
    clean_text = re.sub(image_pattern, '', clean_text)
    clean_text = re.sub(attachment_pattern, '', clean_text).strip()

    # Розділяємо на фото та відео
    images = []
    videos = []

    if issue_key:
        # Обробляємо зображення
        for filename in image_files:
            images.append(filename)

        # Обробляємо attachments (можуть бути відео або інші файли)
        for filename in attachment_files:
            file_type = get_attachment_type(issue_key, filename)
            if file_type == 'video':
                videos.append(filename)
            else:
                # Якщо це не відео, можливо це зображення без синтаксису !filename!
                file_type_check = get_attachment_type(issue_key, filename)
                if file_type_check == 'image':
                    images.append(filename)
    else:
        # Якщо issue_key не передано, вважаємо все зображеннями
        images = image_files + attachment_files

    return {
        'text': clean_text,
        'images': images,
        'images_count': len(images),
        'videos': videos,
        'videos_count': len(videos)
    }


def add_attachment_to_issue(issue_key: str, file_content: bytes, filename: str):
    """
    Завантажує файл як attachment до Jira issue

    Args:
        issue_key: Ключ Jira issue (наприклад, 'SD-12345')
        file_content: Вміст файлу в bytes
        filename: Ім'я файлу

    Returns:
        dict: {'success': True, 'attachment_id': 'xxx', 'filename': 'xxx'} якщо успішно
        dict: {'success': False} якщо помилка
    """
    url = f"https://euromix.atlassian.net/rest/api/3/issue/{issue_key}/attachments"

    auth = HTTPBasicAuth("tgbot@euromix.in.ua", os.getenv("JIRA_API_TOKEN_TELEGRAM_USER"))

    headers = {
        "Accept": "application/json",
        "X-Atlassian-Token": "no-check"
    }

    files = {
        'file': (filename, file_content, 'image/jpeg')
    }

    try:
        response = requests.post(url, headers=headers, files=files, auth=auth)

        if response.status_code == 200:
            attachment_data = response.json()[0]  # Jira повертає масив attachments
            print(f"✅ Attachment {filename} додано до issue {issue_key}")
            print(f"Attachment ID: {attachment_data.get('id')}")
            return {
                'success': True,
                'attachment_id': attachment_data.get('id'),
                'filename': attachment_data.get('filename')
            }
        else:
            print(f"❌ Помилка додавання attachment: {response.status_code} - {response.text}")
            return {'success': False}

    except Exception as e:
        print(f"❌ Помилка при завантаженні attachment: {e}")
        return {'success': False}


def add_comment_with_mentions(sender: str, message: str, issue_key: str, mention_account_ids: list):
    """
    Додає коментар до Jira issue з mentions користувачів.

    Args:
        sender: 'ai_response' або 'telegram_user'
        message: текст коментаря
        issue_key: ключ issue (напр. "AITG-123")
        mention_account_ids: список account ID для @mention

    Returns:
        dict: відповідь від Jira API або None при помилці
    """
    url = f"{JIRA_EUROMIX_MAIN_URL}/rest/api/3/issue/{issue_key}/comment"

    # Створюємо ADF структуру
    adf_content = []

    # Параграф з mentions
    mention_paragraph = {
        "type": "paragraph",
        "content": []
    }

    for i, account_id in enumerate(mention_account_ids):
        mention_paragraph["content"].append({
            "type": "mention",
            "attrs": {
                "id": account_id
            }
        })
        # Пробіл після кожного mention (крім останнього)
        if i < len(mention_account_ids) - 1:
            mention_paragraph["content"].append({
                "type": "text",
                "text": " "
            })

    adf_content.append(mention_paragraph)

    # Додаємо текст повідомлення (кожен рядок = окремий параграф)
    for line in message.split('\n'):
        if line.strip():
            adf_content.append({
                "type": "paragraph",
                "content": [{
                    "type": "text",
                    "text": line
                }]
            })

    # Тіло запиту з ADF
    payload = {
        "body": {
            "version": 1,
            "type": "doc",
            "content": adf_content
        }
    }

    # Додаємо властивості залежно від sender
    if sender == 'ai_response':
        payload["properties"] = [
            {
                "key": "sd.public.comment",
                "value": {"internal": False}
            }
        ]
    elif sender == 'telegram_user':
        payload["properties"] = [
            {
                "key": "sd.public.comment",
                "value": {"internal": True}
            }
        ]

    response = requests.post(
        url,
        json=payload,
        headers=HEADERS_MAIN,
        auth=AUTH_MAIN_AI_TG_BOT
    )

    if response.status_code == 201:
        logger.info(f"✅ Коментар з mentions додано до {issue_key} (від {sender})")
        return response.json()
    else:
        logger.error(f"❌ Помилка додавання коментаря з mentions: {response.status_code} - {response.text}")
        return None

def main():
    # add_comment_to_issue()

    update_issue = update_jira_issue(summary='test112233', description='test777', issue_key='SD-48007')
    print(update_issue)

if __name__ == '__main__':
    main()

