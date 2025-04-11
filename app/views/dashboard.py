#!/usr/bin/env python3
"""
Dashboard views for user-specific information.
"""
from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..db import SessionLocal
from ..models import User, Team, TeamMembership, QRTicket
from ..templates_config import templates

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_or_create_default_user(db: Session):
    """Get user ID 1 or create it if it doesn't exist."""
    user = db.query(User).filter_by(id=1).first()
    if not user:
        # Create a default user
        user = User(
            username="default_user",
            email="default@example.com",
            hashed_password="placeholder"
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user

@router.get("/", response_class=HTMLResponse)
async def user_dashboard(
    request: Request,
    db: Session = Depends(get_db)
):
    """Show the user's dashboard with team info and recent activity."""
    
    # Get current user - using a default user for now
    # In a real app, this would come from auth system
    user = get_or_create_default_user(db)
    
    # Get user's teams
    user_teams = db.query(Team).join(
        TeamMembership,
        TeamMembership.team_id == Team.id
    ).filter(
        TeamMembership.user_id == user.id
    ).all()
    
    # Get team memberships with admin status
    team_memberships = db.query(
        TeamMembership
    ).filter(
        TeamMembership.user_id == user.id
    ).all()
    
    admin_team_ids = [tm.team_id for tm in team_memberships if tm.is_admin]
    
    # Get points per team
    team_points = {}
    for team in user_teams:
        points = db.query(func.sum(QRTicket.points)).filter(
            QRTicket.redeemed_at_team == team.id
        ).scalar() or 0
        
        # Get team ranking - simplified approach
        higher_teams = db.query(func.count(Team.id)).join(
            QRTicket,
            QRTicket.redeemed_at_team == Team.id
        ).group_by(
            Team.id
        ).having(
            func.sum(QRTicket.points) > points
        ).scalar() or 0
        
        rank = higher_teams + 1
        
        team_points[team.id] = {
            'points': points,
            'rank': rank
        }
    
    # Get recent activity
    # For simplicity, we're just getting recent QR code redemptions
    recent_activity = []
    
    recent_tickets = db.query(QRTicket).filter(
        QRTicket.redeemed_by == user.id
    ).order_by(
        QRTicket.id.desc()  # Assuming higher ID = newer
    ).limit(5).all()
    
    for ticket in recent_tickets:
        team = db.query(Team).filter(Team.id == ticket.redeemed_at_team).first()
        activity = {
            'type': 'qr_redeem',
            'points': ticket.points,
            'team_name': team.name if team else "Unknown team",
            'date': "Recently"  # Placeholder - would use ticket.created_at
        }
        recent_activity.append(activity)
    
    # Get total points for user across all teams
    total_points = sum(team_data['points'] for team_data in team_points.values())
    
    # Get best ranking
    best_rank = min(team_data['rank'] for team_data in team_points.values()) if team_points else None
    
    return templates.TemplateResponse(
        "dashboard.html", 
        {
            "request": request,
            "user": user,
            "teams": user_teams,
            "team_points": team_points,
            "admin_team_ids": admin_team_ids,
            "recent_activity": recent_activity,
            "total_points": total_points,
            "best_rank": best_rank,
            "team_count": len(user_teams)
        }
    )

@router.get("/scan", response_class=HTMLResponse)
async def scan_qr(request: Request):
    """Show QR scanning interface."""
    return templates.TemplateResponse(
        "scan_qr.html", 
        {"request": request}
    )
