#!/usr/bin/env python3
from fastapi import FastAPI, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from datetime import datetime
import os

from .db import init_db, engine
from . import models
from .templates_config import templates
from .views import qr, redeem, teams, admin, leaderboard, dashboard, auth
from .db_init import seed_db
from .dependencies import get_user_from_session

# Create tables on startup
init_db()

# Seed database with initial test data
# In a production app, you would handle this differently
seed_db()

app = FastAPI()

# IMPORTANT: Add SessionMiddleware FIRST before any other middleware
# This ensures session data is available to all other middleware and route handlers
app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get("SECRET_KEY", "a-default-secret-key-for-sessions"),
    max_age=int(os.environ.get("SESSION_MAX_AGE", 86400)),  # 24 hours
    same_site="lax",  # Important for security while allowing redirects
    https_only=os.environ.get("COOKIE_SECURE", "False").lower() == "true",
    session_cookie="league_ledger_session",  # Custom cookie name for clarity
)

# Add debugging middleware to help track sessions
@app.middleware("http")
async def debug_session_middleware(request, call_next):
    """Debug middleware to track session state"""
    session_cookie = request.cookies.get("league_ledger_session")
    
    print(f"Request path: {request.url.path}")
    print(f"Has session attribute: {'session' in request.scope}")
    print(f"Has session cookie: {session_cookie is not None}")
    
    if "session" in request.scope:
        print(f"Session data before: {dict(request.session)}")
    
    response = await call_next(request)
    
    if "session" in request.scope:
        print(f"Session data after: {dict(request.session)}")
    
    return response

# Update the template globals at app startup to access the request
@app.middleware("http")
async def add_user_to_request(request: Request, call_next):
    # Print debugging information
    print(f"Processing request to: {request.url.path}")
    
    # Add user to request state so templates can access it
    try:
        if "session" in request.scope:
            print("Session found in request scope")
            if "user_id" in request.session:
                print(f"User ID in session: {request.session['user_id']}")
                # Get user from session
                user = await get_user_from_session(request)
                request.state.user = user
            else:
                print("No user_id in session")
                request.state.user = None
        else:
            print("No session in request scope")
            request.state.user = None
    except Exception as e:
        print(f"Error in middleware: {e}")
        request.state.user = None
    
    # Update template context with current user before processing the request
    templates.env.globals["current_user"] = request.state.user
    
    # Process the request
    response = await call_next(request)
    return response

# Routers
app.include_router(auth.router, prefix="/auth", tags=["Auth"])  # Auth router should be first
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
        "now": datetime.now,
        "current_user": getattr(request.state, "user", None)
    })

@app.get("/about", response_class=HTMLResponse)
def about(request: Request):
    return templates.TemplateResponse("about.html", {
        "request": request,
        "current_user": getattr(request.state, "user", None)
    })

@app.get("/contact", response_class=HTMLResponse)
def contact(request: Request):
    return templates.TemplateResponse("contact.html", {
        "request": request,
        "current_user": getattr(request.state, "user", None)
    })

@app.get("/privacy", response_class=HTMLResponse)
def privacy(request: Request):
    return templates.TemplateResponse("privacy.html", {
        "request": request,
        "current_user": getattr(request.state, "user", None)
    })

@app.get("/terms", response_class=HTMLResponse)
def terms(request: Request):
    return templates.TemplateResponse("terms.html", {
        "request": request,
        "current_user": getattr(request.state, "user", None)
    })
