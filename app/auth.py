#!/usr/bin/env python3
"""
Authentication system using Authlib and session-based auth
"""
import os
import inspect
import hashlib
from functools import wraps

from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Request, status, Depends, HTTPException
from starlette.responses import RedirectResponse
from sqlalchemy.orm import Session
from passlib.context import CryptContext

from .db import SessionLocal
from .templates_config import templates
from . import models
from .dependencies import get_user_from_session

# Initialize OAuth
oauth = OAuth()

# Check if OAuth is configured via environment variables
OAUTH_CONFIGURED = bool(os.environ.get("OAUTH_CLIENT_ID") and os.environ.get("OAUTH_CLIENT_SECRET"))
OAUTH_PROVIDER_NAME = os.environ.get("OAUTH_PROVIDER_NAME", "Single Sign-On")

# Configure OAuth provider if credentials are provided
if OAUTH_CONFIGURED:
    oauth.register(
        name="oauth_provider",
        client_id=os.environ.get("OAUTH_CLIENT_ID"),
        client_secret=os.environ.get("OAUTH_CLIENT_SECRET"),
        server_metadata_url=os.environ.get("OAUTH_CONFIG_URL"),
        client_kwargs={"scope": "openid profile email"},
    )

# Create router and password context
router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_password_hash(password):
    """Generate password hash"""
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    """Verify password against hash"""
    return pwd_context.verify(plain_password, hashed_password)

def get_current_user(request: Request, db: Session = Depends(get_db)):
    """Get current user from session"""
    return get_user_from_session(request, db)

def get_gravatar_url(email):
    """Generate a Gravatar URL for the given email"""
    email = email.lower().strip()
    email_hash = hashlib.md5(email.encode('utf-8')).hexdigest()
    return f"https://www.gravatar.com/avatar/{email_hash}?d=identicon"

def require_login(func):
    """Decorator to require login for routes"""
    @wraps(func)
    async def wrapper(request: Request, *args, **kwargs):
        try:
            db = next(get_db())
            user = get_user_from_session(request, db)
            
            if not user:
                # Store the current URL for redirecting after login
                request.session["redirect_after_login"] = str(request.url)
                return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)
            
            # Check if the wrapped function is a coroutine function
            if inspect.iscoroutinefunction(func):
                return await func(request, *args, **kwargs)
            else:
                return func(request, *args, **kwargs)
        except Exception as e:
            print(f"Error in require_login decorator: {str(e)}")
            return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)

    return wrapper

def require_admin(func):
    """Decorator to require admin access for routes"""
    @wraps(func)
    async def wrapper(request: Request, *args, **kwargs):
        try:
            db = next(get_db())
            user = get_user_from_session(request, db)
            
            if not user:
                request.session["redirect_after_login"] = str(request.url)
                return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)
            
            if not user.is_admin:
                return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
            
            # Check if the wrapped function is a coroutine function
            if inspect.iscoroutinefunction(func):
                return await func(request, *args, **kwargs)
            else:
                return func(request, *args, **kwargs)
        except Exception as e:
            print(f"Error in require_admin decorator: {str(e)}")
            return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)

    return wrapper

# Routes for authentication

@router.get("/login")
async def login_page(request: Request, db: Session = Depends(get_db)):
    """Show login page with appropriate authentication options"""
    # If already logged in, redirect to home
    if get_user_from_session(request, db):
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    
    return templates.TemplateResponse(
        "auth/login.html", 
        {
            "request": request,
            "error": request.query_params.get("error"),
            "message": request.query_params.get("message"),
            "show_oauth": OAUTH_CONFIGURED,
            "oauth_provider_name": OAUTH_PROVIDER_NAME
        }
    )

@router.post("/login")
async def login(request: Request, db: Session = Depends(get_db)):
    """Handle username/password authentication"""
    form_data = await request.form()
    username = form_data.get("username")
    password = form_data.get("password")
    
    # Check if username exists
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user or not verify_password(password, user.hashed_password):
        return RedirectResponse(
            url="/auth/login?error=Invalid+username+or+password", 
            status_code=status.HTTP_302_FOUND
        )
    
    # Make sure we use the actual is_admin field from the User model
    is_admin_value = False
    if hasattr(user, "is_admin") and user.is_admin is not None:
        is_admin_value = user.is_admin
    
    # Store user info in session - STANDARDIZED APPROACH
    # Store both the user_id (for new code) and the full user dict (for backward compatibility)
    request.session["user_id"] = user.id
    
    # Also store the legacy format for backward compatibility
    request.session["user"] = {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "is_admin": is_admin_value,
        "picture": get_gravatar_url(user.email),
        "_permanent": True,
        "created_at": str(user.created_at)
    }
    
    # Log the successful authentication
    print(f"User authenticated: {username}, is_admin: {is_admin_value}")
    
    # Redirect to original destination or default
    redirect_url = request.session.pop("redirect_after_login", "/")
    return RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)

@router.get("/oauth-login")
async def oauth_login(request: Request):
    """Handle OAuth login flow"""
    if not OAUTH_CONFIGURED:
        return RedirectResponse(
            url="/auth/login?error=OAuth+not+configured",
            status_code=status.HTTP_302_FOUND
        )
    
    redirect_uri = request.url_for("oauth_callback")
    return await oauth.oauth_provider.authorize_redirect(request, redirect_uri)

