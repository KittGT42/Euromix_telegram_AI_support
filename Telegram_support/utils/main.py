import base64


def convert_image_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def format_conversation_to_string(messages):
    """
    Перетворює список повідомлень у строку формату: роль: повідомлення
    """
    role_names = {
        'user': 'Користувач',
        'assistant': 'Асистент'
    }

    formatted_parts = []
    for msg in messages:
        role = role_names.get(msg['role'], msg['role'])
        content = msg['content']
        formatted_parts.append(f"{role}: {content}")

    return "\n\n".join(formatted_parts)