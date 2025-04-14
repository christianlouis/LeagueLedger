from fastapi import APIRouter, Request, Depends, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
import secrets
import os
import uuid
from starlette.status import HTTP_303_SEE_OTHER, HTTP_302_FOUND
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import User
from ..auth.oauth import authentik_oauth
from ..templates_config import templates

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
    # This is a placeholder - implement real login logic here
    error = "This login method is not fully implemented yet"
    return templates.TemplateResponse(
        "auth/login.html", 
        {"request": request, "error": error, "show_oauth": True, "oauth_provider_name": "Authentik"}
    )

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
