#!/usr/bin/env python3
"""
Router for static content pages like about, contact, privacy, and terms.
"""
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from ..templates_config import templates
from datetime import datetime
from sqlalchemy.orm import Session
from ..db import get_db
from .. import models

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
def index(request: Request, db: Session = Depends(get_db)):
    """Home page."""
    # Get user from session for navbar
    user = None
    user_id = request.session.get("user_id")
    if user_id:
        user = db.query(models.User).get(user_id)
    
    return templates.TemplateResponse("index.html", {
        "request": request, 
        "now": datetime.now,
        "user": user
    })

@router.get("/about", response_class=HTMLResponse)
def about(request: Request, db: Session = Depends(get_db)):
    """About page."""
    # Get user from session for navbar
    user = None
    user_id = request.session.get("user_id")
    if user_id:
        user = db.query(models.User).get(user_id)
    
    return templates.TemplateResponse("about.html", {
        "request": request,
        "user": user
    })

@router.get("/contact", response_class=HTMLResponse)
def contact(request: Request, db: Session = Depends(get_db)):
    """Contact page."""
    # Get user from session for navbar
    user = None
    user_id = request.session.get("user_id")
    if user_id:
        user = db.query(models.User).get(user_id)
    
    return templates.TemplateResponse("contact.html", {
        "request": request,
        "user": user
    })

@router.get("/privacy", response_class=HTMLResponse)
def privacy(request: Request, db: Session = Depends(get_db)):
    """Privacy policy page."""
    # Get user from session for navbar
    user = None
    user_id = request.session.get("user_id")
    if user_id:
        user = db.query(models.User).get(user_id)
    
    return templates.TemplateResponse("privacy.html", {
        "request": request,
        "user": user
    })

@router.get("/terms", response_class=HTMLResponse)
def terms(request: Request, db: Session = Depends(get_db)):
    """Terms and conditions page."""
    # Get user from session for navbar
    user = None
    user_id = request.session.get("user_id")
    if user_id:
        user = db.query(models.User).get(user_id)
    
    return templates.TemplateResponse("terms.html", {
        "request": request,
        "user": user
    })

@router.get("/cookies", response_class=HTMLResponse)
def cookies(request: Request, db: Session = Depends(get_db)):
    """Cookie policy page."""
    # Get user from session for navbar
    user = None
    user_id = request.session.get("user_id")
    if user_id:
        user = db.query(models.User).get(user_id)
    
    return templates.TemplateResponse("cookies.html", {
        "request": request,
        "user": user
    })

@router.get("/impressum", response_class=HTMLResponse)
def impressum(request: Request, db: Session = Depends(get_db)):
    """Imprint/Impressum page."""
    # Get user from session for navbar
    user = None
    user_id = request.session.get("user_id")
    if user_id:
        user = db.query(models.User).get(user_id)
    
    return templates.TemplateResponse("impressum.html", {
        "request": request,
        "user": user
    })
