#!/usr/bin/env python3
"""
Router for static content pages like about, contact, privacy, and terms.
"""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from ..templates_config import templates
from datetime import datetime

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
def index(request: Request):
    """Home page."""
    return templates.TemplateResponse("index.html", {
        "request": request, 
        "now": datetime.now
    })

@router.get("/about", response_class=HTMLResponse)
def about(request: Request):
    """About page."""
    return templates.TemplateResponse("about.html", {
        "request": request
    })

@router.get("/contact", response_class=HTMLResponse)
def contact(request: Request):
    """Contact page."""
    return templates.TemplateResponse("contact.html", {
        "request": request
    })

@router.get("/privacy", response_class=HTMLResponse)
def privacy(request: Request):
    """Privacy policy page."""
    return templates.TemplateResponse("privacy.html", {
        "request": request
    })

@router.get("/terms", response_class=HTMLResponse)
def terms(request: Request):
    """Terms and conditions page."""
    return templates.TemplateResponse("terms.html", {
        "request": request
    })
