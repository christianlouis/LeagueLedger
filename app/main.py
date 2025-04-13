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
from .auth import router as auth_router, get_current_user

# Create tables on startup
init_db()

# Seed database with initial test data
# In a production app, you would handle this differently
seed_db()

app = FastAPI()

# Configure session middleware with environment variables or defaults
secret_key = os.environ.get("SECRET_KEY", "a-default-secret-key-for-sessions-please-change-this")
if len(secret_key) < 32:
    print(f"WARNING: Secret key is too short ({len(secret_key)} chars). Recommended: 32+ chars")

# Apply SessionMiddleware FIRST - it must be the first middleware in the stack
app.add_middleware(
    SessionMiddleware,
    secret_key=secret_key,
    max_age=int(os.environ.get("SESSION_MAX_AGE", "86400")),  # 24 hours by default
    same_site="lax",  # Important for security while allowing redirects
    https_only=os.environ.get("COOKIE_SECURE", "False").lower() == "true",
    session_cookie="league_ledger_session",  # Custom cookie name
)

# Debug middleware to track session state
@app.middleware("http")
async def debug_session_middleware(request, call_next):
    """Debug middleware to track session state"""
    try:
        session_cookie = request.cookies.get("league_ledger_session")
        
        print(f"Request path: {request.url.path}")
        # Instead of checking request.scope, check if we can access the session dict
        has_session = hasattr(request, "session") and isinstance(request.session, dict)
        print(f"Has session attribute: {has_session}")
        print(f"Has session cookie: {session_cookie is not None}")
        
        # Check session data
        if hasattr(request, "session"):
            try:
                print(f"Session data before: {dict(request.session)}")
            except (TypeError, AttributeError):
                # The session might not be dict-like
                print(f"Session exists but isn't a dictionary")
    except Exception as e:
        print(f"Error in debug middleware (pre): {str(e)}")
    
    response = await call_next(request)
    
    try:
        if hasattr(request, "session"):
            try:
                print(f"Session data after: {dict(request.session)}")
            except (TypeError, AttributeError):
                print(f"Session exists but isn't a dictionary")
    except Exception as e:
        print(f"Error in debug middleware (post): {str(e)}")
    
    return response

# User context middleware to make user available in templates
@app.middleware("http")
async def add_user_to_request(request: Request, call_next):
    """Add user to request state and update template globals"""
    try:
        # Get user from session if available
        user = get_current_user(request)
        
        # Store user in request.state for route handlers
        request.state.user = user
        
        # Update template globals for all templates
        templates.env.globals["current_user"] = user
        
        # Debug output to check user and admin status
        if user:
            print(f"User in context: {user.get('username')}, Admin: {user.get('is_admin', False)}")
            
    except Exception as e:
        print(f"Error setting user context: {str(e)}")
    
    # Process the request
    response = await call_next(request)
    return response

# Routers
app.include_router(auth_router, prefix="/auth", tags=["Auth"])  # Auth router should be first
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
