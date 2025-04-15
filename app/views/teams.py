#!/usr/bin/env python3
"""
Teams management for users and admins.
"""
from fastapi import APIRouter, Depends, Request, Form, HTTPException, status, BackgroundTasks
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, inspect, or_, and_
from datetime import datetime, timedelta
import random  # For demo data
import secrets
from starlette.status import HTTP_303_SEE_OTHER
from starlette.middleware.sessions import SessionMiddleware

from ..db import SessionLocal, get_db
from ..models import Team, TeamMembership, User, QRCode, TeamAchievement, TeamMember, TeamJoinRequest
from ..schemas import TeamCreate
from ..templates_config import templates
from ..utils.auth import get_current_user, is_team_captain
from ..utils.mail import send_team_join_request_notification, send_join_request_response
from ..auth.permissions import require_auth, require_team_captain

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

@router.post("/create", response_class=HTMLResponse)
async def create_team_post(
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    logo_url: str = Form(""),
    is_open: bool = Form(False),  # Added is_open field
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Handle team creation form submission"""
    if not current_user:
        return RedirectResponse("/auth/login", status_code=HTTP_303_SEE_OTHER)
    
    # Check if team name already exists
    existing_team = db.query(Team).filter(Team.name == name).first()
    if existing_team:
        return RedirectResponse("/teams/?error=Team+name+already+exists", status_code=HTTP_303_SEE_OTHER)
    
    # Create team
    team = Team(
        name=name,
        description=description,
        logo_url=logo_url,
        is_open=is_open  # Save is_open value
    )
    db.add(team)
    db.commit()
    db.refresh(team)
    
    # Make the user an admin of the team in TeamMembership
    team_membership = TeamMembership(
        user_id=current_user.id,
        team_id=team.id,
        is_admin=True  # User becomes admin of the team
    )
    db.add(team_membership)
    
    # Create TeamMember relationship as well
    team_member = TeamMember(
        user_id=current_user.id,
        team_id=team.id,
        is_captain=True  # Use is_captain instead of role
    )
    db.add(team_member)
    
    db.commit()

    return RedirectResponse("/teams/", status_code=HTTP_303_SEE_OTHER)

@router.post("/teams/{team_id}/edit", response_class=HTMLResponse)
async def edit_team_post(
    request: Request,
    team_id: int,
    name: str = Form(...),
    description: str = Form(""),
    logo_url: str = Form(""),
    is_open: bool = Form(False),  # Added is_open field
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Handle team edit form submission"""
    if not current_user:
        return RedirectResponse("/auth/login", status_code=HTTP_303_SEE_OTHER)
    
    team = db.query(Team).filter(Team.id == team_id).first()
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
    team.name = name
    team.description = description
    team.logo_url = logo_url
    team.is_open = is_open  # Update is_open value
    db.commit()
    
    return RedirectResponse(f"/teams/{team_id}", status_code=HTTP_303_SEE_OTHER)

@router.get("/{team_id}/join", response_class=HTMLResponse)
async def join_team_page(
    request: Request,
    team_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Page for joining a team"""
    if not current_user:
        return RedirectResponse(f"/auth/login?next=/teams/{team_id}/join", status_code=HTTP_303_SEE_OTHER)
    
    # Check if team exists
    team = db.query(Team).filter(Team.id == team_id, Team.is_active == True).first()
    if not team:
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "error": "Team not found"}
        )
    
    # Check if user is already a member
    existing_membership = db.query(TeamMember).filter(
        TeamMember.team_id == team_id, 
        TeamMember.user_id == current_user.id
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

@router.post("/{team_id}/join", response_class=HTMLResponse)
async def join_team_request(
    request: Request,
    team_id: int,
    background_tasks: BackgroundTasks,
    message: str = Form(""),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Process join team request"""
    if not current_user:
        return RedirectResponse("/auth/login", status_code=HTTP_303_SEE_OTHER)
    
    # Check if team exists
    team = db.query(Team).filter(Team.id == team_id, Team.is_active == True).first()
    if not team:
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "error": "Team not found"}
        )
    
    # Check if user is already a member
    existing_membership = db.query(TeamMember).filter(
        TeamMember.team_id == team_id, 
        TeamMember.user_id == current_user.id
    ).first()
    
    if existing_membership:
        return RedirectResponse(f"/teams/{team_id}", status_code=HTTP_303_SEE_OTHER)
    
    # Open team - directly add the user
    if team.is_open:
        # Add user to team
        new_member = TeamMember(
            team_id=team_id,
            user_id=current_user.id,
            is_captain=False  # Use is_captain instead of role
        )
        
        db.add(new_member)
        db.commit()
        
        return RedirectResponse(
            f"/teams/{team_id}?message=You+have+joined+the+team+successfully", 
            status_code=HTTP_303_SEE_OTHER
        )
    
    # Closed team - create join request
    # Check for existing pending request
    existing_request = db.query(TeamJoinRequest).filter(
        TeamJoinRequest.team_id == team_id,
        TeamJoinRequest.user_id == current_user.id,
        TeamJoinRequest.status == "pending"
    ).first()
    
    if existing_request:
        return RedirectResponse(
            f"/teams/{team_id}?message=Your+join+request+is+pending+approval", 
            status_code=HTTP_303_SEE_OTHER
        )
    
    # Create request token
    request_token = secrets.token_urlsafe(32)
    
    # Create join request
    join_request = TeamJoinRequest(
        team_id=team_id,
        user_id=current_user.id,
        message=message,
        request_token=request_token
    )
    
    db.add(join_request)
    db.commit()
    
    # Get team captains to notify
    captains = db.query(User).join(TeamMember).filter(
        TeamMember.team_id == team_id,
        TeamMember.is_captain == True  # Use is_captain instead of role
    ).all()
    
    if not captains:
        print("No captains found for the team. Unable to send notifications.")
    else:
        # Send email notifications to all captains
        for captain in captains:
            try:
                await send_team_join_request_notification(
                    captain_email=captain.email,
                    captain_name=captain.username,
                    requester_name=current_user.username,
                    team_name=team.name,
                    message=message,
                    approval_token=request_token,
                    background_tasks=background_tasks
                )
                # Log success
                print(f"Team join request notification sent to {captain.email}")
            except Exception as e:
                # Log the error but continue
                print(f"Failed to send notification to {captain.email}: {str(e)}")
    
    return RedirectResponse(
        f"/teams/{team_id}?message=Your+join+request+has+been+submitted+for+approval", 
        status_code=HTTP_303_SEE_OTHER
    )

