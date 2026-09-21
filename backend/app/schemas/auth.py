from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

RoleName = Literal["admin", "analyst", "viewer"]


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    full_name: str
    role_name: RoleName
    is_active: bool
    last_login_at: datetime | None
    created_at: datetime
    updated_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int
    user: UserResponse


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=12, max_length=128)

    @model_validator(mode="after")
    def passwords_must_differ(self) -> "ChangePasswordRequest":
        if self.current_password == self.new_password:
            raise ValueError("New password must differ from the current password")
        return self


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=12, max_length=128)
    role_name: RoleName


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    role_name: RoleName | None = None
    is_active: bool | None = None

    @model_validator(mode="after")
    def require_update(self) -> "UserUpdate":
        if self.full_name is None and self.role_name is None and self.is_active is None:
            raise ValueError("At least one field must be provided")
        return self


class UserListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[UserResponse]


class ApiKeyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    scopes: list[Literal["events:write"]] = Field(default_factory=lambda: ["events:write"])
    expires_at: datetime | None = None


class ApiKeyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    prefix: str
    scopes: list[str]
    is_active: bool
    expires_at: datetime | None
    created_by: uuid.UUID
    last_used_at: datetime | None
    revoked_at: datetime | None
    created_at: datetime


class ApiKeyCreatedResponse(ApiKeyResponse):
    api_key: str


class ApiKeyListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[ApiKeyResponse]


class MessageResponse(BaseModel):
    message: str
