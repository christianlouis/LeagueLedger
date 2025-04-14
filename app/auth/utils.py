from fastapi import Request
from sqlalchemy.orm import Session
from ..models import User
import logging

logger = logging.getLogger(__name__)

def get_current_user_from_session(request: Request, db: Session):
    """Get the current user from the session."""
    try:
        if hasattr(request.state, "user") and request.state.user is not None:
            # User is already in request state, return it
            return request.state.user
            
        if hasattr(request, "session"):
            user_id = request.session.get("user_id")
            if user_id:
                user = db.query(User).filter(User.id == user_id).first()
                if user:
                    # Set it in the request state for future use
                    request.state.user = user
                    return user
    except Exception as e:
        logger.error(f"Error retrieving user from session: {str(e)}")
    
    return None
