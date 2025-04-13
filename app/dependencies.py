from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from .db import get_db
from . import models

# OAuth2 configuration for API-based authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

# Function to get user from session
def get_user_from_session(request: Request, db: Session = Depends(get_db)):
    """
    Get the current user from session.
    This is the SINGLE source of truth for session-based auth.
    """
    try:
        # First check if request has session attribute and it's a dictionary
        if not hasattr(request, "session"):
            print("No session object found in request")
            return None
            
        # Make sure session is a dictionary before trying to access it
        if not isinstance(request.session, dict):
            print(f"Session is not a dictionary: {type(request.session)}")
            return None
            
        # Standard method - get user_id from session
        user_id = request.session.get("user_id")
        if user_id:
            return db.query(models.User).filter(models.User.id == user_id).first()
            
        # Legacy method - get user from session.user
        user_dict = request.session.get("user")
        if user_dict and isinstance(user_dict, dict) and "id" in user_dict:
            return db.query(models.User).filter(models.User.id == user_dict["id"]).first()
            
        return None
    except Exception as e:
        print(f"Error getting user from session: {str(e)}")
        return None

# Function to get current authenticated user
def get_current_user(request: Request, db: Session = Depends(get_db)):
    """Get current authenticated user from session"""
    return get_user_from_session(request, db)

def get_current_active_user(request: Request, db: Session = Depends(get_db)):
    """Get current user and ensure they're authenticated"""
    user = get_user_from_session(request, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

def get_current_admin_user(request: Request, db: Session = Depends(get_db)):
    """Get current user and ensure they're an admin"""
    user = get_user_from_session(request, db)
    if not user or not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    return user

# Keep for backward compatibility
def get_session_db():
    """Legacy function to get DB session directly"""
    return next(get_db())

def get_authenticated_user(request: Request, db: Session = Depends(get_db)):
    """Legacy function for getting the current user"""
    return get_user_from_session(request, db)
