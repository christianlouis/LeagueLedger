#!/usr/bin/env python3
"""
Create or join a team, manage membership.
"""
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, inspect
from datetime import datetime, timedelta
import random  # For demo data

from ..db import SessionLocal
from ..models import Team, TeamMembership, User, QRTicket, TeamAchievement
from ..schemas import TeamCreate
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
def list_teams(request: Request, db: Session = Depends(get_db)):
    teams = db.query(Team).all()
    
    # Get the user's teams to highlight teams they're already in
    user = db.query(User).filter_by(id=1).first()
    user_team_ids = []
    
    if user:
        memberships = db.query(TeamMembership).filter_by(user_id=user.id).all()
        user_team_ids = [m.team_id for m in memberships]
    
    return templates.TemplateResponse(
        "teams.html", 
        {
            "request": request, 
            "teams": teams,
            "user_team_ids": user_team_ids,
            "brand_colors": {
                "irish_green": "#006837",
                "golden_ale": "#FFB400",
                "cream_white": "#F5F0E1",
                "black_stout": "#1A1A1A",
                "guinness_red": "#B22222"
            }
        }
    )

@router.post("/create")
def create_team(name: str = Form(...), db: Session = Depends(get_db)):
    user = get_or_create_default_user(db)
    
    # Create team
    new_team = Team(name=name)
    db.add(new_team)
    db.commit()
    db.refresh(new_team)

    # Make user admin of team
    membership = TeamMembership(user_id=user.id, team_id=new_team.id, is_admin=True)
    db.add(membership)
    db.commit()
    
    return RedirectResponse("/teams/", status_code=303)

@router.post("/join/{team_id}")
def join_team(team_id: int, db: Session = Depends(get_db)):
    user = get_or_create_default_user(db)
    
    team = db.query(Team).filter_by(id=team_id).first()
    if not team:
        return RedirectResponse("/teams/", status_code=303)

    # Check if membership exists
    existing = db.query(TeamMembership).filter_by(user_id=user.id, team_id=team.id).first()
    if existing:
        return RedirectResponse("/teams/", status_code=303)

    # Create membership
    new_member = TeamMembership(user_id=user.id, team_id=team.id, is_admin=False)
    db.add(new_member)
    db.commit()
    
    return RedirectResponse("/teams/", status_code=303)

@router.get("/{team_id}", response_class=HTMLResponse)
def team_detail(request: Request, team_id: int, db: Session = Depends(get_db)):
    """Show details for a specific team."""
    # Get team
    team = db.query(Team).filter_by(id=team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    # Get current user - using a default user for now
    user = get_or_create_default_user(db)
    
    # Get team members with admin status
    memberships = db.query(TeamMembership).filter_by(team_id=team_id).all()
    team_members = []
    
    is_user_admin = False
    for membership in memberships:
        member = db.query(User).filter_by(id=membership.user_id).first()
        if member:
            # Check if current user is admin
            if membership.user_id == user.id and membership.is_admin:
                is_user_admin = True
                
            # Use joined_at if available, otherwise use placeholder
            joined_date = getattr(membership, 'joined_at', None) or datetime.now() - timedelta(days=random.randint(30, 180))
            if isinstance(joined_date, datetime):
                month_name = joined_date.strftime("%b")
                year = joined_date.strftime("%Y")
            else:
                month_name = "Apr"
                year = "2023"
                
            team_members.append({
                "user": member,
                "is_admin": membership.is_admin,
                "joined": f"{month_name} {year}"
            })
    
    # Get total points
    total_points = db.query(func.sum(QRTicket.points)).filter(
        QRTicket.redeemed_at_team == team_id
    ).scalar() or 0
    
    # Calculate rank based on points
    higher_teams = db.query(func.count(Team.id)).join(
        QRTicket, 
        QRTicket.redeemed_at_team == Team.id, 
        isouter=True
    ).group_by(Team.id).having(
        func.sum(QRTicket.points) > total_points
    ).scalar() or 0
    
    team_rank = higher_teams + 1
    
    # Generate points data (with fallbacks for missing columns)
    points_this_month = 65  # Default value
    point_change = 15       # Default value
    point_change_positive = True
    
    # Check if redeemed_at column exists before using it
    try:
        now = datetime.now()
        first_day_of_month = datetime(now.year, now.month, 1)
        
        # Use raw SQL to check if column exists and get points
        has_redeemed_at = False
        inspector = inspect(db.bind)
        if 'redeemed_at' in [col['name'] for col in inspector.get_columns('qr_tickets')]:
            has_redeemed_at = True
            
        if has_redeemed_at:
            points_this_month = db.query(func.sum(QRTicket.points)).filter(
                QRTicket.redeemed_at_team == team_id,
                QRTicket.redeemed_at >= first_day_of_month
            ).scalar() or points_this_month
    except Exception as e:
        print(f"Error calculating monthly points: {e}")
    
    # Activities - simple mock data for now
    activities = [
        {
            "type": "points",
            "points": 15,
            "event": "Music Trivia Night",
            "date": "September 12, 2023"
        },
        {
            "type": "join",
            "user": "Robert Brown",
            "date": "July 28, 2023"
        },
        {
            "type": "achievement",
            "achievement": "1st place",
            "event": "History Night",
            "date": "July 15, 2023"
        },
        {
            "type": "points",
            "points": 20,
            "event": "Movie Trivia Night",
            "date": "July 1, 2023"
        }
    ]
    
    # Safely get team attributes
    is_public = getattr(team, 'is_public', False)
    created_at = getattr(team, 'created_at', None)
    
    # Calculate days since team was founded
    if created_at and isinstance(created_at, datetime):
        days_ago = (datetime.now() - created_at).days
        founded_date_str = created_at.strftime("%B %d, %Y")
    else:
        days_ago = 164  # Default fallback
        founded_date_str = "March 22, 2023"  # Default fallback
    
    # Performance metrics
    performance = {
        "last_quiz": "25 points (2nd place)",
        "average": "18.7 points",
        "best_streak": "3 wins in a row"
    }
    
    return templates.TemplateResponse(
        "team_detail.html",
        {
            "request": request,
            "team": team,
            "team_members": team_members,
            "team_rank": team_rank,
            "total_points": total_points,
            "points_this_month": points_this_month,
            "point_change": point_change,
            "point_change_positive": point_change_positive,
            "activities": activities,
            "performance": performance,
            "is_user_admin": is_user_admin,
            "user": user,
            "days_ago": days_ago,
            "founded_date": founded_date_str
        }
    )

@router.post("/{team_id}/update")
def update_team(
    team_id: int, 
    team_name: str = Form(...), 
    is_public: bool = Form(False),
    db: Session = Depends(get_db)
):
    """Update team details."""
    user = get_or_create_default_user(db)
    team = db.query(Team).filter_by(id=team_id).first()
    
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    # Check if user is admin
    membership = db.query(TeamMembership).filter_by(
        user_id=user.id, 
        team_id=team.id,
        is_admin=True
    ).first()
    
    if not membership:
        raise HTTPException(status_code=403, detail="You don't have permission to update this team")
    
    # Update team details
    team.name = team_name
    team.is_public = is_public
    db.commit()
    
    return RedirectResponse(f"/teams/{team_id}", status_code=303)
