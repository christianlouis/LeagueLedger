#!/usr/bin/env python3
from fastapi import FastAPI, Request, Depends, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
import os
from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv

from .db import init_db, engine, get_db
from . import models
from .templates_config import templates
from .views import qr, redeem, teams, admin, leaderboard, dashboard, static, pages, auth
from .db_init import seed_db
from .db_migrations import apply_migrations

# Load environment variables
load_dotenv()

# Create tables on startup
init_db()

# Apply any pending database migrations
apply_migrations()

# Seed database with initial test data
# In a production app, you would handle this differently
seed_db()

# Create the FastAPI application
app = FastAPI(title="LeagueLedger")

# Add SessionMiddleware with a secure secret key
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SESSION_SECRET_KEY", "your-very-secret-session-key"))

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Configure static files
static.configure_static_files(app)

# Setup Jinja2 templates
templates = Jinja2Templates(directory="app/templates")

# User context middleware to make template globals available
@app.middleware("http")
async def add_template_globals(request: Request, call_next):
    """Add template globals"""
    try:
        # Update template globals for all templates
        user = None
        if "user_id" in request.session and request.session.get("is_authenticated"):
            # Mock user object - in a real app, you'd fetch this from the database
            user = {
                "id": request.session["user_id"],
                "username": request.session.get("username", "User"),
                "is_admin": request.session.get("is_admin", False)
            }
        templates.env.globals["current_user"] = user
    except Exception as e:
        print(f"Error setting template globals: {str(e)}")
    
    # Process the request
    response = await call_next(request)
    return response

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    user = None
    if "user_id" in request.session and request.session.get("is_authenticated"):
        user = {
            "id": request.session["user_id"],
            "username": request.session.get("username", "User"),
            "is_admin": request.session.get("is_admin", False)
        }
    return templates.TemplateResponse(
        "index.html", 
        {"request": request, "user": user}
    )

# Routers
app.include_router(pages.router, tags=["Pages"])  # Pages router for index and static pages
app.include_router(auth.router)  # Include the auth router
app.include_router(qr.router, prefix="/qr", tags=["QR"])
app.include_router(redeem.router, prefix="/redeem", tags=["Redeem"])
app.include_router(teams.router, prefix="/teams", tags=["Teams"])
app.include_router(admin.router, prefix="/admin", tags=["Admin"])
app.include_router(leaderboard.router, prefix="/leaderboard", tags=["Leaderboard"])
app.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
app.include_router(static.router, tags=["Static"])  # Include the static router

# Add a direct route for /scan that redirects to /redeem/scan
@app.get("/scan")
async def scan_redirect():
    return RedirectResponse("/redeem/scan", status_code=303)

# Add convenience routes for auth paths
@app.get("/login")
async def login_redirect():
    return RedirectResponse("/auth/login", status_code=303)

@app.get("/register")
async def register_redirect():
    return RedirectResponse("/auth/register", status_code=303)

@app.get("/profile")
async def profile_redirect():
    return RedirectResponse("/auth/profile", status_code=303)

@app.get("/logout")
async def logout_redirect():
    return RedirectResponse("/auth/logout", status_code=303)
