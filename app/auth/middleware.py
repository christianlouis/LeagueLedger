from starlette.authentication import (
    AuthCredentials, AuthenticationBackend, UnauthenticatedUser
)
from sqlalchemy.orm import Session
from ..db import SessionLocal
from ..models import User

class SessionAuthBackend(AuthenticationBackend):
    """
    Authentication backend that uses session data to authenticate users.
    This maintains compatibility with the existing session-based authentication
    while providing the structure of Starlette's authentication system.
    """
    
    async def authenticate(self, request):
        """
        Authenticate the user from the session.
        
        Args:
            request: The FastAPI/Starlette request object.
            
        Returns:
            Tuple of (AuthCredentials, User) if authenticated,
            or None if not authenticated.
        """
        # Check for user_id in session
        user_id = request.session.get("user_id")
        if not user_id:
            # Return None to indicate no authentication
            return None
            
        # Get database connection
        db = SessionLocal()
        try:
            # Fetch user from database
            user = db.query(User).filter(User.id == user_id).first()
            
            # If user exists, set credentials and return user
            if user:
                # Base credentials for all authenticated users
                scopes = ["authenticated"]
                
                # Add admin scope if user is admin
                if user.is_admin:
                    scopes.append("admin")
                    
                # Add verified scope if user is verified
                if user.is_verified:
                    scopes.append("verified")
                
                # Add OAuth provider scope if it exists
                # This allows policies to be set based on authentication source
                oauth_provider = request.session.get("oauth_provider")
                if oauth_provider:
                    scopes.append(f"oauth:{oauth_provider}")
                
                # Return credentials and user
                return AuthCredentials(scopes), user
        finally:
            db.close()
        
        # If we get here, user not found but session exists
        # Clear session on next request (handled in middleware)
        return None

def on_auth_error(request, exc):
    """Handle authentication errors by redirecting to login"""
    from fastapi.responses import RedirectResponse
    
    # Build the redirect URL with the original requested path as 'next'
    login_url = f"/auth/login?next={request.url.path}"
    
    # Return redirect response
    return RedirectResponse(url=login_url, status_code=303)