#!/usr/bin/env python3
from fastapi import APIRouter, Request, Depends, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
from sqlalchemy.orm import Session
from starlette.status import HTTP_303_SEE_OTHER, HTTP_401_UNAUTHORIZED
from datetime import datetime
import logging

# Set up logging
logger = logging.getLogger(__name__)

from ..db import get_db
from ..models import User, SystemSettings
from ..templates_config import templates
from ..security import verify_password
from ..auth.oauth import oauth_manager

# Create router
router = APIRouter(tags=["Setup"])

@router.get("/setup", response_class=HTMLResponse)
async def setup_page(request: Request, db: Session = Depends(get_db)):
    """
    Setup page that allows a logged-in user to elevate themselves to admin.
    Only available once before being deactivated.
    """
    # Check if user is logged in
    user_id = request.session.get("user_id")
    if not user_id:
        logger.warning("Unauthorized access attempt to setup page")
        # Add a query parameter for redirect back to setup after login
        return RedirectResponse("/auth/login?next=/setup", status_code=HTTP_303_SEE_OTHER)
    
    # Get the logged-in user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        logger.warning(f"User ID {user_id} found in session but not in database")
        request.session.clear()
        return RedirectResponse("/auth/login?next=/setup", status_code=HTTP_303_SEE_OTHER)
    
    # Check if setup has already been completed
    settings = db.query(SystemSettings).first()
    setup_completed = settings and settings.setup_completed
    
    # Check if the current user is already admin
    is_admin = user.is_admin
    
    return templates.TemplateResponse(
        "admin/setup.html", 
        {
            "request": request,
            "user": user,
            "setup_completed": setup_completed,
            "is_admin": is_admin
        }
    )

@router.post("/setup/elevate", response_class=JSONResponse)
async def elevate_to_admin(request: Request, db: Session = Depends(get_db)):
    """
    API endpoint to elevate current user to admin and mark setup as completed.
    Returns JSON response for AJAX handling.
    """
    # Check if user is logged in
    user_id = request.session.get("user_id")
    if not user_id:
        logger.warning("Unauthorized API call to elevate_to_admin")
        return JSONResponse(
            status_code=HTTP_401_UNAUTHORIZED,
            content={"success": False, "message": "Authentication required"}
        )
    
    # Check if setup has already been completed
    settings = db.query(SystemSettings).first()
    if settings and settings.setup_completed:
        logger.warning("Setup already completed, but elevate_to_admin was called")
        return JSONResponse(
            content={
                "success": False,
                "message": "Setup has already been completed"
            }
        )
    
    try:
        # Get the logged-in user
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            logger.warning(f"User ID {user_id} not found in database during elevate_to_admin")
            return JSONResponse(
                status_code=HTTP_401_UNAUTHORIZED,
                content={"success": False, "message": "User not found"}
            )
        
        # Elevate user to admin
        user.is_admin = True
        user.last_login = datetime.utcnow()
        
        # Mark setup as completed in system settings
        if not settings:
            settings = SystemSettings(setup_completed=True)
            db.add(settings)
        else:
            settings.setup_completed = True
        
        # Save the changes with explicit commit
        db.commit()
        logger.info(f"User {user.username} (ID: {user.id}) elevated to admin in setup")
        
        # Update the session to reflect admin status
        request.session["is_admin"] = True
        
        return JSONResponse(
            content={
                "success": True,
                "message": "You have been successfully promoted to administrator"
            }
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Error during admin elevation: {str(e)}")
        return JSONResponse(
            content={
                "success": False,
                "message": f"An error occurred: {str(e)}"
            }
        )