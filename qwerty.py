import requests
from requests.auth import HTTPBasicAuth
import json
from dotenv import load_dotenv
import os

load_dotenv()

#
# url = f'https://mobile.euromix.in.ua/unisales/hs/ex3/profile'
# headers = {
#     'Accept': '*/*',
#     'Content-Type': 'application/json',
#     'Authorization': f'Bearer 53d7aa0f63f7409fa3c03ad4147ab80a',
# }
#
# response = requests.get(url, headers=headers)
# status_response = response.status_code
#
# print(response.json())

def get_issue_by_key(issue_key):
    url = f"https://euromix.atlassian.net/rest/api/3/issue/{issue_key}"

    auth = HTTPBasicAuth("Dmitriy.Kostromskiy@euromix.in.ua", os.getenv("JIRA_API_TOKEN"))

    headers = {
      "Accept": "application/json"
    }

    response = requests.request(
       "GET",
       url,
       headers=headers,
       auth=auth
    )

    print(json.dumps(json.loads(response.text), sort_keys=True, indent=4, separators=(",", ": ")))

def get_edit_meta_by_issue_key(issue_key):

    url = f"https://euromix.atlassian.net//rest/api/3/issue/{issue_key}/editmeta"

    auth = HTTPBasicAuth("Dmitriy.Kostromskiy@euromix.in.ua", os.getenv("JIRA_API_TOKEN"))

    headers = {
      "Accept": "application/json"
    }

    response = requests.request(
       "GET",
       url,
       headers=headers,
       auth=auth
    )

    print(json.dumps(json.loads(response.text), sort_keys=True, indent=4, separators=(",", ": ")))

def get_user_token(phone_number):
    data_response = requests.post(f"https://mobile.euromix.in.ua/testapp/hs/ex3/sign_in",
                                  json={"identity": {"phone": phone_number}})
    data_response_json = data_response.json()
    if data_response.status_code == 401:
        return False
    user_token = data_response_json['data']['access_token']
    return user_token

def get_user_data(user_token):
    url = f'https://mobile.euromix.in.ua/testapp/hs/ex3/profile'
    headers = {
        'Accept': '*/*',
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {user_token}',
    }

    response = requests.get(url, headers=headers)
    status_response = response.status_code

    return response, status_response


# get_edit_meta_by_issue_key('SD-46442')

# user_token = get_user_token('+380993394328')
response, user_data = get_user_data('c940d7a04b4942ed97f9922a7e6ff95e1111')
user_full_name = response.json()['fullName']
departament = response.json()['departmentJiraId']
balance_unit = response.json()['balanceUnitJiraId']
user_login = response.json()['login']
print(user_login, user_full_name, departament, balance_unit)


