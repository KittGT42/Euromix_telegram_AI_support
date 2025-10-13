from sqlmodel import create_engine, Session, SQLModel
from configs.base_config import settings
import logging

logger = logging.getLogger(__name__)

# URL підключення до PostgreSQL
DATABASE_URL = (
    f"postgresql+psycopg://{settings.DB_USER}:{settings.DB_PASSWORD}"
    f"@{settings.DB_HOST}/{settings.DB_NAME}"
)

# Engine для підключення
engine = create_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True
)


def create_all_tables():
    """
    Створює ВСІ таблиці з усіх сервісів.
    Викликається при старті будь-якого бота.
    """
    try:
        from Telegram_support.database.models import TelegramUser, ChatHistory

        SQLModel.metadata.create_all(engine)
        logger.info("✅ All database tables created successfully")
    except Exception as e:
        logger.error(f"❌ Error creating database tables: {e}")
        raise


def get_session():
    """Генератор сесії для роботи з БД"""
    with Session(engine) as session:
        yield session