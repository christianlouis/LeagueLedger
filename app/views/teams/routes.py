from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from ...db import SessionLocal, get_db
from . import views, actions
from ...auth.utils import get_current_user_from_session

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Main routes for teams
@router.get("/", response_class=HTMLResponse)
def list_teams(request: Request, db: Session = Depends(get_db)):
    """List all available teams"""
    # No need to explicitly get current user - it's in request.state.user 
    # from middleware and will be passed to the template
    return views.list_teams_view(request, db)

@router.get("/{team_id}", response_class=HTMLResponse)
def team_detail(request: Request, team_id: int, db: Session = Depends(get_db)):
    """Show details for a specific team."""
    # User is already available in request.state.user
    return views.team_detail_view(request, team_id, db)

@router.get("/{team_id}/join", response_class=HTMLResponse)
async def join_team_page(request: Request, team_id: int, db: Session = Depends(get_db)):
    """Page for joining a team"""
    # User is already available in request.state.user
    return await views.join_team_page_view(request, team_id, db)

# Action routes
router.add_api_route("/create", actions.create_team_post, methods=["POST"], response_class=HTMLResponse)
router.add_api_route("/{team_id}/edit", actions.edit_team_post, methods=["POST"], response_class=HTMLResponse)
router.add_api_route("/{team_id}/join", actions.join_team_request, methods=["POST"], response_class=HTMLResponse)
router.add_api_route("/join/{team_id}", actions.direct_join_team, methods=["POST"])
router.add_api_route("/{team_id}/leave", actions.leave_team, methods=["POST"])
router.add_api_route("/{team_id}/update", actions.update_team, methods=["POST"])

# Add these new routes for handling join requests
@router.get("/approve-request/{token}", response_class=HTMLResponse)
async def approve_join_request(request: Request, token: str, db: Session = Depends(get_db)):
    """Approve a team join request using the provided token"""
    # User is already available in request.state.user
    return await actions.approve_join_request(request, token, db)

@router.get("/deny-request/{token}", response_class=HTMLResponse)
async def deny_join_request(request: Request, token: str, db: Session = Depends(get_db)):
    """Deny a team join request using the provided token"""
    # User is already available in request.state.user
    return await actions.deny_join_request(request, token, db)