@router.post("/join/{team_id}")
def direct_join_team(request: Request, team_id: int, db: Session = Depends(get_db)):
    """Handle direct team join requests"""
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
    
    # Check if team is closed (not open)
    if not team.is_open:
        # For closed teams, redirect to the join request page
        return RedirectResponse(f"/teams/{team_id}/join", status_code=303)

    # Create membership for open teams
    new_member = TeamMembership(
        user_id=user_id,
        team_id=team.id,
        is_admin=False
    )
    db.add(new_member)
    
    # Also create TeamMember record for consistency
    team_member = TeamMember(
        user_id=user_id,
        team_id=team.id,
        is_captain=False  # Use is_captain instead of role
    )
    db.add(team_member)
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
    is_open = getattr(team, 'is_open', False)  # Add this line to get is_open status
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
            "user": user,  # Add user to the context
            "is_open": is_open  # Pass is_open to the template
        }
    )

@router.get("/{team_id}/manage", response_class=HTMLResponse)
@require_team_captain()
async def manage_team(request: Request, team_id: int, db: Session = Depends(get_db)):
    """
    Team management page for captains.
    This route is protected by the require_team_captain decorator which
    automatically checks if the user is a captain of the team.
    """
    # Get team
    team = db.query(Team).filter_by(id=team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    # Get pending join requests
    join_requests = db.query(TeamJoinRequest).filter(
        TeamJoinRequest.team_id == team_id,
        TeamJoinRequest.status == "pending"
    ).all()
    
    # Get requesters' info
    pending_requests = []
    for req in join_requests:
        requester = db.query(User).filter(User.id == req.user_id).first()
        if requester:
            pending_requests.append({
                "request": req,
                "user": requester
            })
    
    # Get team members
    memberships = db.query(TeamMembership).filter_by(team_id=team_id).all()
    team_members = []
    
    for membership in memberships:
        member = db.query(User).filter_by(id=membership.user_id).first()
        if member:
            team_members.append({
                "user": member,
                "is_admin": membership.is_admin,
                "is_captain": membership.is_captain
            })
    
    # Get current user from session for template
    current_user = None
    if hasattr(request, "session") and request.session.get("user_id"):
        current_user = db.query(User).filter_by(id=request.session.get("user_id")).first()
    
    return templates.TemplateResponse(
        "teams/manage.html",
        {
            "request": request,
            "team": team,
            "pending_requests": pending_requests,
            "team_members": team_members,
            "user": current_user  # Use current user from session instead of request.user
        }
    )
