import requests
import base64

def summary_agent(dialog_context):
    response = requests.post(
        "https://ai.euromix.in.ua/api/chat/completions",
        headers={
            "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjhjOWQ2ZTBkLWRmYzMtNDNmNy1hZjcxLWFjMjJlNWI1NWNkOSJ9.H3aCuXDzE7iYr1INXbbkFzMZbCux2BFc7wwPSiAxzUI",
            "Content-Type": "application/json"
        },
        json={
            "model": "summaryagenttickettitle",
            "messages": [{"role": "user", "content": dialog_context}],
            "stream": False
        }
    )

    if response.status_code == 200:
        result = response.json()
        response_agent = result['choices'][0]['message']['content']
    else:
        response_agent = None
    return response_agent


def description_agent(dialog_context):
    response = requests.post(
        "https://ai.euromix.in.ua/api/chat/completions",
        headers={
            "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjhjOWQ2ZTBkLWRmYzMtNDNmNy1hZjcxLWFjMjJlNWI1NWNkOSJ9.H3aCuXDzE7iYr1INXbbkFzMZbCux2BFc7wwPSiAxzUI",
            "Content-Type": "application/json"
        },
        json={
            "model": "summaryagentticketdescription",
            "messages": [{"role": "user", "content": dialog_context}],
            "stream": False
        }
    )

    if response.status_code == 200:
        result = response.json()
        response_agent = result['choices'][0]['message']['content']
    else:
        response_agent = None
    return response_agent


def ask_to_open_web_ui_agent(messages_array):
    """
    Відправляє масив повідомлень в OpenWebUI API.

    Args:
        messages_array: List[dict] у форматі [{"role": "user", "content": "..."}]
    """
    response = requests.post(
        "https://ai.euromix.in.ua/api/chat/completions",
        headers={
            "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjhjOWQ2ZTBkLWRmYzMtNDNmNy1hZjcxLWFjMjJlNWI1NWNkOSJ9.H3aCuXDzE7iYr1INXbbkFzMZbCux2BFc7wwPSiAxzUI",
            "Content-Type": "application/json"
        },
        json={
            "model": "euromixsupportagent",
            "messages": messages_array,
            "stream": False,
            "files": [
                {"type": "collection", "id": "ffc3373a-148f-49dc-947f-fd8db6e6d9cc"}
            ]
        }
    )

    ai_response = ""
    if response.status_code == 200:
        result = response.json()
        ai_response = result['choices'][0]['message']['content']

    return ai_response


def chat_with_image(messages_array, image_bytes):
    """
    Відправляє масив повідомлень в OpenWebUI API.

    Args:
        messages_array: List[dict] у форматі [{"role": "user", "content": "..."}]
        image_bytes: image bytes
    """

    base64_image = base64.b64encode(image_bytes).decode('utf-8')

    image_url = f"data:image/jpeg;base64,{base64_image}"
    response = requests.post(
        "https://ai.euromix.in.ua/api/chat/completions",
        headers={
            "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjhjOWQ2ZTBkLWRmYzMtNDNmNy1hZjcxLWFjMjJlNWI1NWNkOSJ9.H3aCuXDzE7iYr1INXbbkFzMZbCux2BFc7wwPSiAxzUI",
            "Content-Type": "application/json"
        },
        json={
            "model": "euromixsupportagent",
            "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": str(messages_array)},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_url
                        }
                    }
                ]
            }
        ],
            "stream": False,
            "files": [
                {"type": "collection", "id": "ffc3373a-148f-49dc-947f-fd8db6e6d9cc"}
            ]
        }
    )

    ai_response = ""
    if response.status_code == 200:
        result = response.json()
        ai_response = result['choices'][0]['message']['content']

    return ai_response