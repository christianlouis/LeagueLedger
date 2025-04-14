from fastapi import APIRouter, Request, Depends, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
import secrets
import os
import uuid
import re
from starlette.status import HTTP_303_SEE_OTHER, HTTP_302_FOUND
from sqlalchemy.orm import Session
from datetime import datetime

from ..db import get_db
from ..models import User
from ..auth.oauth import authentik_oauth
from ..templates_config import templates
from ..security import verify_password, get_password_hash

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: Optional[str] = None, message: Optional[str] = None):
    """Login page route"""
    return templates.TemplateResponse(
        "auth/login.html", 
        {"request": request, "error": error, "message": message, 
         "show_oauth": True, "oauth_provider_name": "Authentik"}
    )

@router.post("/login", response_class=HTMLResponse)
async def login_post(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    remember: Optional[bool] = Form(False),
    db: Session = Depends(get_db)
):
    """Handle login form submission"""
    error = None
    
    # Look up the user by username or email
    user = db.query(User).filter(
        (User.username == username) | (User.email == username)
    ).first()
    
    # Check if user exists and password is correct
    if not user:
        error = "Invalid username or email"
    elif user.is_oauth_user and not user.hashed_password:
        error = "This account uses OAuth for login. Please use the OAuth login option."
    elif not verify_password(password, user.hashed_password):
        error = "Invalid password"
    elif not user.is_active:
        error = "This account has been deactivated"
    
    # If there was an error, re-render the login page
    if error:
        return templates.TemplateResponse(
            "auth/login.html", 
            {
                "request": request, 
                "error": error, 
                "show_oauth": True, 
                "oauth_provider_name": "Authentik"
            }
        )
    
    # Update the last login timestamp
    user.last_login = datetime.utcnow()
    db.commit()
    
    # Set session data
    request.session["user_id"] = user.id
    request.session["username"] = user.username
    request.session["is_authenticated"] = True
    request.session["is_admin"] = user.is_admin
    
    # If remember me is checked, set session expiry to a longer time (30 days)
    if remember:
        # Session middleware handles this through cookies, so we just need to set the flag
        request.session["remember_me"] = True
    
    # Redirect to dashboard or previously requested page
    next_page = request.query_params.get("next", "/dashboard")
    return RedirectResponse(next_page, status_code=HTTP_303_SEE_OTHER)

@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request, error: Optional[str] = None):
    """Registration page route"""
    return templates.TemplateResponse(
        "auth/register.html", 
        {"request": request, "error": error}
    )

