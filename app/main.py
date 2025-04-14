#!/usr/bin/env python3
from fastapi import FastAPI, Request, Depends, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import os
from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv
import logging
import contextlib

from .db import init_db, engine, get_db
from . import models
from .templates_config import templates
from .views import qr, redeem, teams, admin, leaderboard, dashboard, static, pages, auth, convenience
from .db_init import seed_db
from .db_migrations import apply_migrations

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Create the FastAPI application
app = FastAPI(title="LeagueLedger")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add SessionMiddleware with a secure secret key
SECRET_KEY = os.getenv("SECRET_KEY", "a-very-secure-secret-key-for-development")
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

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
    """Add global variables to all templates."""
    try:
        # Set user in request state for templates
        if hasattr(request, "session"):
            user_id = request.session.get("user_id")
            if user_id:
                # Get a database session
                from sqlalchemy.orm import Session
                from .db import SessionLocal
                from .models import User
                
                db = SessionLocal()
                try:
                    # Fetch actual user from database
                    user = db.query(User).filter(User.id == user_id).first()
                    if user:
                        request.state.user = user
                    else:
                        request.state.user = None
                finally:
                    db.close()
            else:
                request.state.user = None
        else:
            request.state.user = None
    except Exception as e:
        # Log error but continue processing
        logger.error(f"Error setting template globals: {str(e)}")
        request.state.user = None
        
    # Continue with request
    response = await call_next(request)
    return response

# Handle exceptions
@app.exception_handler(404)
async def not_found_exception_handler(request: Request, exc):
    """Handle 404 errors with a custom template."""
    return templates.TemplateResponse(
        "error.html",
        {"request": request, "error": "Page not found"},
        status_code=404
    )

# Routers
app.include_router(pages.router, tags=["Pages"])  # Pages router for index and static pages
app.include_router(auth.router, prefix="/auth", tags=["auth"])  # Include the auth router
app.include_router(qr.router, prefix="/qr", tags=["QR"])
app.include_router(redeem.router, prefix="/redeem", tags=["Redeem"])
app.include_router(teams.router, prefix="/teams", tags=["teams"])
app.include_router(admin.router, prefix="/admin", tags=["Admin"])
app.include_router(leaderboard.router, prefix="/leaderboard", tags=["leaderboard"])
app.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
app.include_router(static.router, tags=["Static"])  # Include the static router
app.include_router(convenience.router, tags=["Convenience"])  # Include convenience routes
