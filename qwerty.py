import requests


url = f'https://mobile.euromix.in.ua/unisales/hs/ex3/profile'
headers = {
    'Accept': '*/*',
    'Content-Type': 'application/json',
    'Authorization': f'Bearer 53d7aa0f63f7409fa3c03ad4147ab80a',
}

response = requests.get(url, headers=headers)
status_response = response.status_code

print(response.json())