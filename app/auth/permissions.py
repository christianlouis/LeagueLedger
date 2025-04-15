from functools import wraps
from typing import List, Optional, Callable, Union
from starlette.authentication import requires
from fastapi import Request, HTTPException, status
from fastapi.responses import RedirectResponse

def require_auth(redirect_url: Optional[str] = None):
    """
    Decorator to require authentication for FastAPI route handlers.
    This uses Starlette's requires decorator with the "authenticated" scope.
    
    Args:
        redirect_url: URL to redirect to if user is not authenticated (optional).
                     If not provided, returns a 401 Unauthorized error.
                     
    Example:
        @router.get("/protected")
        @require_auth(redirect_url="/auth/login")
        async def protected_route(request: Request):
            return {"user": request.user.display_name}
    """
    return requires(
        "authenticated", 
        status_code=status.HTTP_401_UNAUTHORIZED,
        redirect=redirect_url
    )

def require_admin(redirect_url: Optional[str] = None):
    """
    Decorator to require admin privileges for FastAPI route handlers.
    This uses Starlette's requires decorator with the "admin" scope.
    
    Args:
        redirect_url: URL to redirect to if user is not an admin (optional).
                     If not provided, returns a 403 Forbidden error.
                     
    Example:
        @router.get("/admin-only")
        @require_admin(redirect_url="/auth/login")
        async def admin_only_route(request: Request):
            return {"message": "You are an admin"}
    """
    return requires(
        "admin", 
        status_code=status.HTTP_403_FORBIDDEN,
        redirect=redirect_url
    )

def require_verified(redirect_url: Optional[str] = None):
    """
    Decorator to require verified users for FastAPI route handlers.
    This uses Starlette's requires decorator with the "verified" scope.
    
    Args:
        redirect_url: URL to redirect to if user is not verified (optional).
                     If not provided, returns a 403 Forbidden error.
                     
    Example:
        @router.get("/verified-only")
        @require_verified(redirect_url="/auth/verify-email")
        async def verified_only_route(request: Request):
            return {"message": "Your email is verified"}
    """
    return requires(
        "verified", 
        status_code=status.HTTP_403_FORBIDDEN,
        redirect=redirect_url
    )

def require_team_captain(team_id_param: str = "team_id"):
    """
    Decorator to require team captain privileges for a specific team.
    This decorator doesn't use Starlette's requires as it needs access to
    path parameters and the database to check team captain status.
    
    Args:
        team_id_param: Name of the path parameter that contains the team ID.
                      
    Example:
        @router.get("/teams/{team_id}/manage")
        @require_team_captain()
        async def manage_team(request: Request, team_id: int):
            return {"message": f"You are the captain of team {team_id}"}
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = kwargs.get("request") or next(
                (arg for arg in args if isinstance(arg, Request)), None
            )
            
            if not request:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Request object not found in endpoint arguments"
                )
                
            # Check if user is authenticated
            if not request.user.is_authenticated:
                return RedirectResponse(
                    url=f"/auth/login?next={request.url.path}", 
                    status_code=status.HTTP_303_SEE_OTHER
                )
                
            # Get team_id from path parameters
            team_id = kwargs.get(team_id_param)
            if not team_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Team ID parameter '{team_id_param}' not found"
                )
                
            # Get database session
            from sqlalchemy.orm import Session
            from ..db import SessionLocal
            from ..models import TeamMembership
            
            db = SessionLocal()
            try:
                # Check if user is team captain
                membership = db.query(TeamMembership).filter(
                    TeamMembership.team_id == team_id,
                    TeamMembership.user_id == int(request.user.identity),
                    TeamMembership.is_captain == True
                ).first()
                
                if not membership:
                    return RedirectResponse(
                        url=f"/teams/{team_id}", 
                        status_code=status.HTTP_303_SEE_OTHER
                    )
            finally:
                db.close()
                
            return await func(*args, **kwargs)
        return wrapper
    return decorator