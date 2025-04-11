from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from sqlalchemy import inspect
from typing import Optional
from datetime import datetime

from .db import SessionLocal, engine
from .models import User
from .security import SECRET_KEY, ALGORITHM
from .templates_config import templates

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)

def get_db():
    """Database dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Check if all required user columns exist
def get_available_user_columns():
    inspector = inspect(engine)
    if 'users' in inspector.get_table_names():
        return [col['name'] for col in inspector.get_columns('users')]
    return []

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Get the current authenticated user based on the access token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # If no token, return None (not authenticated)
    if not token:
        return None
        
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
        
    # Update last login time if column exists
    columns = get_available_user_columns()
    if 'last_login' in columns and hasattr(user, 'last_login'):
        user.last_login = datetime.utcnow()
        db.commit()
    
    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)):
    """Check if the current user is active."""
    if not current_user:
        return None
    
    columns = get_available_user_columns()
    if 'is_active' in columns and hasattr(current_user, 'is_active') and not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    
    return current_user

# Improved session-based user lookup with better error handling and logging
async def get_user_from_session(request: Request):
    """Get current user from session with improved error handling"""
    try:
        if not hasattr(request, "session"):
            print("No session attribute in request")
            return None
        
        user_id = request.session.get("user_id")
        if not user_id:
            print("No user_id in session")
            return None
        
        print(f"Looking up user with ID: {user_id}")
        # Manually get a database session from get_db
        db = next(get_db())
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                print(f"User with ID {user_id} not found in database")
                # Clear invalid session data
                request.session.clear()
                return None
            return user
        finally:
            db.close()
            
    except Exception as e:
        print(f"Error getting user from session: {str(e)}")
        return None

# Template context processor to add user to all templates
async def add_user_to_templates(request: Request):
    """Add current user to all template contexts."""
    user = await get_user_from_session(request)
    return {"current_user": user}