@router.post("/register", response_class=HTMLResponse)
async def register_post(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Handle registration form submission"""
    # This is a placeholder - implement real registration logic here
    if password != confirm_password:
        return templates.TemplateResponse(
            "auth/register.html", 
            {"request": request, "error": "Passwords do not match"}
        )

    # Check username and email uniqueness, then create user
    return templates.TemplateResponse(
        "auth/registration_success.html", 
        {"request": request}
    )

@router.get("/oauth-login")
async def oauth_login(request: Request):
    """Start the OAuth login flow"""
    # Generate the redirect URI
    base_url = str(request.base_url)
    redirect_uri = f"{base_url}auth/oauth-callback"
    
    # Request a login URL from the Authentik provider
    try:
        # Set a session ID to validate the callback
        if "session_id" not in request.session:
            request.session["session_id"] = str(uuid.uuid4())
            
        # Get the authorization URL - make sure to await it
        auth_url = await authentik_oauth.get_login_url(request, redirect_uri)
        
        # Redirect to the authorization URL
        return RedirectResponse(auth_url)
    except Exception as e:
        print(f"OAuth login error: {str(e)}")
        return RedirectResponse(
            f"/auth/login?error=OAuth+login+failed:+{str(e)}",
            status_code=HTTP_303_SEE_OTHER
        )

@router.get("/oauth-callback")
async def oauth_callback(request: Request, code: Optional[str] = None, state: Optional[str] = None, error: Optional[str] = None, db: Session = Depends(get_db)):
    """Handle the OAuth callback"""
    if error:
        return RedirectResponse(
            f"/auth/login?error=OAuth+login+failed:+{error}",
            status_code=HTTP_303_SEE_OTHER
        )
    
    if not code:
        return RedirectResponse(
            "/auth/login?error=No+authorization+code+received", 
            status_code=HTTP_303_SEE_OTHER
        )
    
    # Generate the redirect URI that matches the one used in the initial request
    base_url = str(request.base_url)
    redirect_uri = f"{base_url}auth/oauth-callback"
    
    try:
        # Get user info from the provider
        user_info = await authentik_oauth.get_user_info(request, redirect_uri, code)
        
        if not user_info:
            return RedirectResponse(
                "/auth/login?error=Could+not+retrieve+user+information", 
                status_code=HTTP_303_SEE_OTHER
            )
        
        # Extract user details from OAuth info
        sub = user_info.get("sub", "")
        email = user_info.get("email", "")
        name = user_info.get("preferred_username", "") or user_info.get("name", "") or email.split("@")[0]
        picture = user_info.get("picture", None)
        
        # Check if the user already exists
        user = db.query(User).filter(User.email == email).first()
        
        if not user:
            print(f"Creating new user with email {email} and username {name}")
            # Create a new user
            user = User(
                username=name,
                email=email,
                oauth_id=sub,
                is_oauth_user=True,
                oauth_provider="authentik",
                picture=picture,
                is_verified=True  # OAuth users are considered verified
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        else:
            # Update existing user's OAuth information
            if not user.is_oauth_user:
                user.is_oauth_user = True
                user.oauth_id = sub
                user.oauth_provider = "authentik"
                
            # Update profile picture if available
            if picture and not user.picture:
                user.picture = picture
                
            db.commit()
        
        # Set session data
        request.session["user_id"] = user.id
        request.session["username"] = user.username
        request.session["is_authenticated"] = True
        request.session["is_admin"] = user.is_admin
        
        return RedirectResponse("/dashboard", status_code=HTTP_303_SEE_OTHER)
        
    except Exception as e:
        print(f"OAuth callback error: {str(e)}")
        return RedirectResponse(
            f"/auth/login?error=OAuth+login+failed:+{str(e)}", 
            status_code=HTTP_303_SEE_OTHER
        )

@router.get("/logout")
async def logout(request: Request):
    """Log out the user"""
    request.session.clear()
    return RedirectResponse("/", status_code=HTTP_303_SEE_OTHER)

@router.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request):
    """User profile page"""
    # Get the user ID from the session
    user_id = request.session.get("user_id")
    
    if not user_id:
        return RedirectResponse("/auth/login", status_code=HTTP_303_SEE_OTHER)
    
    # Mock user data - in a real app, you'd fetch this from the database
    user = {
        "id": user_id,
        "username": request.session.get("username", "User"),
        "email": "user@example.com",
        "is_admin": request.session.get("is_admin", False),
        "created_at": "2023-01-01 12:00:00",
        "picture": None
    }
    
    return templates.TemplateResponse(
        "auth/profile.html", 
        {"request": request, "user": user}
    )

@router.get("/change-password", response_class=HTMLResponse)
async def change_password_page(request: Request, error: Optional[str] = None, message: Optional[str] = None):
    """Change password page"""
    # Check if user is logged in
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/auth/login?next=/auth/change-password", status_code=HTTP_303_SEE_OTHER)
    
    return templates.TemplateResponse(
        "auth/change_password.html", 
        {"request": request, "error": error, "message": message}
    )

@router.post("/change-password", response_class=HTMLResponse)
async def change_password_post(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Handle change password form submission"""
    # Check if user is logged in
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/auth/login", status_code=HTTP_303_SEE_OTHER)
    
    # Validate form data
    if new_password != confirm_password:
        return templates.TemplateResponse(
            "auth/change_password.html",
            {"request": request, "error": "New passwords do not match"}
        )
    
    # Get user from database
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        request.session.clear()
        return RedirectResponse("/auth/login", status_code=HTTP_303_SEE_OTHER)
    
    # Check if this is an OAuth user without a password
    if user.is_oauth_user and not user.hashed_password:
        return templates.TemplateResponse(
            "auth/change_password.html",
            {"request": request, "error": "OAuth users cannot change passwords this way"}
        )
    
    # Verify current password
    if not verify_password(current_password, user.hashed_password):
        return templates.TemplateResponse(
            "auth/change_password.html",
            {"request": request, "error": "Current password is incorrect"}
        )
    
    # Check if new password is the same as current password
    if current_password == new_password:
        return templates.TemplateResponse(
            "auth/change_password.html",
            {"request": request, "error": "New password must be different from your current password"}
        )
    
    # Server-side password strength validation
    password_validation_error = validate_password_strength(new_password)
    if password_validation_error:
        return templates.TemplateResponse(
            "auth/change_password.html",
            {"request": request, "error": password_validation_error}
        )
    
    # Update password
    user.hashed_password = get_password_hash(new_password)
    db.commit()
    
    # Redirect to profile page with success message
    return RedirectResponse(
        "/auth/profile?message=Password+changed+successfully",
        status_code=HTTP_303_SEE_OTHER
    )

def validate_password_strength(password: str) -> Optional[str]:
    """
    Validates password strength based on the following criteria:
    - At least 8 characters long
    - Contains at least one lowercase letter
    - Contains at least one uppercase letter
    - Contains at least one digit
    - Contains at least one special character
    
    Returns error message if validation fails, None if password is valid
    """
    if len(password) < 8:
        return "Password must be at least 8 characters long"
    
    if not re.search(r"[a-z]", password):
        return "Password must contain at least one lowercase letter"
    
    if not re.search(r"[A-Z]", password):
        return "Password must contain at least one uppercase letter"
    
    if not re.search(r"\d", password):
        return "Password must contain at least one number"
    
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return "Password must contain at least one special character"
    
    return None
