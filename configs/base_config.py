
from dotenv import load_dotenv
import os

load_dotenv()

class Settings:
    #server camera url
    SERVER_URL_WEBCAMERA: str = os.getenv("SERVER_URL_WEBCAMERA")
    # telegram bot token
    TELEGRAM_BOT_TOKEN : str = os.getenv("BOT_TOKEN")

    #testapp or unisales for 1C database
    PART_OF_URL_DATABASE : str = os.getenv("PART_OF_URL_DATABASE")

    #connection to a database
    DB_HOST : str = os.getenv("DB_HOST")
    DB_NAME : str = os.getenv("DB_NAME")
    DB_USER : str = os.getenv("DB_USER")
    DB_PASSWORD : str = os.getenv("DB_PASSWORD")

    # OpenAI API key for voice transcription
    OPENAI_API_KEY : str = os.getenv("OPENAI_API_KEY")



settings = Settings()
