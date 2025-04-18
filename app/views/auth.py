from fastapi import APIRouter, Request, Depends, Form, HTTPException, status, BackgroundTasks, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from typing import Optional, List, Dict, Any
import secrets
import os
import uuid
import re
import shutil
from pathlib import Path
from starlette.status import HTTP_303_SEE_OTHER, HTTP_302_FOUND
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from ..db import get_db
from ..models import User
from ..auth.oauth import oauth_manager
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
    
    # Get available OAuth providers for the login screen
    oauth_providers = oauth_manager.get_available_providers()
    
    return templates.TemplateResponse(
        "auth/login.html", 
        {
            "request": request, 
            "error": error, 
            "message": message,
            "user": user,
            "oauth_providers": oauth_providers
        }
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
                "oauth_providers": oauth_manager.get_available_providers(),
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
                "oauth_providers": oauth_manager.get_available_providers()
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
    background_tasks: BackgroundTasks,
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
        await send_welcome_email(
            email_to=user.email,
            username=user.username,
            background_tasks=background_tasks
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

@router.get("/oauth-login/{provider_id}")
async def oauth_login(request: Request, provider_id: str):
    """Start the OAuth login flow for the specified provider"""
    # Generate the redirect URI
    base_url = str(request.base_url)
    redirect_uri = f"{base_url}auth/oauth-callback/{provider_id}"
    
    # Request a login URL from the provider
    try:
        # Set a session ID to validate the callback
        if "session_id" not in request.session:
            request.session["session_id"] = str(uuid.uuid4())
            
        # Get the authorization URL
        auth_url = await oauth_manager.get_login_url(request, provider_id, redirect_uri)
        
        # Redirect to the authorization URL
        return RedirectResponse(auth_url)
    except Exception as e:
        print(f"OAuth login error: {str(e)}")
        return RedirectResponse(
            f"/auth/login?error=OAuth+login+failed:+{str(e)}",
            status_code=HTTP_303_SEE_OTHER
        )

@router.get("/oauth-callback/{provider_id}")
async def oauth_callback(
    request: Request, 
    provider_id: str,
    code: Optional[str] = None, 
    state: Optional[str] = None, 
    error: Optional[str] = None, 
    db: Session = Depends(get_db)
):
    """Handle the OAuth callback for the specified provider"""
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
    redirect_uri = f"{base_url}auth/oauth-callback/{provider_id}"
    
    try:
        # Get normalized user info from the provider
        user_info = await oauth_manager.get_user_info(request, provider_id, redirect_uri, code)
        
        if not user_info:
            return RedirectResponse(
                "/auth/login?error=Could+not+retrieve+user+information", 
                status_code=HTTP_303_SEE_OTHER
            )
        
        # Extract user details from the normalized OAuth info
        provider_user_id = user_info.get("id")
        email = user_info.get("email")
        name = user_info.get("name") or (email.split("@")[0] if email else f"user_{provider_id}")
        first_name = user_info.get("first_name")
        last_name = user_info.get("last_name")
        picture = user_info.get("picture")
        
        if not email:
            return RedirectResponse(
                "/auth/login?error=Email+address+not+provided+by+the+OAuth+provider", 
                status_code=HTTP_303_SEE_OTHER
            )
        
        # Check if the user already exists with this email
        user = db.query(User).filter(User.email == email).first()
        
        if not user:
            # Set username to be unique if it already exists
            username = name
            base_username = username
            counter = 1
            
            # Check if username already exists
            while db.query(User).filter(User.username == username).first():
                username = f"{base_username}{counter}"
                counter += 1
            
            # Create a new user
            user = User(
                username=username,
                email=email,
                oauth_id=provider_user_id,
                is_oauth_user=True,
                oauth_provider=provider_id,
                first_name=first_name,
                last_name=last_name,
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
                user.oauth_id = provider_user_id
                
            # If user has a different OAuth provider, add this one as additional
            if user.oauth_provider and user.oauth_provider != provider_id:
                if not user.additional_oauth_providers:
                    user.additional_oauth_providers = {}
                user.additional_oauth_providers[provider_id] = provider_user_id
            else:
                user.oauth_provider = provider_id
                
            # Update profile info if not already set
            if first_name and not user.first_name:
                user.first_name = first_name
            if last_name and not user.last_name:
                user.last_name = last_name
            
            # Only update profile picture if one doesn't exist yet or if it was never manually deleted
            # We track manual deletion by setting a flag in the database
            if picture and (user.picture is None and not user.picture_manually_deleted):
                user.picture = picture
                
            # Update last login time
            user.last_login = datetime.utcnow()
            
            db.commit()
        
        # Set session data
        request.session["user_id"] = user.id
        request.session["username"] = user.username
        request.session["is_authenticated"] = True
        request.session["is_admin"] = user.is_admin
        request.session["oauth_provider"] = provider_id  # Store the provider for possible UI customization
        
        # Redirect to dashboard or the requested next page
        next_page = request.query_params.get("next", "/dashboard")
        return RedirectResponse(next_page, status_code=HTTP_303_SEE_OTHER)
        
    except Exception as e:
        print(f"OAuth callback error: {str(e)}")
        return RedirectResponse(
            f"/auth/login?error=OAuth+login+failed:+{str(e)}", 
            status_code=HTTP_303_SEE_OTHER
        )

# Legacy route for backward compatibility
@router.get("/oauth-login")
async def legacy_oauth_login(request: Request):
    """Redirect to Authentik OAuth login for backward compatibility"""
    return RedirectResponse("/auth/oauth-login/authentik", status_code=HTTP_302_FOUND)

@router.get("/oauth-callback")
async def legacy_oauth_callback(
    request: Request, 
    code: Optional[str] = None, 
    state: Optional[str] = None, 
    error: Optional[str] = None, 
    db: Session = Depends(get_db)
):
    """Redirect to Authentik OAuth callback handler for backward compatibility"""
    params = []
    if code:
        params.append(f"code={code}")
    if state:
        params.append(f"state={state}")
    if error:
        params.append(f"error={error}")
    
    query_string = "&".join(params)
    redirect_url = f"/auth/oauth-callback/authentik"
    if query_string:
        redirect_url = f"{redirect_url}?{query_string}"
    
    return RedirectResponse(redirect_url, status_code=HTTP_302_FOUND)

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

@router.post("/update-profile-picture", response_class=HTMLResponse)
async def update_profile_picture(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Handle profile picture upload"""
    # Check if user is logged in
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/auth/login", status_code=HTTP_303_SEE_OTHER)
    
    # Get user from database
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        request.session.clear()
        return RedirectResponse("/auth/login", status_code=HTTP_303_SEE_OTHER)
    
    # Validate file type
    valid_extensions = [".jpg", ".jpeg", ".png"]
    file_ext = os.path.splitext(file.filename)[1].lower()
    
    if file_ext not in valid_extensions:
        return templates.TemplateResponse(
            "auth/profile.html",
            {"request": request, "user": user, "error": "Invalid file type. Only JPG and PNG are allowed."}
        )
    
    # Create directory if it doesn't exist
    upload_dir = Path("app/static/uploads/profile_pictures")
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate unique filename
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = upload_dir / unique_filename
    
    # Save the file
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Update user profile with the picture URL
    user.picture = f"/static/uploads/profile_pictures/{unique_filename}"
    user.picture_manually_deleted = False  # Reset manual deletion flag
    db.commit()
    
    # Redirect back to profile with success message
    return RedirectResponse(
        "/auth/profile?message=Profile+picture+updated+successfully",
        status_code=HTTP_303_SEE_OTHER
    )

@router.post("/delete-profile-picture", response_class=HTMLResponse)
async def delete_profile_picture(
    request: Request,
    db: Session = Depends(get_db)
):
    """Handle profile picture deletion"""
    # Check if user is logged in
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/auth/login", status_code=HTTP_303_SEE_OTHER)
    
    # Get user from database
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        request.session.clear()
        return RedirectResponse("/auth/login", status_code=HTTP_303_SEE_OTHER)
    
    # Only proceed if user has a profile picture
    if user.picture:
        # Get the file path
        image_path = user.picture.replace("/static/", "app/static/")
        
        # Try to delete the file if it exists
        try:
            if os.path.exists(image_path):
                os.remove(image_path)
        except Exception as e:
            print(f"Error deleting profile picture file: {str(e)}")
            # Continue anyway since we still want to clear the database entry
        
        # Clear the picture field in the database and set the manually deleted flag
        user.picture = None
        user.picture_manually_deleted = True
        db.commit()
    
    # Redirect back to profile with success message
    return RedirectResponse(
        "/auth/profile?message=Profile+picture+deleted+successfully",
        status_code=HTTP_303_SEE_OTHER
    )

@router.post("/update-username", response_class=HTMLResponse)
async def update_username(
    request: Request,
    username: str = Form(...),
    db: Session = Depends(get_db)
):
    """Handle username update"""
    # Check if user is logged in
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/auth/login", status_code=HTTP_303_SEE_OTHER)
    
    # Get user from database
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        request.session.clear()
        return RedirectResponse("/auth/login", status_code=HTTP_303_SEE_OTHER)
    
    # Check if username is unchanged
    if user.username == username:
        return RedirectResponse(
            "/auth/profile?message=No+changes+made+to+username",
            status_code=HTTP_303_SEE_OTHER
        )
    
    # Validate username
    if len(username) < 3:
        return templates.TemplateResponse(
            "auth/profile.html",
            {"request": request, "user": user, "error": "Username must be at least 3 characters long"}
        )
    
    if len(username) > 30:
        return templates.TemplateResponse(
            "auth/profile.html",
            {"request": request, "user": user, "error": "Username must be less than 30 characters long"}
        )
    
    # Check if username contains only allowed characters (alphanumeric, underscore, hyphen)
    if not re.match(r'^[a-zA-Z0-9_-]+$', username):
        return templates.TemplateResponse(
            "auth/profile.html",
            {"request": request, "user": user, "error": "Username can only contain letters, numbers, underscores and hyphens"}
        )
    
    # Check if username already exists
    existing_user = db.query(User).filter(User.username == username).first()
    if existing_user:
        return templates.TemplateResponse(
            "auth/profile.html",
            {"request": request, "user": user, "error": "Username already taken"}
        )
    
    # Update user's username
    old_username = user.username
    user.username = username
    
    # Update session with new username
    request.session["username"] = username
    
    try:
        db.commit()
        return RedirectResponse(
            "/auth/profile?message=Username+updated+successfully",
            status_code=HTTP_303_SEE_OTHER
        )
    except Exception as e:
        db.rollback()
        print(f"Error updating username: {str(e)}")
        return templates.TemplateResponse(
            "auth/profile.html",
            {"request": request, "user": user, "error": "An error occurred while updating your username"}
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
                email_to=user.email,
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

@router.post("/delete-account", response_class=HTMLResponse)
async def delete_account(
    request: Request,
    db: Session = Depends(get_db)
):
    """Handle account deletion"""
    # Check if user is logged in
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/auth/login", status_code=HTTP_303_SEE_OTHER)
    
    # Get user from database
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        request.session.clear()
        return RedirectResponse("/auth/login", status_code=HTTP_303_SEE_OTHER)
    
    # Don't allow admins to delete their accounts through this flow
    # to prevent accidentally removing the only admin account
    if user.is_admin:
        return templates.TemplateResponse(
            "auth/profile.html",
            {"request": request, "user": user, "error": "Admin accounts cannot be deleted through this page. Please contact the system administrator."}
        )

    try:
        # Handle team memberships (anonymize rather than delete)
        from ..models import TeamMembership, TeamJoinRequest, UserPoints, EventAttendee
        
        # Get all team memberships
        memberships = db.query(TeamMembership).filter(TeamMembership.user_id == user_id).all()
        
        # Clean up any pending join requests
        db.query(TeamJoinRequest).filter(TeamJoinRequest.user_id == user_id).delete()
        
        # Instead of deleting data completely, we'll anonymize it to keep integrity
        # Update the username and email to indicate this is a deleted account
        anonymous_username = f"deleted_user_{user_id}"
        anonymous_email = f"deleted_{user_id}@deleted.user"
        
        user.username = anonymous_username
        user.email = anonymous_email
        user.is_active = False
        user.hashed_password = None
        user.picture = None
        user.first_name = None
        user.last_name = None
        user.oauth_id = None
        user.oauth_provider = None
        user.additional_oauth_providers = None
        
        # Mark account as deactivated
        db.commit()
        
        # Clear session
        request.session.clear()
        
        # Show success page
        return templates.TemplateResponse(
            "auth/account_deleted.html",
            {"request": request}
        )
    except Exception as e:
        db.rollback()
        print(f"Error deleting account: {str(e)}")
        return templates.TemplateResponse(
            "auth/profile.html",
            {"request": request, "user": user, "error": "An error occurred while deleting your account. Please try again later."}
        )

@router.get("/privacy-settings", response_class=HTMLResponse)
async def privacy_settings_page(request: Request, db: Session = Depends(get_db)):
    """Display privacy settings page"""
    # Check if user is logged in
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/auth/login", status_code=HTTP_303_SEE_OTHER)
    
    # Get user from database
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        request.session.clear()
        return RedirectResponse("/auth/login", status_code=HTTP_303_SEE_OTHER)
    
    # Get current privacy settings
    privacy_settings = user.get_privacy_settings()
    
    return templates.TemplateResponse(
        "auth/privacy_settings.html", 
        {
            "request": request, 
            "user": user,
            "privacy_settings": privacy_settings,
            "privacy_options": [
                {"value": "public", "label": "Everyone", "description": "Visible to all users"},
                {"value": "friends", "label": "Team Members", "description": "Only visible to members of your teams"},
                {"value": "private", "label": "Private", "description": "Only visible to you and admins"}
            ]
        }
    )

@router.post("/privacy-settings", response_class=HTMLResponse)
async def update_privacy_settings(
    request: Request,
    email_visibility: str = Form(...),
    full_name_visibility: str = Form(...),
    teams_visibility: str = Form(...),
    points_visibility: str = Form(...),
    achievements_visibility: str = Form(...),
    events_visibility: str = Form(...),
    db: Session = Depends(get_db)
):
    """Handle privacy settings update"""
    # Check if user is logged in
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/auth/login", status_code=HTTP_303_SEE_OTHER)
    
    # Get user from database
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        request.session.clear()
        return RedirectResponse("/auth/login", status_code=HTTP_303_SEE_OTHER)
    
    # Validate inputs
    valid_options = ["public", "friends", "private"]
    privacy_settings = {
        "email": email_visibility if email_visibility in valid_options else "private",
        "full_name": full_name_visibility if full_name_visibility in valid_options else "friends",
        "teams": teams_visibility if teams_visibility in valid_options else "public",
        "points": points_visibility if points_visibility in valid_options else "public",
        "achievements": achievements_visibility if achievements_visibility in valid_options else "public",
        "events": events_visibility if events_visibility in valid_options else "friends"
    }
    
    # Update user privacy settings
    user.privacy_settings = privacy_settings
    db.commit()
    
    # Redirect back to privacy settings with success message
    return RedirectResponse(
        "/auth/privacy-settings?message=Privacy+settings+updated+successfully",
        status_code=HTTP_303_SEE_OTHER
    )

@router.get("/user/{user_id}", response_class=HTMLResponse)
async def view_user_profile(
    request: Request,
    user_id: int,
    db: Session = Depends(get_db)
):
    """View another user's profile with privacy settings applied"""
    # Check if the requested user exists
    profile_user = db.query(User).filter(User.id == user_id).first()
    if not profile_user:
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "error": "User not found"}
        )
    
    # Get current logged-in user (if any)
    current_user_id = request.session.get("user_id")
    current_user = None
    if current_user_id:
        current_user = db.query(User).filter(User.id == current_user_id).first()
    
    # Check if the user is viewing their own profile
    if current_user_id and current_user_id == user_id:
        return RedirectResponse("/auth/profile", status_code=HTTP_303_SEE_OTHER)
    
    # Import privacy utilities
    from ..utils.auth import get_viewable_profile_data, check_privacy_permission
    
    # Get viewable profile data based on privacy settings
    profile_data = get_viewable_profile_data(db, profile_user, current_user_id)
    
    # If the user can view teams, fetch team data
    teams = []
    if profile_data["can_view_teams"]:
        from ..models import TeamMembership, Team
        team_memberships = db.query(TeamMembership, Team).join(
            Team, TeamMembership.team_id == Team.id
        ).filter(
            TeamMembership.user_id == user_id
        ).all()
        
        teams = [
            {
                "id": team.id,
                "name": team.name,
                "is_captain": membership.is_captain
            } for membership, team in team_memberships
        ]
    
    # If the user can view points, fetch points data
    total_points = 0
    if profile_data["can_view_points"]:
        from ..models import UserPoints
        points_records = db.query(UserPoints).filter(UserPoints.user_id == user_id).all()
        total_points = sum(record.points for record in points_records)
    
    return templates.TemplateResponse(
        "auth/view_profile.html", 
        {
            "request": request, 
            "profile": profile_data,
            "profile_user_id": user_id,
            "user": current_user,  # Pass the current user for menu display
            "teams": teams,
            "total_points": total_points,
        }
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
