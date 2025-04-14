#!/usr/bin/env python3
"""
Teams management for users and admins.
"""
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, inspect
from datetime import datetime, timedelta
import random  # For demo data

from ..db import SessionLocal
from ..models import Team, TeamMembership, User, QRCode, TeamAchievement, TeamMember
from ..schemas import TeamCreate
from ..templates_config import templates

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/", response_class=HTMLResponse)
def list_teams(request: Request, db: Session = Depends(get_db)):
    teams = db.query(Team).all()
    
    # Get the user's teams to highlight teams they're already in
    user_team_ids = []
    
    # Get user from session for navbar
    user = None
    user_id = request.session.get("user_id")
    if user_id:
        user = db.query(User).get(user_id)
        # Get teams that user is a member of
        memberships = db.query(TeamMembership).filter(TeamMembership.user_id == user_id).all()
        user_team_ids = [membership.team_id for membership in memberships]
    
    # Get error message if present
    error = request.query_params.get("error")
    
    return templates.TemplateResponse(
        "teams.html", 
        {
            "request": request, 
            "teams": teams,
            "user_team_ids": user_team_ids,
            "user": user,
            "error": error,
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
def create_team(request: Request, name: str = Form(...), db: Session = Depends(get_db)):
    # Check if user is logged in
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/auth/login?next=/teams", status_code=303)
    
    # Get the user
    user = db.query(User).get(user_id)
    if not user:
        return RedirectResponse("/auth/login", status_code=303)
    
    # Check if team name already exists
    existing_team = db.query(Team).filter(Team.name == name).first()
    if existing_team:
        # Return to teams page with error message
        # In a real app, you'd add error handling/flash messages
        return RedirectResponse("/teams/?error=Team+name+already+exists", status_code=303)
    
    # Create team with the user as owner
    new_team = Team(name=name, owner_id=user_id)
    db.add(new_team)
    db.commit()
    db.refresh(new_team)
    
    # Make the user an admin of the team in TeamMembership
    team_membership = TeamMembership(
        user_id=user_id,
        team_id=new_team.id,
        is_admin=True  # User becomes admin of the team
    )
    db.add(team_membership)
    
    # Check if TeamMember model exists in the database
    try:
        # Use a safer approach to check if the model exists and is usable
        if 'team_members' in inspect(db.bind).get_table_names():
            # Create TeamMember relationship as well
            team_member = TeamMember(
                user_id=user_id,
                team_id=new_team.id,
                is_captain=True  # User becomes captain in TeamMember model
            )
            db.add(team_member)
    except Exception as e:
        print(f"Could not create TeamMember record: {str(e)}")
        # Continue even if this fails - TeamMembership is primary relationship
    
    db.commit()

    return RedirectResponse("/teams/", status_code=303)

@router.post("/join/{team_id}")
def join_team(request: Request, team_id: int, db: Session = Depends(get_db)):
    # Check if user is logged in
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/auth/login?next=/teams", status_code=303)
        
    # Get user
    user = db.query(User).get(user_id)
    if not user:
        return RedirectResponse("/auth/login", status_code=303)
    
    # Find the team
    team = db.query(Team).filter_by(id=team_id).first()
    if not team:
        return RedirectResponse("/teams/?error=Team+not+found", status_code=303)

    # Check if membership exists
    existing = db.query(TeamMembership)\
        .filter_by(user_id=user_id, team_id=team.id)\
        .first()
        
    if existing:
        return RedirectResponse("/teams/?error=You+are+already+a+member+of+this+team", status_code=303)

    # Create membership
    new_member = TeamMembership(
        user_id=user_id,
        team_id=team.id,
        is_admin=False
    )
    db.add(new_member)
    db.commit()
    
    # Redirect to the team detail page
    return RedirectResponse(f"/teams/{team_id}", status_code=303)

@router.post("/{team_id}/leave")
def leave_team(request: Request, team_id: int, db: Session = Depends(get_db)):
    """Allow a user to leave a team"""
    # Check if user is logged in
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/auth/login?next=/teams", status_code=303)
        
    # Get team
    team = db.query(Team).filter_by(id=team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    # Can't leave if you're the owner
    if team.owner_id == user_id:
        return RedirectResponse(f"/teams/{team_id}?error=Team+owner+cannot+leave", status_code=303)
    
    # Find membership
    membership = db.query(TeamMembership)\
        .filter(TeamMembership.user_id == user_id, TeamMembership.team_id == team_id)\
        .first()
        
    if not membership:
        return RedirectResponse("/teams/?error=You+are+not+a+member+of+this+team", status_code=303)
    
    # Delete the team membership
    db.delete(membership)
    db.commit()
    
    return RedirectResponse("/teams/?message=Successfully+left+the+team", status_code=303)

@router.post("/{team_id}/update")
def update_team(
    request: Request,
    team_id: int, 
    team_name: str = Form(...), 
    is_public: bool = Form(False),
    db: Session = Depends(get_db)
):
    """Update team details."""
    team = db.query(Team).filter_by(id=team_id).first()
    
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    # Check if user is admin
    membership = db.query(TeamMembership).filter_by(
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

@router.get("/{team_id}", response_class=HTMLResponse)
def team_detail(request: Request, team_id: int, db: Session = Depends(get_db)):
    """Show details for a specific team."""
    # Get team
    team = db.query(Team).filter_by(id=team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    # Get user from session for navbar
    user = None
    user_id = request.session.get("user_id")
    is_team_member = False
    
    if user_id:
        user = db.query(User).get(user_id)
        
        # Check if user is a team member
        team_membership = db.query(TeamMembership)\
            .filter(TeamMembership.user_id == user_id, TeamMembership.team_id == team_id)\
            .first()
        
        is_team_member = team_membership is not None
    
    # Get team members with admin status
    memberships = db.query(TeamMembership).filter_by(team_id=team_id).all()
    team_members = []
    
    is_user_admin = False
    for membership in memberships:
        member = db.query(User).filter_by(id=membership.user_id).first()
        if member:
            # Check if current user is admin of this team
            if user and user.id == membership.user_id and membership.is_admin:
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
    
    # Also check if user is the owner
    is_user_owner = user and team.owner_id == user.id
    if is_user_owner:
        is_user_admin = True  # Owner has admin privileges
    
    # Get total points
    total_points = db.query(func.sum(QRCode.points)).filter(
        QRCode.redeemed_at_team == team_id
    ).scalar() or 0
    
    # Calculate rank based on points - using a safer approach
    try:
        # First, get the aggregated points for all teams
        team_points = db.query(
            QRCode.redeemed_at_team, 
            func.sum(QRCode.points).label('total')
        ).filter(
            QRCode.redeemed_at_team != None
        ).group_by(QRCode.redeemed_at_team).all()
        
        # Sort them by points (descending)
        sorted_teams = sorted(team_points, key=lambda x: x.total or 0, reverse=True)
        
        # Find our team's position
        team_rank = 1
        for idx, team_data in enumerate(sorted_teams):
            if team_data.redeemed_at_team == team_id:
                team_rank = idx + 1
                break
            
    except Exception as e:
        print(f"Error calculating team rank: {e}")
        team_rank = 1  # Default to 1st place on error
    
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
        if 'redeemed_at' in [col['name'] for col in inspector.get_columns('qr_codes')]:
            has_redeemed_at = True
            
        if has_redeemed_at:
            points_this_month = db.query(func.sum(QRCode.points)).filter(
                QRCode.redeemed_at_team == team_id,
                QRCode.redeemed_at >= first_day_of_month
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
            "is_user_owner": is_user_owner,
            "is_team_member": is_team_member,
            "days_ago": days_ago,
            "founded_date": founded_date_str,
            "user": user  # Add user to the context
        }
    )
