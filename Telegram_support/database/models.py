from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime
from typing import Optional, List
from sqlalchemy import BigInteger


class TelegramUser(SQLModel, table=True):
    """Модель користувача Telegram"""
    __tablename__ = "telegram_ai_support_users"

    id: Optional[int] = Field(default=None, primary_key=True)
    telegram_user_id: int = Field(
        unique=True,
        index=True,
        sa_type=BigInteger
    )
    telegram_user_name: str = Field(max_length=255)
    telegram_user_phone: str = Field(max_length=255)

    # Зв'язок з повідомленнями (один користувач - багато повідомлень)
    messages: List["ChatHistory"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )

    jira_issues: List["JiraIssueStatus"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )


class ChatHistory(SQLModel, table=True):
    """Модель історії чату"""
    __tablename__ = "telegram_ai_support_chat_history"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(
        foreign_key="telegram_ai_support_users.telegram_user_id",
        index=True,
        sa_type=BigInteger
    )
    role: str = Field(max_length=20)  # "user" або "assistant"
    message: str
    timestamp: datetime = Field(default_factory=datetime.now)

    # Зв'язок з користувачем
    user: Optional[TelegramUser] = Relationship(back_populates="messages")


class JiraIssueStatus(SQLModel, table=True):
    """Модель статусу Jira Issue"""
    __tablename__ = "telegram_ai_support_jira_issue_status"

    id: Optional[int] = Field(default=None, primary_key=True)

    telegram_user_id: int = Field(
        foreign_key="telegram_ai_support_users.telegram_user_id",
        index=True,
        sa_type=BigInteger
    )

    issue_key: str = Field(
        max_length=255,
        unique=True,
        index=True
    )

    category_status_issue: str = Field(max_length=255, default='To Do')
    timestamp: datetime = Field(default_factory=datetime.now)

    user: Optional[TelegramUser] = Relationship(back_populates="jira_issues")