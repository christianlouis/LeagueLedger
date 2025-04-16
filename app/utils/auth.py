"""
Authentication utilities for LeagueLedger.
This module provides backward compatibility with the existing code while leveraging
the new Starlette authentication system.
"""
from typing import Optional, Dict, Any
from fastapi import Request, Depends
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import User, TeamMembership
from starlette.authentication import UnauthenticatedUser

async def get_current_user(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    """
    Get the current authenticated user from the request.
    Now uses request.user from Starlette authentication with fallback to session.
    
    Args:
        request: The FastAPI request object
        db: SQLAlchemy database session
        
    Returns:
        User object if authenticated, None otherwise
    """
    # First try to get user from Starlette authentication
    if hasattr(request, "user") and request.user.is_authenticated:
        return request.user
    
    # Fallback to session-based authentication (for backward compatibility)
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
        TeamMembership.is_captain == True  # Changed from role="captain" to is_captain=True
    ).first()
    
    return bool(is_captain)

async def is_admin(request: Request, db: Session = Depends(get_db)) -> bool:
    """
    Check if the current user is an admin.
    Now checks Starlette auth scopes first.
    
    Args:
        request: FastAPI request object
        db: SQLAlchemy database session
        
    Returns:
        True if the user is an admin, False otherwise
    """
    # Check for 'admin' scope in Starlette auth
    if hasattr(request, "auth") and request.auth and "admin" in request.auth.scopes:
        return True
    
    # Fallback to user object check
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
    
    # Check Starlette auth first
    if hasattr(request, "user") and request.user.is_authenticated:
        return request.user
        
    # Fallback to session check
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
    
    # Check for admin scope in Starlette auth
    if hasattr(request, "auth") and request.auth and "admin" in request.auth.scopes:
        if hasattr(request, "user") and request.user.is_authenticated:
            return request.user
    
    # Fallback to user object check
    user = await get_current_user(request, db)
    
    if not user or not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
        
    return user

def check_privacy_permission(
    db: Session, 
    profile_user: User, 
    viewing_user_id: Optional[int], 
    setting_name: str
) -> bool:
    """
    Check if the viewing user has permission to see a specific profile setting
    
    Args:
        db: Database session
        profile_user: The user whose profile is being viewed
        viewing_user_id: The ID of the user viewing the profile (None if not logged in)
        setting_name: The name of the setting to check (email, full_name, teams, points, achievements, events)
    
    Returns:
        True if viewer has permission to see the setting, False otherwise
    """
    # Admin users can see everything
    if viewing_user_id:
        viewing_user = db.query(User).filter(User.id == viewing_user_id).first()
        if viewing_user and viewing_user.is_admin:
            return True
    
    # Owner can see everything on their own profile
    if viewing_user_id and viewing_user_id == profile_user.id:
        return True
    
    # Get privacy settings for this user
    privacy_settings = profile_user.get_privacy_settings()
    privacy_level = privacy_settings.get(setting_name, "private")
    
    # Public settings are visible to everyone
    if privacy_level == "public":
        return True
    
    # Private settings are only visible to the user and admins (handled above)
    if privacy_level == "private":
        return False
    
    # For "friends" level (team members), check if viewing user is in same team
    if privacy_level == "friends" and viewing_user_id:
        # Get teams of the profile user
        profile_user_team_ids = [
            membership.team_id 
            for membership in db.query(TeamMembership).filter(
                TeamMembership.user_id == profile_user.id
            ).all()
        ]
        
        # Check if viewing user is in any of the same teams
        common_team = db.query(TeamMembership).filter(
            TeamMembership.user_id == viewing_user_id,
            TeamMembership.team_id.in_(profile_user_team_ids)
        ).first()
        
        return common_team is not None
    
    return False

def get_viewable_profile_data(
    db: Session, 
    profile_user: User, 
    viewing_user_id: Optional[int]
) -> Dict[str, Any]:
    """
    Get profile data respecting privacy settings
    
    Args:
        db: Database session
        profile_user: The user whose profile is being viewed
        viewing_user_id: The ID of the user viewing the profile (None if not logged in)
    
    Returns:
        Dictionary with profile data that the viewing user is allowed to see
    """
    data = {
        "username": profile_user.username,
        "picture": profile_user.picture,
        "is_admin": profile_user.is_admin,
        "created_at": profile_user.created_at
    }
    
    # Only include email if permission allows
    if check_privacy_permission(db, profile_user, viewing_user_id, "email"):
        data["email"] = profile_user.email
    
    # Only include full name if permission allows
    if check_privacy_permission(db, profile_user, viewing_user_id, "full_name"):
        data["first_name"] = profile_user.first_name
        data["last_name"] = profile_user.last_name
    
    # For teams, points, achievements, events - we'll just include permission flags
    # The actual data will be loaded by the view functions when needed
    data["can_view_teams"] = check_privacy_permission(db, profile_user, viewing_user_id, "teams")
    data["can_view_points"] = check_privacy_permission(db, profile_user, viewing_user_id, "points")
    data["can_view_achievements"] = check_privacy_permission(db, profile_user, viewing_user_id, "achievements")
    data["can_view_events"] = check_privacy_permission(db, profile_user, viewing_user_id, "events")
    
    return data

# Note: For new code, consider using the decorators in app.auth.permissions instead
# of these dependency functions directly
