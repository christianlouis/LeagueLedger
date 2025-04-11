#!/usr/bin/env python3
"""
Authentication routes for user login, registration, and management.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request, Form, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import inspect
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import smtplib
from email.message import EmailMessage
import os

from ..db import SessionLocal, engine
from ..models import User
from ..security import (
    verify_password, get_password_hash, create_access_token, generate_token,
    SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
)
from ..dependencies import get_db, get_current_user, get_user_from_session
from ..templates_config import templates
from ..schemas import UserCreate, UserLogin, UserUpdate, PasswordReset

router = APIRouter()

# Check if all required user columns exist
def get_available_user_columns():
    inspector = inspect(engine)
    if 'users' in inspector.get_table_names():
        return [col['name'] for col in inspector.get_columns('users')]
    return []

# --- HTML ROUTES (Web UI) ---

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, next: str = "/"):
    """Display login page."""
    # Debug print to check what's happening in the route
    print("Login page accessed, checking session...")
    
    # DO NOT redirect if user is logged in - there's likely an issue with session handling
    # Just render the login page regardless of session state for now
    return templates.TemplateResponse(
        "auth/login.html", 
        {
            "request": request, 
            "next": next,
            "messages": []
        }
    )

@router.post("/login", response_class=HTMLResponse)
async def login(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    username: str = Form(...),
    password: str = Form(...),
    remember: bool = Form(False),
    next: str = Form("/")
):
    """Process login form."""
    # Try to authenticate user
    user = db.query(User).filter((User.username == username) | (User.email == username)).first()
    
    if not user or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse(
            "auth/login.html",
            {
                "request": request,
                "next": next,
                "messages": [{"type": "error", "text": "Invalid username or password"}],
                "username": username
            },
            status_code=status.HTTP_401_UNAUTHORIZED
        )
    
    # Check if is_active column exists and if user is active
    columns = get_available_user_columns()
    if 'is_active' in columns and hasattr(user, 'is_active') and not user.is_active:
        return templates.TemplateResponse(
            "auth/login.html",
            {
                "request": request,
                "next": next,
                "messages": [{"type": "error", "text": "Account is deactivated"}],
                "username": username
            },
            status_code=status.HTTP_401_UNAUTHORIZED
        )
    
    # Update last login time if column exists
    if 'last_login' in columns and hasattr(user, 'last_login'):
        user.last_login = datetime.utcnow()
        db.commit()
    
    # Debug info
    print(f"User authenticated: {user.username}")
    
    # Set session data with better error handling
    try:
        # Use directly accessible dictionary
        request.session["user_id"] = user.id 
        request.session["username"] = user.username
        request.session["_permanent"] = True
        
        # Check if is_admin attribute exists
        if hasattr(user, "is_admin"):
            request.session["is_admin"] = user.is_admin
        else:
            request.session["is_admin"] = False
        
        # Add timestamp for session creation
        request.session["created_at"] = str(datetime.now())
        
        # Debug session data
        print(f"Session data set: {dict(request.session)}")
    except Exception as e:
        print(f"Error setting session: {str(e)}")
    
    # Redirect to next page or home
    return RedirectResponse(url=next, status_code=status.HTTP_303_SEE_OTHER)

@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """Display registration page."""
    # Check if user is already logged in
    user = await get_user_from_session(request)
    if user:
        return RedirectResponse(url="/")
        
    return templates.TemplateResponse("auth/register.html", {"request": request})

@router.post("/register", response_class=HTMLResponse)
async def register(
    request: Request,
    db: Session = Depends(get_db),
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
):
    """Process registration form."""
    # Validate the form data
    if password != confirm_password:
        return templates.TemplateResponse(
            "auth/register.html",
            {
                "request": request,
                "messages": [{"type": "error", "text": "Passwords do not match"}],
                "username": username,
                "email": email
            }
        )
    
    # Check if username already exists
    if db.query(User).filter(User.username == username).first():
        return templates.TemplateResponse(
            "auth/register.html",
            {
                "request": request,
                "messages": [{"type": "error", "text": "Username already exists"}],
                "username": username,
                "email": email
            }
        )
    
    # Check if email already exists
    if db.query(User).filter(User.email == email).first():
        return templates.TemplateResponse(
            "auth/register.html",
            {
                "request": request,
                "messages": [{"type": "error", "text": "Email already exists"}],
                "username": username,
                "email": email
            }
        )
    
    # Create new user
    hashed_password = get_password_hash(password)
    
    # Get available columns
    columns = get_available_user_columns()
    user_data = {
        "username": username,
        "email": email,
        "hashed_password": hashed_password
    }
    
    # Add optional fields only if they exist in the database
    if 'is_active' in columns:
        user_data["is_active"] = True
    if 'is_verified' in columns:
        user_data["is_verified"] = False
    if 'verification_token' in columns:
        user_data["verification_token"] = generate_token()
    
    new_user = User(**user_data)
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # In a real app, send verification email here
    # For now, just redirect to a success page
    
    # Log the user in
    request.session["user_id"] = new_user.id
    
    return RedirectResponse(
        url="/auth/registration-success",
        status_code=status.HTTP_303_SEE_OTHER
    )

@router.get("/registration-success", response_class=HTMLResponse)
async def registration_success(request: Request):
    """Display registration success page."""
    return templates.TemplateResponse("auth/registration_success.html", {"request": request})

@router.get("/logout")
async def logout(request: Request):
    """Log user out by clearing session."""
    request.session.clear()
    return RedirectResponse(url="/")

@router.get("/profile", response_class=HTMLResponse)
async def profile_page(
    request: Request,
    db: Session = Depends(get_db)
):
    """Display user profile page."""
    user = await get_user_from_session(request)
    if not user:
        return RedirectResponse(url="/auth/login?next=/auth/profile")
    
    # Get user's teams (using fresh user object from database to ensure relationships are loaded)
    user = db.query(User).filter(User.id == user.id).first()
    
    user_teams = []
    for membership in user.memberships:
        user_teams.append({
            "team": membership.team,
            "is_admin": membership.is_admin
        })
    
    return templates.TemplateResponse(
        "auth/profile.html", 
        {
            "request": request, 
            "user": user,
            "user_teams": user_teams
        }
    )

@router.post("/update-profile", response_class=HTMLResponse)
async def update_profile(
    request: Request,
    db: Session = Depends(get_db),
    username: str = Form(None),
    email: str = Form(None),
):
    """Update user profile information."""
    user = await get_user_from_session(request)
    if not user:
        return RedirectResponse(url="/auth/login?next=/auth/profile")
    
    # Check for username collision
    if username and username != user.username:
        existing_user = db.query(User).filter(User.username == username).first()
        if existing_user:
            return templates.TemplateResponse(
                "auth/profile.html", 
                {
                    "request": request, 
                    "user": user,
                    "messages": [{"type": "error", "text": "Username already exists"}]
                }
            )
        user.username = username
    
    # Check for email collision
    if email and email != user.email:
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            return templates.TemplateResponse(
                "auth/profile.html", 
                {
                    "request": request, 
                    "user": user,
                    "messages": [{"type": "error", "text": "Email already exists"}]
                }
            )
        user.email = email
    
    db.commit()
    
    return templates.TemplateResponse(
        "auth/profile.html", 
        {
            "request": request, 
            "user": user,
            "messages": [{"type": "success", "text": "Profile updated successfully"}]
        }
    )

@router.post("/change-password", response_class=HTMLResponse)
async def change_password(
    request: Request,
    db: Session = Depends(get_db),
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
):
    """Change user password."""
    user = await get_user_from_session(request)
    if not user:
        return RedirectResponse(url="/auth/login?next=/auth/profile")
    
    # Verify current password
    if not verify_password(current_password, user.hashed_password):
        return templates.TemplateResponse(
            "auth/profile.html", 
            {
                "request": request, 
                "user": user,
                "messages": [{"type": "error", "text": "Current password is incorrect"}]
            }
        )
    
    # Check if new passwords match
    if new_password != confirm_password:
        return templates.TemplateResponse(
            "auth/profile.html", 
            {
                "request": request, 
                "user": user,
                "messages": [{"type": "error", "text": "New passwords do not match"}]
            }
        )
    
    # Update password
    user.hashed_password = get_password_hash(new_password)
    db.commit()
    
    return templates.TemplateResponse(
        "auth/profile.html", 
        {
            "request": request, 
            "user": user,
            "messages": [{"type": "success", "text": "Password changed successfully"}]
        }
    )

@router.get("/forgot-password", response_class=HTMLResponse)
async def forgot_password_page(request: Request):
    """Display forgot password page."""
    return templates.TemplateResponse("auth/forgot_password.html", {"request": request})

@router.post("/forgot-password")
async def forgot_password(
    request: Request,
    db: Session = Depends(get_db),
    email: str = Form(...)
):
    """Process forgot password form."""
    # Find user by email
    user = db.query(User).filter(User.email == email).first()
    
    # Always show success to prevent email enumeration
    if not user:
        return templates.TemplateResponse(
            "auth/forgot_password_sent.html", 
            {"request": request}
        )
    
    # Generate reset token
    reset_token = generate_token()
    user.reset_token = reset_token
    user.reset_token_expires_at = datetime.utcnow() + timedelta(hours=1)
    db.commit()
    
    # In a real app, send email with reset link
    # For demo, just show the reset link on the success page
    reset_url = f"/auth/reset-password?token={reset_token}"
    
    return templates.TemplateResponse(
        "auth/forgot_password_sent.html", 
        {
            "request": request,
            "reset_url": reset_url  # Remove in production, just for demo
        }
    )

@router.get("/reset-password", response_class=HTMLResponse)
async def reset_password_page(
    request: Request,
    token: str,
    db: Session = Depends(get_db)
):
    """Display reset password page."""
    # Check if token exists and is valid
    user = db.query(User).filter(
        User.reset_token == token,
        User.reset_token_expires_at > datetime.utcnow()
    ).first()
    
    if not user:
        return templates.TemplateResponse(
            "auth/reset_password_error.html", 
            {"request": request}
        )
    
    return templates.TemplateResponse(
        "auth/reset_password.html", 
        {"request": request, "token": token}
    )

@router.post("/reset-password")
async def reset_password(
    request: Request,
    db: Session = Depends(get_db),
    token: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...)
):
    """Process reset password form."""
    # Check if token exists and is valid
    user = db.query(User).filter(
        User.reset_token == token,
        User.reset_token_expires_at > datetime.utcnow()
    ).first()
    
    if not user:
        return templates.TemplateResponse(
            "auth/reset_password_error.html", 
            {"request": request}
        )
    
    # Check if passwords match
    if new_password != confirm_password:
        return templates.TemplateResponse(
            "auth/reset_password.html", 
            {
                "request": request, 
                "token": token,
                "messages": [{"type": "error", "text": "Passwords do not match"}]
            }
        )
    
    # Update password
    user.hashed_password = get_password_hash(new_password)
    user.reset_token = None
    user.reset_token_expires_at = None
    db.commit()
    
    return templates.TemplateResponse(
        "auth/reset_password_success.html", 
        {"request": request}
    )

@router.get("/delete-account", response_class=HTMLResponse)
async def delete_account_page(request: Request):
    """Display delete account confirmation page."""
    user = await get_user_from_session(request)
    if not user:
        return RedirectResponse(url="/auth/login?next=/auth/delete-account")
    
    return templates.TemplateResponse("auth/delete_account.html", {"request": request})

@router.post("/delete-account")
async def delete_account(
    request: Request,
    db: Session = Depends(get_db),
    password: str = Form(...)
):
    """Process account deletion."""
    user = await get_user_from_session(request)
    if not user:
        return RedirectResponse(url="/auth/login?next=/auth/delete-account")
    
    # Verify password
    if not verify_password(password, user.hashed_password):
        return templates.TemplateResponse(
            "auth/delete_account.html", 
            {
                "request": request,
                "messages": [{"type": "error", "text": "Incorrect password"}]
            }
        )
    
    # In a real app, you might want to anonymize the user data instead
    # of deleting it completely, but for this demo we'll delete
    
    # Clear session
    request.session.clear()
    
    # Delete user
    db.delete(user)
    db.commit()
    
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

# --- API ROUTES (for potential SPA frontend) ---

@router.post("/token")
async def login_api(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """API login endpoint returning JWT token."""
    # Authenticate user
    user = db.query(User).filter((User.username == form_data.username) | (User.email == form_data.username)).first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    columns = get_available_user_columns()
    if 'is_active' in columns and hasattr(user, 'is_active') and not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if 'last_login' in columns and hasattr(user, 'last_login'):
        user.last_login = datetime.utcnow()
        db.commit()
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user.id,
        "username": user.username
    }

@router.get("/session-test")
async def test_session(request: Request):
    """Test endpoint to verify session data persistence"""
    has_session = hasattr(request, "session")
    session_data = dict(request.session) if has_session else {}
    
    return {
        "has_session": has_session,
        "session_data": session_data,
        "authenticated": "user_id" in session_data
    }
