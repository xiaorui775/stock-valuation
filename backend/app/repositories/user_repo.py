"""用户与会话的数据访问。"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session as OrmSession

from app.models.user import Session, User


def _utcnow() -> datetime:
    return datetime.now(UTC)


class UserRepository:
    def __init__(self, db: OrmSession) -> None:
        self.db = db

    def count(self) -> int:
        return self.db.scalar(select(func.count()).select_from(User)) or 0

    def exists(self) -> bool:
        return self.db.scalar(select(User.id).limit(1)) is not None

    def get_by_email(self, email: str) -> Optional[User]:
        return self.db.scalar(select(User).where(User.email == email.lower()))

    def get(self, user_id: int) -> Optional[User]:
        return self.db.get(User, user_id)

    def add(self, user: User) -> User:
        self.db.add(user)
        self.db.flush()
        return user

    def add_session(self, session: Session) -> Session:
        self.db.add(session)
        self.db.flush()
        return session

    def get_session_by_token_hash(self, token_hash: str) -> Optional[Session]:
        return self.db.scalar(select(Session).where(Session.token_hash == token_hash))

    def revoke_session(self, session: Session) -> None:
        session.revoked_at = _utcnow()
        self.db.flush()

    def revoke_all_sessions(self, user_id: int) -> None:
        now = _utcnow()
        for s in self.db.scalars(select(Session).where(Session.user_id == user_id)):
            if s.revoked_at is None:
                s.revoked_at = now
        self.db.flush()
