from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, EmailStr, Field


class UserStatus(str, Enum):
    INVITED = "invited"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DISABLED = "disabled"
    DELETED = "deleted"


class UserCreate(BaseModel):
    email: EmailStr
    password_hash: Optional[str] = Field(default=None, description="Only for password auth")
    full_name: Optional[str] = None
    status: UserStatus = UserStatus.INVITED
    role: str = "member"

    auth_provider: Optional[str] = None
    provider_id: Optional[str] = None

    phone: Optional[str] = None

    metadata: dict[str, Any] = Field(default_factory=dict)


class UserSchema(BaseModel):
    id: str = Field(..., description="User ID (UUID or ObjectId string)")
    email: EmailStr
    password_hash: Optional[str] = Field(default=None, description="Only for password auth")
    full_name: Optional[str] = None
    status: UserStatus = UserStatus.INVITED
    role: str = "member"

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_login_at: Optional[datetime] = None
    email_verified_at: Optional[datetime] = None

    auth_provider: Optional[str] = None
    provider_id: Optional[str] = None

    phone: Optional[str] = None

    deleted_at: Optional[datetime] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=3)

class UserSignup(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    password: str = Field(min_length=3)


class UserAlreadyExistsError(Exception):
    def __init__(self, email: str) -> None:
        super().__init__(f"User with email '{email}' already exists.")
        self.email = email
