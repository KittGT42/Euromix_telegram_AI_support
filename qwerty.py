import requests
import base64

def convert_image_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def chat_with_image(user_prompt, image_path):
    """
    Відправляє масив повідомлень в OpenWebUI API.

    Args:
        messages_array: List[dict] у форматі [{"role": "user", "content": "..."}]
    """

    base64_image = convert_image_to_base64(image_path)

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
                    {"type": "text", "text": user_prompt},
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


result_from_ai = chat_with_image(user_prompt='що тут не так', image_path='telegram-3715096143596989257file_8996.jpg')
print(result_from_ai)