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
    If not logged in, prompt them.
    """
    # In real app, you'd check user session or redirect to login
    ticket = db.query(QRTicket).filter_by(code=code, used=False).first()
    if not ticket:
        return "Invalid or already used code."

    # Skeleton: you'd get the user's teams from session user
    # For now, we mock a user ID = 1:
    user = db.query(User).filter_by(id=1).first()
    if not user:
        return "User not found. Please log in."

    # This is where you'd show the team selection or "create new team" UI
    user_teams = [m.team for m in user.memberships]

    return templates.TemplateResponse("redeem.html", {
        "request": request,
        "ticket": ticket,
        "user_teams": user_teams
    })

@router.post("/apply/{code}")
async def apply_code(
    request: Request,
    code: str,
    db: Session = Depends(get_db)
):
    """
    Apply the QR code to a selected team (if user is a member),
    or set to pending if user isn't a member yet.
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

    # For skeleton, assume user = 1
    user = db.query(User).filter_by(id=1).first()
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

    # Check membership
    membership = db.query(TeamMembership).filter_by(user_id=user.id, team_id=team.id).first()
    if membership:
        # Redeem
        ticket.redeemed_by = user.id
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
    else:
        # In real app, create a pending record or request flow
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "error_title": "Not a Team Member",
                "error_message": "You are not a member of this team. Please join the team first or select another team."
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
