import os
from dotenv import load_dotenv

import requests
from requests.auth import HTTPBasicAuth

import json

from Telegram_support.database.crud import save_jira_issue

load_dotenv()

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


def add_comment_to_issue(sender: str,message: str = None, issue_key: str = None):
    url = f"https://euromix.atlassian.net/rest/api/3/issue/{issue_key}/comment"
    if sender == 'telegram_user':
        auth = HTTPBasicAuth("tgbot@euromix.in.ua", os.getenv("JIRA_API_TOKEN_TELEGRAM_USER"))
    else:
        auth = HTTPBasicAuth("aitgbot@euromix.in.ua", os.getenv("JIRA_API_TOKEN_TELEGRAM_AI"))

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    payload = json.dumps({
        "body": {
            "content": [
                {
                    "content": [
                        {
                            "text": f"{message}",
                            "type": "text"
                        }
                    ],
                    "type": "paragraph"
                }
            ],
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

def main():
    # add_comment_to_issue()

    update_issue = update_jira_issue(summary_from_user='test112233', description='test777', issue_key='SD-48007')
    print(update_issue)

if __name__ == '__main__':
    main()

