#!/usr/bin/env python3
from fastapi import FastAPI, Request, status, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from datetime import datetime
import os

from .db import init_db, engine
from . import models
from .templates_config import templates
from .views import qr, redeem, teams, admin, leaderboard, dashboard
from .db_init import seed_db
from .auth import router as auth_router
from .dependencies import get_user_from_session

# Create tables on startup
init_db()

# Seed database with initial test data
# In a production app, you would handle this differently
seed_db()

# Initialize FastAPI app
app = FastAPI()

# Configure session middleware settings
secret_key = os.environ.get("SECRET_KEY", "a-default-secret-key-for-sessions-please-change-this")
if len(secret_key) < 32:
    print(f"WARNING: Secret key is too short ({len(secret_key)} chars). Recommended: 32+ chars")

# IMPORTANT: Add SessionMiddleware before anything else
# This must be the FIRST middleware in the stack
app.add_middleware(
    SessionMiddleware,
    secret_key=secret_key,
    max_age=int(os.environ.get("SESSION_MAX_AGE", "86400")),  # 24 hours by default
    same_site="lax",
    https_only=os.environ.get("COOKIE_SECURE", "False").lower() == "true",
    session_cookie="league_ledger_session",
)

# Debug middleware - ADDED AFTER SessionMiddleware
@app.middleware("http")
async def debug_session_middleware(request, call_next):
    """Debug middleware to track session state"""
    try:
        session_cookie = request.cookies.get("league_ledger_session")
        
        print(f"Request path: {request.url.path}")
        # First check if the session attribute exists properly
        has_session = hasattr(request, "session")
        is_dict = has_session and isinstance(request.session, dict)
        print(f"Has session attribute: {has_session}")
        print(f"Session is dict: {is_dict}")
        print(f"Has session cookie: {session_cookie is not None}")
        
        # Safely check session data
        if has_session and is_dict:
            print(f"Session data before: {dict(request.session)}")
    except Exception as e:
        print(f"Error in debug middleware (pre): {str(e)}")
    
    response = await call_next(request)
    
    try:
        if hasattr(request, "session"):
            print(f"Session data after: {dict(request.session)}")
    except Exception as e:
        print(f"Error in debug middleware (post): {str(e)}")
    
    return response

# User context middleware
@app.middleware("http")
async def add_user_to_request(request: Request, call_next):
    """Add user to request state and update template globals"""
    try:
        # Get database connection from context
        from .db import SessionLocal
        db = SessionLocal()
        
        # Get user from session with safer approach
        user = None
        try:
            user = get_user_from_session(request, db)
        except Exception as e:
            print(f"Error getting user for request context: {str(e)}")
        
        # Store user in request.state for route handlers
        request.state.user = user
        
        # Update template globals for all templates
        templates.env.globals["current_user"] = user
        
        # Debug output to check user and admin status
        if user:
            print(f"User in context: {user.username}, Admin: {getattr(user, 'is_admin', False)}")
    except Exception as e:
        print(f"Error setting user context: {str(e)}")
    finally:
        # Always close the DB connection
        if 'db' in locals():
            db.close()
    
    # Process the request
    response = await call_next(request)
    return response

# Routers - include after middleware setup is complete
app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(qr.router, prefix="/qr", tags=["QR"])
app.include_router(redeem.router, prefix="/redeem", tags=["Redeem"])
app.include_router(teams.router, prefix="/teams", tags=["Teams"])
app.include_router(admin.router, prefix="/admin", tags=["Admin"])
app.include_router(leaderboard.router, prefix="/leaderboard", tags=["Leaderboard"])
app.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request, 
        "now": datetime.now
    })

@app.get("/about", response_class=HTMLResponse)
def about(request: Request):
    return templates.TemplateResponse("about.html", {
        "request": request
    })

@app.get("/contact", response_class=HTMLResponse)
def contact(request: Request):
    return templates.TemplateResponse("contact.html", {
        "request": request
    })

@app.get("/privacy", response_class=HTMLResponse)
def privacy(request: Request):
    return templates.TemplateResponse("privacy.html", {
        "request": request
    })

@app.get("/terms", response_class=HTMLResponse)
def terms(request: Request):
    return templates.TemplateResponse("terms.html", {
        "request": request
    })
