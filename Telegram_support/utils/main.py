import base64
import openai
from configs.base_config import settings
from io import BytesIO
import logging
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

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

async def transcribe_voice(voice_bytes: bytes) -> str:
    """Транскрибує голосове повідомлення в текст через OpenAI Whisper API"""
    try:
        # Налаштування OpenAI API ключа
        openai.api_key = settings.OPENAI_API_KEY

        # Створюємо file-like object з bytes
        voice_file = BytesIO(voice_bytes)
        voice_file.name = "voice.ogg"

        # Викликаємо Whisper API
        transcript = openai.audio.transcriptions.create(
            model="whisper-1",
            file=voice_file,
            language="uk"  # Українська мова
        )

        return transcript.text

    except Exception as e:
        logger.error(f"❌ Помилка транскрипції: {e}")
        return None