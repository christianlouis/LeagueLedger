#!/usr/bin/env python3
from fastapi import FastAPI, Request, Depends, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
import os
from starlette.middleware.sessions import SessionMiddleware

from .db import init_db, engine
from . import models
from .templates_config import templates
from .views import qr, redeem, teams, admin, leaderboard, dashboard, static, pages
from .db_init import seed_db

# Create tables on startup
init_db()

# Seed database with initial test data
# In a production app, you would handle this differently
seed_db()

# Create the FastAPI application
app = FastAPI(title="LeagueLedger")

# Add SessionMiddleware with a secure secret key
app.add_middleware(SessionMiddleware, secret_key="your-very-secret-session-key")

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
        templates.env.globals["current_user"] = None
    except Exception as e:
        print(f"Error setting template globals: {str(e)}")
    
    # Process the request
    response = await call_next(request)
    return response

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse(
        "index.html", 
        {"request": request, "user": None}
    )

# Routers
app.include_router(pages.router, tags=["Pages"])  # Pages router for index and static pages
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