@router.get("/oauth-callback")
async def oauth_callback(request: Request, db: Session = Depends(get_db)):
    """Handle OAuth callback from provider"""
    try:
        token = await oauth.oauth_provider.authorize_access_token(request)
        userinfo = token.get("userinfo")
        if not userinfo:
            return RedirectResponse(
                url="/auth/login?error=Failed+to+retrieve+user+information",
                status_code=status.HTTP_302_FOUND
            )
            
        # Get or create user in database
        email = userinfo.get("email")
        if not email:
            return RedirectResponse(
                url="/auth/login?error=Email+not+provided+by+OAuth+provider",
                status_code=status.HTTP_302_FOUND
            )
        
        # Find user by email or create a new one
        user = db.query(models.User).filter(models.User.email == email).first()
        if not user:
            # Create new user with OAuth data
            username = userinfo.get("preferred_username") or email.split("@")[0]
            user = models.User(
                username=username,
                email=email,
                hashed_password=get_password_hash(os.urandom(24).hex()),  # Random password
                is_active=True,  # Set user as active
                is_admin=False   # Default to non-admin
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        
        # Determine if user is admin
        is_admin_value = False
        if hasattr(user, "is_admin") and user.is_admin is not None:
            is_admin_value = user.is_admin
        
        # Store user ID in session (new standardized approach)
        request.session["user_id"] = user.id
        
        # Also store legacy user data format
        user_data = {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "is_active": getattr(user, "is_active", True),
            "is_admin": is_admin_value,
            "_permanent": True,
            "created_at": str(getattr(user, "created_at", "")),
        }
        
        # Add picture from OAuth or Gravatar
        if userinfo.get("picture"):
            user_data["picture"] = userinfo.get("picture")
        elif email:
            user_data["picture"] = get_gravatar_url(email)
        
        request.session["user"] = user_data
        
        # Log the successful authentication
        print(f"User authenticated via OAuth: {email}, is_admin: {is_admin_value}")
        
        # Redirect to original destination or default
        redirect_url = request.session.pop("redirect_after_login", "/")
        return RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        print(f"OAuth authentication error: {str(e)}")
        return RedirectResponse(
            url=f"/auth/login?error=Authentication+failed:+{str(e)}",
            status_code=status.HTTP_302_FOUND
        )

@router.get("/logout")
async def logout(request: Request):
    """Handle user logout"""
    request.session.pop("user", None)
    request.session.pop("user_id", None)
    return RedirectResponse(
        url="/auth/login?message=You+have+been+logged+out+successfully", 
        status_code=status.HTTP_302_FOUND
    )

@router.get("/profile")
@require_login
async def profile_page(request: Request, db: Session = Depends(get_db)):
    """Show user profile page"""
    user = get_user_from_session(request, db)
    return templates.TemplateResponse("auth/profile.html", {"request": request, "user": user})

@router.get("/register")
async def register_page(request: Request):
    """Show registration page"""
    return templates.TemplateResponse("auth/register.html", {"request": request})

@router.post("/register")
async def register(request: Request, db: Session = Depends(get_db)):
    """Handle user registration"""
    form_data = await request.form()
    username = form_data.get("username")
    email = form_data.get("email")
    password = form_data.get("password")
    confirm_password = form_data.get("confirm_password")
    
    # Validate input
    if not username or not email or not password:
        return RedirectResponse(
            url="/auth/register?error=All+fields+are+required", 
            status_code=status.HTTP_302_FOUND
        )
    
    if password != confirm_password:
        return RedirectResponse(
            url="/auth/register?error=Passwords+do+not+match", 
            status_code=status.HTTP_302_FOUND
        )
    
    # Check if username or email already exists
    if db.query(models.User).filter(models.User.username == username).first():
        return RedirectResponse(
            url="/auth/register?error=Username+already+taken", 
            status_code=status.HTTP_302_FOUND
        )
    
    if db.query(models.User).filter(models.User.email == email).first():
        return RedirectResponse(
            url="/auth/register?error=Email+already+registered", 
            status_code=status.HTTP_302_FOUND
        )
    
    # Create new user with the appropriate fields
    user = models.User(
        username=username,
        email=email,
        hashed_password=get_password_hash(password),
        is_active=True,
        is_admin=False  # Explicitly set is_admin to False for new registrations
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Log the user in immediately after registration
    request.session["user_id"] = user.id
    request.session["user"] = {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "is_admin": False,
        "picture": get_gravatar_url(user.email),
        "_permanent": True,
        "created_at": str(getattr(user, "created_at", ""))
    }
    
    # Redirect to registration success page
    return RedirectResponse(
        url="/auth/registration-success", 
        status_code=status.HTTP_303_SEE_OTHER
    )

@router.get("/registration-success")
async def registration_success(request: Request):
    """Show registration success page"""
    return templates.TemplateResponse(
        "auth/registration_success.html", 
        {"request": request}
    )

@router.get("/api/whoami")
async def whoami(request: Request, db: Session = Depends(get_db)):
    """API endpoint to get current user information"""
    user = get_user_from_session(request, db)
    if not user:
        return {"error": "Not authenticated"}
    
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "is_admin": user.is_admin if hasattr(user, "is_admin") else False
    }
