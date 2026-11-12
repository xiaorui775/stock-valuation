"""认证相关请求/响应模型。"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class BootstrapRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(default="用户", max_length=120)
    base_currency: str = Field(default="CNY", min_length=3, max_length=3)


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=128)
    remember: bool = False


class UpdateProfileRequest(BaseModel):
    display_name: str | None = Field(default=None, max_length=120)
    base_currency: str | None = Field(default=None, min_length=3, max_length=3)
    current_password: str | None = Field(default=None, max_length=128)
    new_password: str | None = Field(default=None, min_length=8, max_length=128)


class UserOut(BaseModel):
    id: int
    email: str
    display_name: str
    base_currency: str
    role: str
    created_at: datetime

    model_config = {"from_attributes": True}
