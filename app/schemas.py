#!/usr/bin/env python3
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, Dict, Any
from datetime import datetime

# User schemas
class UserBase(BaseModel):
    username: str
    email: EmailStr

class UserCreate(UserBase):
    password: str
    
    # Validators could be added here, like:
    @field_validator('password')
    def password_must_be_strong(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v

class UserLogin(BaseModel):
    username_or_email: str
    password: str
    remember_me: bool = False

class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None

class UserOut(BaseModel):
    id: int
    username: str
    email: EmailStr
    created_at: datetime
    is_active: bool
    is_verified: bool
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    user_id: int
    username: str

class TokenData(BaseModel):
    username: Optional[str] = None

class PasswordChange(BaseModel):
    current_password: str
    new_password: str
    confirm_password: str

class PasswordReset(BaseModel):
    token: str
    new_password: str
    confirm_password: str

# Team schemas
class TeamCreate(BaseModel):
    name: str

class TeamOut(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True
        
class TeamMembershipCreate(BaseModel):
    user_id: int
    team_id: int
    is_admin: bool = False
    
    # Validator to handle form data conversion
    @field_validator('is_admin')
    def parse_boolean(cls, v):
        if isinstance(v, str):
            return v.lower() in ('true', 'yes', 'y', '1', 'on', 'checked')
        return v
