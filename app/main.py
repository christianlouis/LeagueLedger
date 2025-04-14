#!/usr/bin/env python3
from fastapi import FastAPI, Request, Depends, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
import os
from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv
import logging
import contextlib

from .db import init_db, engine, get_db
from . import models
from .templates_config import templates
from .views import qr, redeem, teams, admin, leaderboard, dashboard, static, pages, auth
from .db_init import seed_db
from .db_migrations import apply_migrations

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Create the FastAPI application
app = FastAPI(title="LeagueLedger")

# Add SessionMiddleware with a secure secret key
# Must be added first before other middleware to ensure it's available
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SESSION_SECRET_KEY", "your-very-secret-session-key"))

# Initialize database on startup
@app.on_event("startup")
async def startup_db_client():
    logger.info("Starting database initialization")
    try:
        # Import models to ensure they're registered with Base before initialization
        from . import models
        
        # Create all tables first
        init_db()
        logger.info("Base tables created successfully")
        
        # Apply migrations to add additional columns and constraints
        with contextlib.suppress(Exception):
            apply_migrations()
            logger.info("Migrations applied successfully")
        
        # Seed the database with test data if needed
        with contextlib.suppress(Exception):
            seed_db()
            logger.info("Database seeded successfully")
            
    except Exception as e:
        logger.error(f"Database initialization error: {str(e)}")
        # We continue even if there was an error, as the application might still work with partial functionality

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Configure static files
static.configure_static_files(app)

# Setup Jinja2 templates
templates = Jinja2Templates(directory="app/templates")

# User context middleware
@app.middleware("http")
async def add_template_globals(request: Request, call_next):
    """Add template globals"""
    try:
        # Update template globals for all templates
        user = None
        if hasattr(request, "session") and "user_id" in request.session and request.session.get("is_authenticated"):
            # Mock user object - in a real app, you'd fetch this from the database
            user = {
                "id": request.session["user_id"],
                "username": request.session.get("username", "User"),
                "is_admin": request.session.get("is_admin", False)
            }
        templates.env.globals["current_user"] = user
    except Exception as e:
        logger.error(f"Error setting template globals: {str(e)}")
    
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

# Add a direct route for /scan that redirects to /dashboard/scan
@app.get("/scan")
async def scan_redirect():
    return RedirectResponse("/dashboard/scan", status_code=303)

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
