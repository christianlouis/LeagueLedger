#!/usr/bin/env python3
from fastapi import FastAPI, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from datetime import datetime
import os

from .db import init_db, engine
from . import models
from .templates_config import templates
from .views import qr, redeem, teams, admin, leaderboard, dashboard
from .db_init import seed_db

# Create tables on startup
init_db()

# Seed database with initial test data
# In a production app, you would handle this differently
seed_db()

app = FastAPI()

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

# Routers - auth router removed
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
