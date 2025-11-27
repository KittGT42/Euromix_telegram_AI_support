from sqlmodel import Session, select, desc
from Telegram_support.database.models import TelegramUser, ChatHistory, JiraIssueStatus
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from database.engine import engine
from typing import List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


# ============= КОРИСТУВАЧІ =============

def create_user(telegram_id: int, telegram_name: str, phone: str, erp_user_token: str) -> bool:
    """Створює користувача бота підтримки"""
    try:
        with Session(engine) as session:
            # Перевіряємо чи не існує
            existing = session.exec(
                select(TelegramUser).where(
                    TelegramUser.telegram_user_id == telegram_id
                )
            ).first()

            if existing:
                logger.warning(f"User {telegram_id} already exists")
                return False

            user = TelegramUser(
                telegram_user_id=telegram_id,
                telegram_user_name=telegram_name,
                telegram_user_phone=phone,
                erp_user_token=erp_user_token
            )
            session.add(user)
            session.commit()
            logger.info(f"✅ User {telegram_id} created")
            return True
    except Exception as e:
        logger.error(f"❌ Error creating user: {e}")
        return False


def get_user_by_telegram_id(telegram_id: int) -> Optional[Tuple]:
    """
    Дістає користувача по telegram_id.
    ✅ ЗМІНЕНО: тепер повертає tuple БЕЗ jira_issue_key
    Повертає tuple: (id, telegram_id, name, phone)
    """
    try:
        with Session(engine) as session:
            statement = select(TelegramUser).where(
                TelegramUser.telegram_user_id == telegram_id
            )
            user = session.exec(statement).first()

            if user:
                return (
                    user.id,
                    user.telegram_user_id,
                    user.telegram_user_name,
                    user.telegram_user_phone,
                    user.erp_user_token
                )
            return None
    except Exception as e:
        logger.error(f"❌ Error getting user: {e}")
        return None

def update_erp_user_token(telegram_user_id: str, new_erp_user_token: str) -> bool:
    try:
        with Session(engine) as session:
            statement = select(TelegramUser).where(
                TelegramUser.telegram_user_id == telegram_user_id
            )
            telegram_user = session.exec(statement).first()

            if not telegram_user:
                logger.warning(f"Issue {telegram_user_id} not found")
                return False

            telegram_user.erp_user_token = new_erp_user_token
            session.add(telegram_user)
            session.commit()

            logger.info(f"✅ Jira issue {new_erp_user_token} updated for user with id {telegram_user_id}")
            return True

    except Exception as e:
        logger.error(f"❌ Error updating jira issue: {e}")
        return False

# ============= ІСТОРІЯ ЧАТУ =============

def save_message(user_id: int, role: str, message: str, issue_key: Optional[str] = None) -> bool:
    """
    Зберігає повідомлення в історію чату.

    Args:
        user_id: telegram_user_id користувача
        role: "user" або "assistant"
        message: текст повідомлення
        issue_key: ключ Jira issue (опціонально)
    """
    try:
        with Session(engine) as session:
            chat_message = ChatHistory(
                user_id=user_id,
                role=role,
                message=message,
                issue_key=issue_key
            )
            session.add(chat_message)
            session.commit()
            issue_info = f" for issue {issue_key}" if issue_key else ""
            logger.info(f"💾 Message saved for user {user_id}{issue_info}")
            return True
    except Exception as e:
        logger.error(f"❌ Error saving message: {e}")
        return False


def get_chat_history(user_id: int, limit: int = 10) -> List[dict]:
    """
    Дістає останні N повідомлень користувача.
    Повертає у форматі для OpenWebUI API.

    Args:
        user_id: telegram_user_id користувача
        limit: кількість останніх повідомлень

    Returns:
        List[dict]: [{"role": "user", "content": "..."}, ...]
    """
    try:
        with Session(engine) as session:
            statement = (
                select(ChatHistory)
                .where(ChatHistory.user_id == user_id)
                .order_by(desc(ChatHistory.timestamp))
                .limit(limit)
            )
            results = session.exec(statement).all()

            # Перевертаємо, бо треба від старого до нового
            messages = [
                {"role": msg.role, "content": msg.message}
                for msg in reversed(results)
            ]

            logger.info(f"📜 Retrieved {len(messages)} messages for user {user_id}")
            return messages
    except Exception as e:
        logger.error(f"❌ Error getting chat history: {e}")
        return []


