import psycopg
from contextlib import contextmanager
import logging
from configs.base_config import settings
import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_CONFIG = {
    "host": settings.DB_HOST,
    "dbname": settings.DB_NAME,
    "user": settings.DB_USER,
    "password": settings.DB_PASSWORD
}

@contextmanager
def get_db_connection():
    conn = None
    try:
        conn = psycopg.connect(**DB_CONFIG)
        yield conn
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        if conn:
            conn.rollback()
        raise e
    finally:
        if conn:
            conn.close()



def get_user_by_telegram_id(telegram_id):
    """Get product manufacturer by barcode - minimal version"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM telegram_ai_support_users WHERE telegram_user_id = %s", (telegram_id,))
                result = cur.fetchone()
                return result if result else None
    except:
        return None


def create_user(telegram_id, telegram_name, phone):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO telegram_ai_support_users (telegram_user_id, telegram_user_name, telegram_user_phone) VALUES (%s, %s, %s)", (telegram_id, telegram_name, phone))
                conn.commit()
                return True
    except:
        return False

def get_token(telegram_id):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT user_token FROM telegram_ai_support_users WHERE telegram_id = %s", (telegram_id,))
            result = cur.fetchone()
            return result[0] if result else None

def update_user_token(telegram_id, new_token):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE telegram_ai_support_users SET user_token = %s WHERE telegram_id = %s", (new_token, telegram_id))
                conn.commit()
                return True
    except:
        return False


def get_user_status(telegram_id):
    """Отримати статус користувача"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT user_status, last_report_date FROM telegram_ai_support_users WHERE telegram_id = %s", (telegram_id,))
                result = cur.fetchone()
                return result if result else ('no_reports', None)
    except:
        return ('no_reports', None)

def update_user_status(telegram_id, status, report_date=None):
    """Оновити статус користувача"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                if report_date:
                    cur.execute("UPDATE telegram_ai_support_users SET user_status = %s, last_report_date = %s WHERE telegram_id = %s",
                               (status, report_date, telegram_id))
                else:
                    cur.execute("UPDATE telegram_ai_support_users SET user_status = %s WHERE telegram_id = %s",
                               (status, telegram_id))
                conn.commit()
                return True
    except Exception as e:
        logger.error(f"Error updating user status: {e}")
        return False

def update_user_status(telegram_id, status, report_date=None):
    """Оновити статус користувача"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                if report_date:
                    cur.execute("UPDATE telegram_ai_support_users SET user_status = %s, last_report_date = %s WHERE telegram_id = %s",
                               (status, report_date, telegram_id))
                else:
                    cur.execute("UPDATE telegram_ai_support_users SET user_status = %s WHERE telegram_id = %s",
                               (status, telegram_id))
                conn.commit()
                return True
    except Exception as e:
        logger.error(f"Error updating user status: {e}")
        return False


def get_users_with_unfinished_reports():
    """Отримати telegram_id користувачів зі статусом morning_done і звітом за сьогодні"""
    try:
        today = datetime.date.today()  # сьогоднішня дата
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                query = """
                    SELECT telegram_id 
                    FROM telegram_ai_support_users 
                    WHERE user_status = %s AND last_report_date = %s
                """
                cur.execute(query, ("morning_done", today))
                results = cur.fetchall()
                return results if results else []
    except Exception as e:
        print("Помилка при отриманні користувачів:", e)
        return []


def get_users_with_unstarted_reports():
    try:
        today = datetime.date.today()
        week_day = today.weekday()
        if week_day == 0:
            previous_day = today - datetime.timedelta(days=3)
        elif week_day in [1, 2, 3, 4]:
            previous_day = today - datetime.timedelta(days=1)
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                query = """
                    SELECT telegram_id 
                    FROM telegram_ai_support_users 
                    WHERE (user_status = %s OR user_status = %s) AND last_report_date = %s
                """
                cur.execute(query, ("morning_done", 'day_completed', previous_day))
                results = cur.fetchall()
                return results if results else []
    except Exception as e:
        print("Помилка при отриманні користувачів:", e)
        return []

def main():
    token_user = get_token(324015551)
    print(token_user)

    # product = get_user_by_telegram_id('4823071659115')
    # print(product)

if __name__ == '__main__':
    main()