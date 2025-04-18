#!/usr/bin/env python3
from fastapi import FastAPI, Request, Depends, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import os
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.authentication import AuthenticationMiddleware
from dotenv import load_dotenv
import logging
import contextlib
import time
import asyncio
import sqlalchemy
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy import text

from .db import engine, get_db
from . import models
from .templates_config import templates
from .views import qr, redeem, teams, admin, leaderboard, dashboard, static, pages, auth, convenience, setup
from .db_init import init_db
from .auth.middleware import SessionAuthBackend, on_auth_error

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

# Get secret key for the session
SECRET_KEY = os.getenv("SECRET_KEY", "a-very-secure-secret-key-for-development")

# Important: Order of middleware matters!
# First add AuthenticationMiddleware
app.add_middleware(
    AuthenticationMiddleware, 
    backend=SessionAuthBackend(),
    on_error=on_auth_error
)

# Then add SessionMiddleware (last added = first executed)
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

# Function to check database connection
async def check_db_connection(max_retries=10, initial_retry_delay=1):
    """
    Check database connection with retries and exponential backoff
    
    Args:
        max_retries: Maximum number of retry attempts
        initial_retry_delay: Initial delay before first retry in seconds
        
    Returns:
        bool: True if connection succeeded, False otherwise
    """
    retry_delay = initial_retry_delay
    
    for attempt in range(1, max_retries + 1):
        try:
            # Try a simple query to test the connection
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                logger.info(f"Database connection successful on attempt {attempt}")
                return True
        except (OperationalError, ProgrammingError) as e:
            if "Connection refused" in str(e) or "Can't connect" in str(e):
                logger.warning(f"Database connection attempt {attempt}/{max_retries} failed: {str(e)}")
                
                if attempt < max_retries:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)
                    # Exponential backoff with a maximum delay of 10 seconds
                    retry_delay = min(retry_delay * 2, 10)
                else:
                    logger.error(f"Failed to connect to database after {max_retries} attempts")
                    return False
            else:
                # For other database errors, log and continue
                logger.error(f"Database error: {str(e)}")
                return False
        except Exception as e:
            logger.error(f"Unexpected error connecting to database: {str(e)}")
            return False
            
    return False

# Initialize database with schema and tables
async def initialize_database():
    """
    Initialize the database schema and seed data
    """
    try:
        # Import models to ensure they're registered with Base before initialization
        from . import models
        
        # Initialize database (applies migrations and seeds data)
        init_db()
        logger.info("Database initialized and migrated successfully")
        return True
    except Exception as e:
        logger.error(f"Database initialization error: {str(e)}")
        return False

# Initialize database on startup
@app.on_event("startup")
async def startup_db_client():
    logger.info("Starting database initialization")
    
    # First, ensure database server is available with polling
    max_retries = 15  # Try up to 15 times (with exponential backoff, this could be ~2 minutes)
    connected = await check_db_connection(max_retries=max_retries)
    
    if connected:
        # Once connected, initialize the database
        success = await initialize_database()
        if success:
            logger.info("Database setup completed successfully")
        else:
            logger.warning("Database initialization completed with errors")
    else:
        logger.error("Failed to connect to database, application may not function correctly")

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
app.include_router(setup.router, tags=["Setup"])  # Setup router for initial admin setup
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
