from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from .db import get_db
from . import models
from .auth import get_current_user, require_login, require_admin

# Reuse functions from auth.py
# This is just for backward compatibility with any code that imported these from dependencies

# Function to get a db session
def get_session_db():
    return next(get_db())

# Function to get current authenticated user
def get_authenticated_user(request: Request):
    return get_current_user(request)

# These are kept for API backward compatibility
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

def get_current_active_user(request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

def get_current_admin_user(request: Request):
    user = get_current_user(request)
    if not user or not user.get("is_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    return user
