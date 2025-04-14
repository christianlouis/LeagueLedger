#!/usr/bin/env python3
"""
Redeem a QR code and attribute points to a team.
"""
import os
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime
from ..db import SessionLocal
from ..models import QRCode, User, Team, TeamMembership, TeamAchievement
from ..templates_config import templates

router = APIRouter()

# Get base URL from environment variable or use default
BASE_URL = os.environ.get("LEAGUELEDGER_BASE_URL", "https://rover.leagueledger.net")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/{code}", response_class=HTMLResponse)
def redeem_code(code: str, request: Request, db: Session = Depends(get_db)):
    """
    Display a page to let the user choose which team to apply points to.
    No login required.
    """
    # Get user from session for navbar
    user = None
    user_id = request.session.get("user_id")
    if user_id:
        user = db.query(User).get(user_id)

    # Find the QR code record
    qr_code = db.query(QRCode).filter_by(code=code).first()
    
    # Handle invalid or already used codes
    if not qr_code:
        return templates.TemplateResponse(
            "error.html", 
            {
                "request": request,
                "error_title": "Invalid Code",
                "error_message": "This QR code is invalid or does not exist.",
                "user": user  # Add user to the context
            }
        )
    
    if qr_code.used and (not qr_code.max_uses or qr_code.max_uses <= 1):
        return templates.TemplateResponse(
            "error.html", 
            {
                "request": request,
                "error_title": "Code Already Used",
                "error_message": "This QR code has already been redeemed.",
                "user": user  # Add user to the context
            }
        )
    
    # Check expiration if applicable
    if qr_code.expires_at and qr_code.expires_at < datetime.now():
        return templates.TemplateResponse(
            "error.html", 
            {
                "request": request,
                "error_title": "Expired Code",
                "error_message": "This QR code has expired and can no longer be redeemed.",
                "user": user  # Add user to the context
            }
        )

    # Get all available teams
    all_teams = db.query(Team).all()

    return templates.TemplateResponse("redeem.html", {
        "request": request,
        "ticket": qr_code,  # Using the same template variable name for compatibility
        "user_teams": all_teams,
        "has_achievement": bool(qr_code.achievement_name),
        "base_url": BASE_URL,
        "user": user  # Add user to the context
    })

@router.get("/scan", response_class=HTMLResponse)
def scan_qr_code(request: Request, db: Session = Depends(get_db)):
    """
    Display the QR code scanner page
    """
    # Get user from session for navbar
    user = None
    user_id = request.session.get("user_id")
    if user_id:
        user = db.query(User).get(user_id)
        
    return templates.TemplateResponse("scan_qr.html", {
        "request": request,
        "user": user  # Add user to the context
    })

@router.post("/apply/{code}")
async def apply_code(
    request: Request,
    code: str,
    db: Session = Depends(get_db)
):
    """
    Apply the QR code to a selected team and award points and/or achievements
    """
    # Get user from session for navbar
    user = None
    user_id = request.session.get("user_id")
    if user_id:
        user = db.query(User).get(user_id)
    
    # Get form data
    form_data = await request.form()
    team_id = int(form_data.get("team_id", 0))
    
    if team_id <= 0:
        return templates.TemplateResponse(
            "error.html", 
            {
                "request": request,
                "error_title": "Team Selection Required",
                "error_message": "Please select a team to redeem this code.",
                "user": user  # Add user to the context
            }
        )
    
    # Get the QR code
    qr_code = db.query(QRCode).filter_by(code=code).first()
    if not qr_code:
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "error_title": "Invalid Code",
                "error_message": "This QR code is invalid or does not exist.",
                "user": user  # Add user to the context
            }
        )
    
    # Check if the code is already used (for single-use codes)
    if qr_code.used and (not qr_code.max_uses or qr_code.max_uses <= 1):
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "error_title": "Code Already Used",
                "error_message": "This QR code has already been redeemed.",
                "user": user  # Add user to the context
            }
        )
    
    # Check expiration if applicable
    if qr_code.expires_at and qr_code.expires_at < datetime.now():
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "error_title": "Expired Code",
                "error_message": "This QR code has expired and can no longer be redeemed.",
                "user": user  # Add user to the context
            }
        )

    team = db.query(Team).filter_by(id=team_id).first()
    if not team:
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "error_title": "Team Not Found",
                "error_message": "The selected team could not be found.",
                "user": user  # Add user to the context
            }
        )

    # Mark the QR code as redeemed
    qr_code.redeemed_at_team = team.id
    qr_code.redeemed_at = datetime.now()
    qr_code.used = True
    
    # Handle achievements if present
    if qr_code.achievement_name:
        achievement = TeamAchievement(
            team_id=team.id,
            name=qr_code.achievement_name,
            description=qr_code.description,
            event_id=qr_code.event_id,
            qr_code_id=qr_code.id,
            achieved_at=datetime.now()
        )
        db.add(achievement)
    
    db.commit()
    
    # Return the success page with appropriate information
    return templates.TemplateResponse(
        "redeem_success.html",
        {
            "request": request,
            "points": qr_code.points,
            "achievement": qr_code.achievement_name if qr_code.achievement_name else None,
            "team": team,
            "event": qr_code.event if qr_code.event else None,
            "base_url": BASE_URL,
            "user": user  # Add user to the context
        }
    )

@router.post("/manual")
async def manual_code_entry(
    request: Request,
    code: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Handle manual code entry from the form.
    This redirects to the normal redeem flow after validating the code.
    """
    # Get user from session for navbar
    user = None
    user_id = request.session.get("user_id")
    if user_id:
        user = db.query(User).get(user_id)
    
    # Check if the code exists
    qr_code = db.query(QRCode).filter_by(code=code).first()
    
    if not qr_code:
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "error_title": "Invalid Code",
                "error_message": "The code you entered is invalid or does not exist.",
                "user": user  # Add user to the context
            }
        )
    
    # Check if already used (for single-use codes)
    if qr_code.used and (not qr_code.max_uses or qr_code.max_uses <= 1):
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "error_title": "Code Already Used",
                "error_message": "This code has already been redeemed.",
                "user": user  # Add user to the context
            }
        )
    
    # Redirect to the regular redeem flow
    return RedirectResponse(f"/redeem/{code}", status_code=303)
