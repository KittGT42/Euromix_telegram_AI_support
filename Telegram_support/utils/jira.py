import os
from dotenv import load_dotenv

import requests
from requests.auth import HTTPBasicAuth

import json

from Telegram_support.database.crud import save_jira_issue

load_dotenv()

def create_issue(summary_from_user: str, description: str, telegram_user_id, telegram_user_number,
                 telegram_user_full_name, service_app_name: str, telegram_user_link: str = None, project_key: str = "TP"):

    url = "https://zabutniy15.atlassian.net/rest/api/3/issue"

    auth = HTTPBasicAuth("zabutniy15@gmail.com", os.getenv("JIRA_API_TOKEN"))

    headers = {
      "Accept": "application/json",
      "Content-Type": "application/json"
    }


    data = json.dumps({
        'fields': {
            'project': {
                'key': project_key
            },
            "assignee": {
                "id": "712020:0abca624-07e3-4beb-bc81-b705121bb567"
            },
            "customfield_10062": str(telegram_user_id),
            "customfield_10059": telegram_user_number,
            "customfield_10060": telegram_user_full_name,
            "customfield_10061": telegram_user_link,
            'summary': summary_from_user,
            'issuetype': {
                'name': 'Task'
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
            }
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


def add_comment_to_issue(message: str = None, issue_key: str = None):
    url = f"https://zabutniy15.atlassian.net/rest/api/3/issue/{issue_key}/comment"

    auth = HTTPBasicAuth("zabutniy15@gmail.com", os.getenv("JIRA_API_TOKEN"))

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

def main():
    add_comment_to_issue()

if __name__ == '__main__':
    main()

