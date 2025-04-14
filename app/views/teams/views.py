"""Team-related view functions for rendering templates"""
from fastapi import Request, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
import random
from sqlalchemy import inspect

from ...models import Team, TeamMembership, User, QRCode, TeamJoinRequest
from ...templates_config import templates
from ...utils.auth import get_current_user
from . import utils

def list_teams_view(request: Request, db: Session):
    """Render the teams list view"""
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

async def join_team_page_view(request: Request, team_id: int, db: Session):
    """Render the join team page"""
    user_id = request.session.get("user_id")
    current_user = db.query(User).get(user_id) if user_id else None
    
    if not current_user:
        return RedirectResponse(f"/auth/login?next=/teams/{team_id}/join", status_code=303)
    
    # Check if team exists
    team = db.query(Team).filter(Team.id == team_id, Team.is_active == True).first()
    if not team:
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "error": "Team not found"}
        )
    
    # Check if user is already a member
    existing_membership = db.query(TeamMembership).filter(
        TeamMembership.team_id == team_id, 
        TeamMembership.user_id == current_user.id
    ).first()
    
    if existing_membership:
        return templates.TemplateResponse(
            "teams/join_team.html",
            {
                "request": request, 
                "team": team, 
                "error": "You are already a member of this team"
            }
        )
    
    # Check if there's a pending join request
    pending_request = db.query(TeamJoinRequest).filter(
        TeamJoinRequest.team_id == team_id,
        TeamJoinRequest.user_id == current_user.id,
        TeamJoinRequest.status == "pending"
    ).first()
    
    if pending_request:
        return templates.TemplateResponse(
            "teams/join_team.html",
            {
                "request": request, 
                "team": team, 
                "error": "You already have a pending join request for this team"
            }
        )
    
    return templates.TemplateResponse(
        "teams/join_team.html",
        {"request": request, "team": team, "is_open": team.is_open}
    )

def team_detail_view(request: Request, team_id: int, db: Session):
    """Render the team detail page"""
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
    
    # Get team members with user info
    team_members = utils.get_team_members_with_details(db, team_id)
    
    # Check if user is admin or owner
    is_user_admin, is_user_owner, is_captain = utils.check_user_permissions(db, user, team_id, team)
    
    # Get team statistics
    total_points = utils.get_team_total_points(db, team_id)
    team_rank = utils.calculate_team_rank(db, team_id)
    points_this_month, point_change, point_change_positive = utils.get_team_points_history(db, team_id)
    
    # Activities - simple mock data for now
    activities = utils.get_team_activities()
    
    # Get team metadata
    days_ago, founded_date_str = utils.get_team_age(team)
    
    # Performance metrics
    performance = {
        "last_quiz": "25 points (2nd place)",
        "average": "18.7 points",
        "best_streak": "3 wins in a row"
    }
    
    # Safely get team attributes
    is_public = getattr(team, 'is_public', False)
    is_open = getattr(team, 'is_open', False)
    
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
            "is_captain": is_captain,
            "days_ago": days_ago,
            "founded_date": founded_date_str,
            "user": user,
            "is_open": is_open
        }
    )
