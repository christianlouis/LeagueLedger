"""Team-related actions for team management"""
from fastapi import Request, Depends, Form, HTTPException, BackgroundTasks
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
import secrets
from starlette.status import HTTP_303_SEE_OTHER
from fastapi.templating import Jinja2Templates

from ...models import Team, TeamMembership, User, TeamJoinRequest
from ...utils.auth import get_current_user
from ...utils.mail import send_team_join_request_notification, send_join_request_response
from ...templates_config import templates
from .routes import get_db
from . import utils

async def create_team_post(
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    logo_url: str = Form(""),
    is_open: bool = Form(False),
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
    
    # Create team with only the fields that exist in the model
    team_data = {
        "name": name,
        "description": description,
        "is_open": is_open,
        "owner_id": current_user.id
    }
    
    # Only add logo_url if it exists in the Team model
    from sqlalchemy import inspect
    team_columns = [c.key for c in inspect(Team).columns]
    if "logo_url" in team_columns:
        team_data["logo_url"] = logo_url
    
    team = Team(**team_data)
    db.add(team)
    db.commit()
    db.refresh(team)
    
    # Make the user an admin and captain of the team
    team_membership = TeamMembership(
        user_id=current_user.id,
        team_id=team.id,
        is_admin=True,
        is_captain=True
    )
    db.add(team_membership)
    db.commit()

    return RedirectResponse("/teams/", status_code=HTTP_303_SEE_OTHER)

async def edit_team_post(
    request: Request,
    team_id: int,
    name: str = Form(...),
    description: str = Form(""),
    logo_url: str = Form(""),
    is_open: bool = Form(False),
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
        user_id=current_user.id,
        is_admin=True
    ).first()
    
    if not membership:
        raise HTTPException(status_code=403, detail="You don't have permission to update this team")
    
    # Update team details
    team.name = name
    team.description = description
    team.logo_url = logo_url
    team.is_open = is_open
    db.commit()
    
    return RedirectResponse(f"/teams/{team_id}", status_code=HTTP_303_SEE_OTHER)

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
    existing_membership = db.query(TeamMembership).filter(
        TeamMembership.team_id == team_id, 
        TeamMembership.user_id == current_user.id
    ).first()
    
    if existing_membership:
        return RedirectResponse(f"/teams/{team_id}", status_code=HTTP_303_SEE_OTHER)
    
    # Open team - directly add the user
    if team.is_open:
        # Add user to team
        new_member = TeamMembership(
            team_id=team_id,
            user_id=current_user.id,
            is_admin=False,
            is_captain=False
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
    
    # Get team captains to notify - Updated to use TeamMembership instead of TeamMember
    captains = db.query(User).join(TeamMembership).filter(
        TeamMembership.team_id == team_id,
        TeamMembership.is_captain == True
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
        is_admin=False,
        is_captain=False
    )
    db.add(new_member)
    db.commit()
    
    # Redirect to the team detail page
    return RedirectResponse(f"/teams/{team_id}", status_code=303)

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
        user_id=request.session.get("user_id"),
        is_admin=True
    ).first()
    
    if not membership:
        raise HTTPException(status_code=403, detail="You don't have permission to update this team")
    
    # Update team details
    team.name = team_name
    team.is_public = is_public
    db.commit()
    
    return RedirectResponse(f"/teams/{team_id}", status_code=303)

async def approve_join_request(request: Request, token: str, db: Session = Depends(get_db)):
    """Approve a team join request using the provided token"""
    # Find the join request by token
    join_request = db.query(TeamJoinRequest).filter_by(request_token=token).first()
    
    if not join_request:
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "error": "Invalid or expired join request"}
        )
    
    if join_request.status != "pending":
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "error": "This request has already been processed"}
        )
    
    # Get the team
    team = db.query(Team).filter_by(id=join_request.team_id).first()
    if not team:
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "error": "Team not found"}
        )
    
    # Check if the user has permission to approve requests
    # Get user from session
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/auth/login", status_code=303)
    
    user = db.query(User).get(user_id)
    if not user:
        return RedirectResponse("/auth/login", status_code=303)
    
    # Check if user is admin, owner or captain
    is_user_admin, is_user_owner, is_captain = utils.check_user_permissions(db, user, join_request.team_id, team)
    
    if not (is_user_admin or is_user_owner or is_captain):
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "error": "You don't have permission to approve join requests"}
        )
    
    # Get the user who requested to join
    requester = db.query(User).filter_by(id=join_request.user_id).first()
    if not requester:
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "error": "Requesting user not found"}
        )
    
    # Check if user is already a member
    existing_membership = db.query(TeamMembership).filter(
        TeamMembership.team_id == join_request.team_id, 
        TeamMembership.user_id == join_request.user_id
    ).first()
    
    if existing_membership:
        # Update request status
        join_request.status = "approved"
        db.commit()
        
        return templates.TemplateResponse(
            "teams/request_processed.html",
            {
                "request": request,
                "message": f"{requester.username} is already a member of {team.name}",
                "team_id": team.id
            }
        )
    
    # Create team membership
    new_member = TeamMembership(
        team_id=join_request.team_id,
        user_id=join_request.user_id,
        is_admin=False,
        is_captain=False
    )
    db.add(new_member)
    
    # Update request status
    join_request.status = "approved"
    db.commit()
    
    # Send notification to the user (if email sending is available)
    try:
        background_tasks = BackgroundTasks()
        await send_join_request_response(
            user_email=requester.email,
            user_name=requester.username,
            team_name=team.name,
            approved=True,
            background_tasks=background_tasks
        )
    except Exception as e:
        print(f"Failed to send approval notification: {str(e)}")
    
    return templates.TemplateResponse(
        "teams/request_processed.html",
        {
            "request": request,
            "message": f"Successfully approved {requester.username}'s request to join {team.name}",
            "team_id": team.id
        }
    )

