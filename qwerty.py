import requests


response = requests.post(
        "https://ai.euromix.in.ua/api/chat/completions",
        headers={
            "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjhjOWQ2ZTBkLWRmYzMtNDNmNy1hZjcxLWFjMjJlNWI1NWNkOSJ9.H3aCuXDzE7iYr1INXbbkFzMZbCux2BFc7wwPSiAxzUI",
            "Content-Type": "application/json"
        },
        json={
            "model": "summaryagentticketdescription",
            "messages": [{"role": "user", "content": '123'}],
            "stream": False
        }
    )
print(response.json())