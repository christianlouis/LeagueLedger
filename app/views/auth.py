from fastapi import APIRouter, Request, Depends, Form, HTTPException, status, BackgroundTasks
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
import secrets
import os
import uuid
import re
from starlette.status import HTTP_303_SEE_OTHER, HTTP_302_FOUND
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from ..db import get_db
from ..models import User
from ..auth.oauth import authentik_oauth
from ..templates_config import templates
from ..security import verify_password, get_password_hash
from ..utils.mail import send_password_reset_email

router = APIRouter(tags=["Auth"])

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: Optional[str] = None, message: Optional[str] = None, db: Session = Depends(get_db)):
    """Login page route"""
    # Check if user is already logged in
    user = None
    user_id = request.session.get("user_id")
    if user_id:
        user = db.query(User).get(user_id)
        # If user is already logged in, show a message
        if not message:
            message = "You are already logged in."
    
    return templates.TemplateResponse(
        "auth/login.html", 
        {"request": request, "error": error, "message": message, 
         "show_oauth": True, "oauth_provider_name": "Authentik",
         "user": user}  # Add user to context
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
    elif not user.is_verified and not user.is_oauth_user:
        # For unverified users, show special error message with option to resend verification
        # Pass user ID in the template to enable resending verification email
        return templates.TemplateResponse(
            "auth/login.html", 
            {
                "request": request, 
                "error": "Please verify your email address before logging in",
                "show_oauth": True, 
                "oauth_provider_name": "Authentik",
                "unverified_user_id": user.id,
                "unverified_email": user.email
            }
        )
    
    # If any error was detected, return to the login page with the error message
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
async def register_page(request: Request, error: Optional[str] = None, db: Session = Depends(get_db)):
    """Registration page route"""
    # Check if user is already logged in
    user = None
    user_id = request.session.get("user_id")
    if user_id:
        user = db.query(User).get(user_id)
        # If no specific error is set, inform user they're already registered
        if not error:
            error = "You are already registered and logged in. You can logout first if you want to create a new account."
    
    return templates.TemplateResponse(
        "auth/register.html", 
        {"request": request, "error": error, "user": user}  # Add user to context
    )

@router.post("/register", response_class=HTMLResponse)
async def register_post(
    request: Request,
    background_tasks: BackgroundTasks,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Handle registration form submission"""
    # Validate passwords match
    if password != confirm_password:
        return templates.TemplateResponse(
            "auth/register.html", 
            {"request": request, "error": "Passwords do not match"}
        )
    
    # Validate password strength
    password_validation_error = validate_password_strength(password)
    if password_validation_error:
        return templates.TemplateResponse(
            "auth/register.html",
            {"request": request, "error": password_validation_error}
        )
    
    # Check if username already exists
    if db.query(User).filter(User.username == username).first():
        return templates.TemplateResponse(
            "auth/register.html", 
            {"request": request, "error": "Username already taken"}
        )
    
    # Check if email already exists
    if db.query(User).filter(User.email == email).first():
        return templates.TemplateResponse(
            "auth/register.html", 
            {"request": request, "error": "Email already registered"}
        )
    
    try:
        # Create the user with verification token
        verification_token = secrets.token_urlsafe(32)
        expiration = datetime.utcnow() + timedelta(hours=24)
        
        new_user = User(
            username=username,
            email=email,
            hashed_password=get_password_hash(password),
            is_verified=False,
            verification_token=verification_token,
            verification_token_expires_at=expiration,
            last_verification_email_sent=datetime.utcnow()  # Add this line
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        # Send verification email
        try:
            from ..utils.mail import send_verification_email
            await send_verification_email(
                email=email,
                username=username,
                verification_token=verification_token,
                background_tasks=background_tasks
            )
        except Exception as e:
            print(f"Failed to send verification email: {str(e)}")
            # We'll show success anyway, but log the error
        
        # Return success template
        return templates.TemplateResponse(
            "auth/registration_success.html", 
            {"request": request, "email_verification_required": True}
        )
    except Exception as e:
        print(f"Registration error: {str(e)}")
        return templates.TemplateResponse(
            "auth/register.html", 
            {"request": request, "error": "An error occurred during registration"}
        )

@router.get("/verify-email", response_class=HTMLResponse)
async def verify_email(
    request: Request,
    token: str,
    db: Session = Depends(get_db)
):
    """Verify user email address with verification token"""
    # Find user by verification token
    user = db.query(User).filter(User.verification_token == token).first()
    
    # Check if token exists and hasn't expired
    if not user or not user.verification_token_expires_at or user.verification_token_expires_at < datetime.utcnow():
        return templates.TemplateResponse(
            "auth/verification_error.html",
            {"request": request, "error": "Invalid or expired verification link"}
        )
    
    # Mark user as verified and clear verification token
    user.is_verified = True
    user.verification_token = None
    user.verification_token_expires_at = None
    db.commit()
    
    # Send welcome email in the background
    try:
        from ..utils.mail import send_welcome_email
        background_tasks = BackgroundTasks()
        background_tasks.add_task(
            send_welcome_email,
            email=user.email,
            username=user.username
        )
    except Exception as e:
        print(f"Failed to queue welcome email: {str(e)}")
    
    # Redirect to login page with success message
    return templates.TemplateResponse(
        "auth/verification_success.html",
        {"request": request, "username": user.username}
    )

@router.get("/resend-verification", response_class=HTMLResponse)
async def resend_verification(
    request: Request,
    user_id: int,
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Resend verification email with cooldown period"""
    # Get the user
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        return RedirectResponse(
            "/auth/login?error=User+not+found", 
            status_code=HTTP_303_SEE_OTHER
        )
    
    # Check if user is already verified
    if user.is_verified:
        return RedirectResponse(
            "/auth/login?message=Your+account+is+already+verified.+Please+log+in.", 
            status_code=HTTP_303_SEE_OTHER
        )
    
    # Check cooldown period (1 hour)
    if user.last_verification_email_sent and (datetime.utcnow() - user.last_verification_email_sent) < timedelta(hours=1):
        # Calculate time remaining in cooldown
        time_since_last_email = datetime.utcnow() - user.last_verification_email_sent
        minutes_remaining = max(0, 60 - int(time_since_last_email.total_seconds() / 60))
        
        return RedirectResponse(
            f"/auth/login?error=Verification+email+was+recently+sent.+Please+wait+{minutes_remaining}+minutes+before+requesting+another+one.", 
            status_code=HTTP_303_SEE_OTHER
        )
    
    # Generate new verification token
    verification_token = secrets.token_urlsafe(32)
    expiration = datetime.utcnow() + timedelta(hours=24)
    
    # Update user record
    user.verification_token = verification_token
    user.verification_token_expires_at = expiration
    user.last_verification_email_sent = datetime.utcnow()
    db.commit()
    
    # Send verification email
    try:
        from ..utils.mail import send_verification_email
        await send_verification_email(
            email=user.email,
            username=user.username,
            verification_token=verification_token,
            background_tasks=background_tasks
        )
        
        return RedirectResponse(
            "/auth/login?message=Verification+email+has+been+resent.+Please+check+your+inbox.", 
            status_code=HTTP_303_SEE_OTHER
        )
    except Exception as e:
        print(f"Failed to send verification email: {str(e)}")
        return RedirectResponse(
            "/auth/login?error=Failed+to+send+verification+email.+Please+try+again+later.", 
            status_code=HTTP_303_SEE_OTHER
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
async def profile_page(request: Request, db: Session = Depends(get_db)):
    """User profile page"""
    # Get the user ID from the session
    user_id = request.session.get("user_id")
    
    if not user_id:
        return RedirectResponse("/auth/login", status_code=HTTP_303_SEE_OTHER)
    
    # Fetch the actual user data from the database
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        # If user doesn't exist in the database but has a session, clear the session
        request.session.clear()
        return RedirectResponse("/auth/login", status_code=HTTP_303_SEE_OTHER)
    
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

@router.get("/forgot-password", response_class=HTMLResponse)
async def forgot_password_page(request: Request, error: Optional[str] = None, message: Optional[str] = None):
    """Forgot password page"""
    return templates.TemplateResponse(
        "auth/forgot_password.html",
        {"request": request, "error": error, "message": message}
    )

@router.post("/forgot-password", response_class=HTMLResponse)
async def forgot_password_post(
    request: Request,
    background_tasks: BackgroundTasks,
    email: str = Form(...),
    db: Session = Depends(get_db)
):
    """Handle forgot password form submission"""
    try:
        # Find user by email
        user = db.query(User).filter(User.email == email).first()
        
        # Always show success message even if email doesn't exist (security best practice)
        if not user:
            return templates.TemplateResponse(
                "auth/forgot_password.html",
                {
                    "request": request,
                    "message": "If your email is in our system, you will receive a password reset link shortly."
                }
            )
        
        # Generate reset token
        reset_token = secrets.token_urlsafe(32)
        user.reset_token = reset_token
        user.reset_token_expires_at = datetime.utcnow() + timedelta(hours=24)
        db.commit()
        
        try:
            # Send reset email
            await send_password_reset_email(
                email=user.email,
                username=user.username,
                reset_token=reset_token,
                background_tasks=background_tasks,
            )
        except Exception as e:
            print(f"Failed to send password reset email: {str(e)}")
            # We don't show this error to the user for security reasons
            # In a production app, you would log this error properly
        
        return templates.TemplateResponse(
            "auth/forgot_password.html",
            {
                "request": request,
                "message": "If your email is in our system, you will receive a password reset link shortly."
            }
        )
    except Exception as e:
        print(f"Password reset error: {str(e)}")
        return templates.TemplateResponse(
            "auth/forgot_password.html",
            {
                "request": request,
                "error": "An error occurred. Please try again later."
            }
        )

@router.get("/reset-password", response_class=HTMLResponse)
async def reset_password_page(
    request: Request,
    token: str,
    error: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Reset password page"""
    # Validate token
    user = db.query(User).filter(User.reset_token == token).first()
    
    # Check if token exists and hasn't expired
    if not user or not user.reset_token_expires_at or user.reset_token_expires_at < datetime.utcnow():
        return templates.TemplateResponse(
            "auth/reset_password_error.html",
            {"request": request, "error": "Invalid or expired reset token."}
        )
    
    return templates.TemplateResponse(
        "auth/reset_password.html",
        {"request": request, "token": token, "error": error}
    )

@router.post("/reset-password", response_class=HTMLResponse)
async def reset_password_post(
    request: Request,
    token: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Handle reset password form submission"""
    # Validate token
    user = db.query(User).filter(User.reset_token == token).first()
    
    # Check if token exists and hasn't expired
    if not user or not user.reset_token_expires_at or user.reset_token_expires_at < datetime.utcnow():
        return templates.TemplateResponse(
            "auth/reset_password_error.html",
            {"request": request, "error": "Invalid or expired reset token."}
        )
    
    # Validate passwords
    if new_password != confirm_password:
        return templates.TemplateResponse(
            "auth/reset_password.html",
            {"request": request, "token": token, "error": "Passwords do not match."}
        )
    
    # Server-side password strength validation
    password_validation_error = validate_password_strength(new_password)
    if password_validation_error:
        return templates.TemplateResponse(
            "auth/reset_password.html",
            {"request": request, "token": token, "error": password_validation_error}
        )
    
    # Update password and clear reset token
    user.hashed_password = get_password_hash(new_password)
    user.reset_token = None
    user.reset_token_expires_at = None  # Clear the token after use
    db.commit()
    
    # Redirect to login page with success message
    return RedirectResponse(
        "/auth/login?message=Password+has+been+reset+successfully.+Please+login+with+your+new+password.",
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
