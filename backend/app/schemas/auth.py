import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints

from app.models.enums import UserRole


class RegistrationRequest(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserProfile(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    email: EmailStr
    role: UserRole
    created_at: datetime


class ProfileUpdate(BaseModel):
    # Stripped before the length is checked, so a name of only spaces is empty.
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class AccountDeletion(BaseModel):
    """The email is typed back so nobody deletes an account by mistake."""

    email: EmailStr