def get_chat_history_by_issue(issue_key: str, limit: int = 10) -> List[dict]:
    """
    Дістає останні N повідомлень для конкретного Jira issue.
    Повертає у форматі для OpenWebUI API.

    Args:
        issue_key: ключ Jira issue (наприклад 'TP-123')
        limit: кількість останніх повідомлень

    Returns:
        List[dict]: [{"role": "user", "content": "..."}, ...]
    """
    try:
        with Session(engine) as session:
            statement = (
                select(ChatHistory)
                .where(ChatHistory.issue_key == issue_key)
                .order_by(desc(ChatHistory.timestamp))
                .limit(limit)
            )
            results = session.exec(statement).all()

            # Перевертаємо, бо треба від старого до нового
            messages = [
                {"role": msg.role, "content": msg.message}
                for msg in reversed(results)
            ]

            logger.info(f"📜 Retrieved {len(messages)} messages for issue {issue_key}")
            return messages
    except Exception as e:
        logger.error(f"❌ Error getting chat history for issue: {e}")
        return []


def clear_chat_history(user_id: int) -> bool:
    """
    Видаляє всю історію чату користувача.

    Args:
        user_id: telegram_user_id користувача
    """
    try:
        with Session(engine) as session:
            statement = select(ChatHistory).where(
                ChatHistory.user_id == user_id
            )
            results = session.exec(statement).all()

            for message in results:
                session.delete(message)

            session.commit()
            logger.info(f"🗑️ Chat history cleared for user {user_id}")
            return True
    except Exception as e:
        logger.error(f"❌ Error clearing chat history: {e}")
        return False


def get_chat_history_count(user_id: int) -> int:
    """
    Повертає кількість повідомлень користувача.
    """
    try:
        with Session(engine) as session:
            statement = select(ChatHistory).where(
                ChatHistory.user_id == user_id
            )
            results = session.exec(statement).all()
            return len(results)
    except Exception as e:
        logger.error(f"❌ Error counting messages: {e}")
        return 0


# ============= ДЖИРА ТОКЕН =============
def save_jira_issue(telegram_user_id: int, issue_key: str, service_app_name: str, group_support_name: str = 'ТехПідтримка') -> bool:
    try:
        with Session(engine) as session:
            jira_issue = JiraIssueStatus(
                telegram_user_id=telegram_user_id,
                issue_key=issue_key,
                service_app_name=service_app_name,
                group_support_name = group_support_name
            )
            session.add(jira_issue)
            session.commit()
            logger.info(f"💾 Issue {issue_key} saved for user {telegram_user_id}")
            return True
    except Exception as e:
        logger.error(f"❌ Error saving issue: {e}")
        return False

def get_jira_issue_status(jira_issue_key: str) -> str:
    """
    Отримує статус Jira issue

    Args:
        jira_issue_key: ключ issue (наприклад 'TP-17')
    """
    try:
        with Session(engine) as session:
            statement = select(JiraIssueStatus).where(
                JiraIssueStatus.issue_key == jira_issue_key
            )
            jira_issue = session.exec(statement).first()

            if not jira_issue:
                logger.warning(f"Issue {jira_issue_key} not found")
                return f'Issue {jira_issue_key} not found'

            jira_issue_status = jira_issue.category_status_issue


            return jira_issue_status

    except Exception as e:
        logger.error(f"❌ Error getting jira issue: {e}")
        return f'Error getting jira issue: {e}'


def update_jira_issue_status(jira_issue_key: str, jira_new_status: str = 'Done') -> bool:
    """
    Оновлює статус Jira issue

    Args:
        jira_issue_key: ключ issue (наприклад 'TP-17')
        jira_new_status: новий статус (за замовчуванням 'Done')
    """
    try:
        with Session(engine) as session:
            statement = select(JiraIssueStatus).where(
                JiraIssueStatus.issue_key == jira_issue_key
            )
            jira_issue = session.exec(statement).first()

            if not jira_issue:
                logger.warning(f"Issue {jira_issue_key} not found")
                return False

            jira_issue.category_status_issue = jira_new_status
            session.add(jira_issue)
            session.commit()

            logger.info(f"✅ Jira issue {jira_issue_key} updated to status {jira_new_status}")
            return True

    except Exception as e:
        logger.error(f"❌ Error updating jira issue: {e}")
        return False