async def deny_join_request(request: Request, token: str, db: Session = Depends(get_db)):
    """Deny a team join request using the provided token"""
    # Find the join request by token
    join_request = db.query(TeamJoinRequest).filter_by(request_token=token).first()
    
    if not join_request:
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "error": "Invalid or expired join request"}
        )
    
    if join_request.status != "pending":
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "error": "This request has already been processed"}
        )
    
    # Get the team
    team = db.query(Team).filter_by(id=join_request.team_id).first()
    if not team:
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "error": "Team not found"}
        )
    
    # Check if the user has permission to deny requests
    # Get user from session
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/auth/login", status_code=303)
    
    user = db.query(User).get(user_id)
    if not user:
        return RedirectResponse("/auth/login", status_code=303)
    
    # Check if user is admin, owner or captain
    is_user_admin, is_user_owner, is_captain = utils.check_user_permissions(db, user, join_request.team_id, team)
    
    if not (is_user_admin or is_user_owner or is_captain):
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "error": "You don't have permission to deny join requests"}
        )
    
    # Get the user who requested to join
    requester = db.query(User).filter_by(id=join_request.user_id).first()
    if not requester:
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "error": "Requesting user not found"}
        )
    
    # Update request status
    join_request.status = "denied"
    db.commit()
    
    # Send notification to the user (if email sending is available)
    try:
        background_tasks = BackgroundTasks()
        await send_join_request_response(
            user_email=requester.email,
            user_name=requester.username,
            team_name=team.name,
            approved=False,
            background_tasks=background_tasks
        )
    except Exception as e:
        print(f"Failed to send denial notification: {str(e)}")
    
    return templates.TemplateResponse(
        "teams/request_processed.html",
        {
            "request": request,
            "message": f"Successfully denied {requester.username}'s request to join {team.name}",
            "team_id": team.id
        }
    )
