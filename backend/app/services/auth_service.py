"""认证服务：初始化、登录、会话校验。"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session as OrmSession

from app.core.errors import AppError, ErrorCode
from app.core.logging import get_logger
from app.core.security import hash_password, hash_token, new_session_token, verify_password
from app.models.user import Session, User
from app.repositories.user_repo import UserRepository
from app.schemas.auth import BootstrapRequest, LoginRequest, UpdateProfileRequest

logger = get_logger("auth")

SESSION_TTL = timedelta(days=1)
SESSION_TTL_REMEMBER = timedelta(days=30)
SESSION_COOKIE = "stockval_session"


class AuthService:
    def __init__(self, db: OrmSession) -> None:
        self.db = db
        self.users = UserRepository(db)

    def is_initialized(self) -> bool:
        return self.users.exists()

    def bootstrap(self, payload: BootstrapRequest) -> User:
        if self.users.exists():
            raise AppError(ErrorCode.CONFLICT, "系统已完成初始化，无法重复创建账号", 409)
        email = payload.email.strip().lower()
        if self.users.get_by_email(email) is not None:
            raise AppError(ErrorCode.CONFLICT, "该邮箱已被使用", 409)
        user = User(
            email=email,
            display_name=payload.display_name.strip() or "用户",
            password_hash=hash_password(payload.password),
            base_currency=payload.base_currency.upper(),
            role="owner",
            is_active=True,
        )
        self.users.add(user)
        self.db.commit()
        logger.info("bootstrap", user_id=user.id, email=user.email)
        return user

    def login(self, payload: LoginRequest, user_agent: str | None, ip: str | None) -> tuple[User, str, datetime]:
        user = self.users.get_by_email(payload.email.strip().lower())
        if user is None or not verify_password(payload.password, user.password_hash):
            raise AppError(ErrorCode.UNAUTHORIZED, "邮箱或密码不正确", 401)
        if not user.is_active:
            raise AppError(ErrorCode.FORBIDDEN, "账号已被停用", 403)
        token = new_session_token()
        ttl = SESSION_TTL_REMEMBER if payload.remember else SESSION_TTL
        expires_at = datetime.now(UTC) + ttl
        self.users.add_session(
            Session(
                user_id=user.id,
                token_hash=hash_token(token),
                expires_at=expires_at,
                user_agent=user_agent,
                ip=ip,
            )
        )
        self.db.commit()
        logger.info("login", user_id=user.id)
        return user, token, expires_at

    def authenticate_token(self, token: str) -> User | None:
        session = self.users.get_session_by_token_hash(hash_token(token))
        if session is None:
            return None
        now = datetime.now(UTC)
        expires = session.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=UTC)
        if session.revoked_at is not None or expires <= now:
            return None
        user = self.users.get(session.user_id)
        if user is None or not user.is_active:
            return None
        return user

    def logout(self, token: str) -> None:
        session = self.users.get_session_by_token_hash(hash_token(token))
        if session is not None:
            self.users.revoke_session(session)
            self.db.commit()

    def update_profile(self, user: User, payload: UpdateProfileRequest) -> User:
        if payload.display_name is not None:
            user.display_name = payload.display_name.strip() or user.display_name
        if payload.base_currency is not None:
            user.base_currency = payload.base_currency.upper()
        if payload.new_password:
            if not payload.current_password:
                raise AppError(ErrorCode.VALIDATION_ERROR, "修改密码需要提供当前密码", 400)
            if not verify_password(payload.current_password, user.password_hash):
                raise AppError(ErrorCode.UNAUTHORIZED, "当前密码不正确", 401)
            user.password_hash = hash_password(payload.new_password)
            self.users.revoke_all_sessions(user.id)
        self.db.commit()
        return user
