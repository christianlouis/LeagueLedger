"""
Authentication utilities for LeagueLedger.
"""
from typing import Optional
from fastapi import Request, Depends
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import User, TeamMembership

async def get_current_user(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    """
    Get the current authenticated user from the session.
    
    Args:
        request: The FastAPI request object
        db: SQLAlchemy database session
        
    Returns:
        User object if authenticated, None otherwise
    """
    user_id = request.session.get("user_id")
    
    if not user_id:
        return None
        
    # Fetch the user from the database
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        # If user doesn't exist in database but has a session, clear the session
        request.session.clear()
        return None
        
    return user

async def is_team_captain(
    team_id: int, 
    user: Optional[User] = None, 
    request: Optional[Request] = None,
    db: Session = Depends(get_db)
) -> bool:
    """
    Check if the current user is a captain of the specified team.
    
    Args:
        team_id: ID of the team to check
        user: Optional pre-loaded user object
        request: Optional FastAPI request object (used if user is not provided)
        db: SQLAlchemy database session
        
    Returns:
        True if the user is a team captain, False otherwise
    """
    if not user and request:
        user = await get_current_user(request, db)
        
    if not user:
        return False
        
    # Check if the user is a captain of the team
    is_captain = db.query(TeamMembership).filter(
        TeamMembership.team_id == team_id,
        TeamMembership.user_id == user.id,
        TeamMembership.role == "captain"
    ).first()
    
    return bool(is_captain)

async def is_admin(request: Request, db: Session = Depends(get_db)) -> bool:
    """
    Check if the current user is an admin.
    
    Args:
        request: FastAPI request object
        db: SQLAlchemy database session
        
    Returns:
        True if the user is an admin, False otherwise
    """
    user = await get_current_user(request, db)
    
    if not user:
        return False
        
    return user.is_admin

async def requires_login(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    """
    Dependency to ensure the user is logged in.
    
    Args:
        request: FastAPI request object
        db: SQLAlchemy database session
        
    Returns:
        User object if authenticated, raises HTTPException otherwise
    """
    from fastapi import HTTPException, status
    
    user = await get_current_user(request, db)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    return user

async def requires_admin(request: Request, db: Session = Depends(get_db)) -> User:
    """
    Dependency to ensure the user is an admin.
    
    Args:
        request: FastAPI request object
        db: SQLAlchemy database session
        
    Returns:
        User object if authenticated and is admin, raises HTTPException otherwise
    """
    from fastapi import HTTPException, status
    
    user = await get_current_user(request, db)
    
    if not user or not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
        
    return user