def update_jira_issue_ai_work_status(jira_issue_key: str, jira_new_ai_work_status: bool = False) -> bool:
    """
    Оновлює статус Jira issue ai work status

    Args:
        jira_issue_key: ключ issue (наприклад 'TP-17')
        jira_new_ai_work_status: новий статус (за замовчуванням False)
    """
    try:
        with Session(engine) as session:
            statement = select(JiraIssueStatus).where(
                JiraIssueStatus.issue_key == jira_issue_key
            )
            jira_issue_ai_work_status = session.exec(statement).first()

            if not jira_issue_ai_work_status:
                logger.warning(f"Issue {jira_issue_key} not found")
                return False

            jira_issue_ai_work_status.ai_work_status = jira_new_ai_work_status
            session.add(jira_issue_ai_work_status)
            session.commit()

            logger.info(f"✅ Jira ai work status in jira issue ticket {jira_issue_key} updated to status {jira_new_ai_work_status}")
            return True

    except Exception as e:
        logger.error(f"❌ Error updating jira issue: {e}")
        return False

def get_jira_issue_ai_work_status(jira_issue_key: str) -> bool:
    """
    Отримує статус Jira issue ai_work_status

    Args:
        jira_issue_key: ключ issue (наприклад 'TP-17')
    """
    try:
        with Session(engine) as session:
            statement = select(JiraIssueStatus).where(
                JiraIssueStatus.issue_key == jira_issue_key
            )
            jira_issue = session.exec(statement).first()

            if not jira_issue:
                logger.warning(f"Issue {jira_issue_key} not found")
                return False

            ai_work_status = jira_issue.ai_work_status


            return ai_work_status

    except Exception as e:
        logger.error(f"❌ Error getting jira issue: {e}")
        return False


def get_active_issue_for_user(telegram_user_id: int) -> Optional[str]:
    """
    ✅ НОВА ФУНКЦІЯ: Повертає активний (не Done) issue користувача
    Якщо є кілька - повертає найновіший

    Args:
        telegram_user_id: ID користувача в Telegram

    Returns:
        str: issue_key активного issue або None якщо немає
    """
    try:
        with Session(engine) as session:
            statement = (
                select(JiraIssueStatus)
                .where(
                    JiraIssueStatus.telegram_user_id == telegram_user_id,
                    JiraIssueStatus.category_status_issue != 'Done'
                )
                .order_by(desc(JiraIssueStatus.timestamp))
                .limit(1)
            )
            jira_issue = session.exec(statement).first()

            if jira_issue:
                return jira_issue.issue_key
            return None
    except Exception as e:
        logger.error(f"❌ Error getting active issue: {e}")
        return None


def get_telegram_user_id_by_issue(issue_key: str) -> Optional[int]:
    """
    Повертає telegram_user_id по issue_key

    Args:
        issue_key: ключ Jira issue (наприклад 'TP-123')

    Returns:
        int: telegram_user_id або None якщо не знайдено
    """
    try:
        with Session(engine) as session:
            statement = select(JiraIssueStatus).where(
                JiraIssueStatus.issue_key == issue_key
            )
            jira_issue = session.exec(statement).first()

            if jira_issue:
                logger.info(f"✅ Found telegram_user_id {jira_issue.telegram_user_id} for issue {issue_key}")
                return jira_issue.telegram_user_id

            logger.warning(f"⚠️ No telegram_user_id found for issue {issue_key}")
            return None
    except Exception as e:
        logger.error(f"❌ Error getting telegram_user_id by issue: {e}")
        return None


def main():
    # print(get_jira_issue_status('SD-47982'))

    result = get_chat_history_by_issue(issue_key='SD-48056')
    print(result)
if __name__ == "__main__":
    main()