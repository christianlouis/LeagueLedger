#!/usr/bin/env python3
"""
Redeem a QR code and attribute points to a team.
"""
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from ..db import SessionLocal
from ..models import QRTicket, User, Team, TeamMembership
from ..templates_config import templates

router = APIRouter()

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
    ticket = db.query(QRTicket).filter_by(code=code, used=False).first()
    if not ticket:
        return templates.TemplateResponse(
            "error.html", 
            {
                "request": request,
                "error_title": "Invalid Code",
                "error_message": "This code is invalid or has already been used."
            }
        )

    # Get all available teams
    all_teams = db.query(Team).all()

    return templates.TemplateResponse("redeem.html", {
        "request": request,
        "ticket": ticket,
        "user_teams": all_teams  # Now showing all teams
    })

@router.post("/apply/{code}")
async def apply_code(
    request: Request,
    code: str,
    db: Session = Depends(get_db)
):
    """
    Apply the QR code to a selected team (without authentication)
    """
    # Get form data
    form_data = await request.form()
    team_id = int(form_data.get("team_id", 0))
    
    if team_id <= 0:
        return templates.TemplateResponse(
            "error.html", 
            {
                "request": request,
                "error_title": "Team Selection Required",
                "error_message": "Please select a team to redeem this code."
            }
        )
    
    ticket = db.query(QRTicket).filter_by(code=code, used=False).first()
    if not ticket:
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "error_title": "Invalid Code",
                "error_message": "This code is invalid or has already been used."
            }
        )

    team = db.query(Team).filter_by(id=team_id).first()
    
    if not team:
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "error_title": "Team Not Found",
                "error_message": "The selected team could not be found."
            }
        )

    # Redeem without checking membership
    ticket.redeemed_at_team = team.id
    ticket.used = True
        
    # If we have redeemed_at column, update it
    if hasattr(ticket, 'redeemed_at'):
        from datetime import datetime
        ticket.redeemed_at = datetime.now()
            
    db.commit()
        
    # Redirect to success page or dashboard
    return templates.TemplateResponse(
        "redeem_success.html",
        {
            "request": request,
            "points": ticket.points,
            "team": team
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
    # Check if the code exists
    ticket = db.query(QRTicket).filter_by(code=code, used=False).first()
    
    if not ticket:
        # In a real app, add a flash message or error handling
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "error_title": "Invalid Code",
                "error_message": "The code you entered is invalid or has already been used."
            }
        )
    
    # Redirect to the regular redeem flow
    return RedirectResponse(f"/redeem/{code}", status_code=303)
