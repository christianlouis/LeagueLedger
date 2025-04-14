#!/usr/bin/env python3
"""
Leaderboard views for displaying team rankings.
"""
from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import datetime, timedelta

from ..db import SessionLocal
from ..models import Team, TeamMembership, QRCode, User
from ..templates_config import templates

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/", response_class=HTMLResponse)
async def show_leaderboard(
    request: Request, 
    timeframe: str = Query("all", regex="^(week|month|all)$"),
    db: Session = Depends(get_db)
):
    """Show the leaderboard with team rankings."""
    
    # Get user from session for navbar
    user = None
    user_id = request.session.get("user_id")
    if user_id:
        user = db.query(User).get(user_id)
    
    # Define cutoff date based on timeframe
    cutoff_date = None
    if timeframe == "week":
        cutoff_date = datetime.now() - timedelta(days=7)
        time_label = "This Week"
    elif timeframe == "month":
        cutoff_date = datetime.now() - timedelta(days=30)
        time_label = "This Month"
    else:
        timeframe = "all"  # Ensure valid value
        time_label = "All Time"

    # Base query to get teams
    query = db.query(
        Team.id,
        Team.name,
        func.coalesce(func.sum(QRCode.points), 0).label('total_points')
    ).join(
        QRCode,
        QRCode.redeemed_at_team == Team.id,
        isouter=True
    )
    
    # Apply time filter if needed
    if cutoff_date:
        # Filter by redeemed_at timestamp if available
        query = query.filter(QRCode.redeemed_at >= cutoff_date)
    
    # Group and order
    teams_ranking = query.group_by(Team.id).order_by(desc('total_points')).all()
    
    # Add ranks
    ranked_teams = []
    for idx, team in enumerate(teams_ranking):
        ranked_teams.append({
            'rank': idx + 1,
            'id': team.id,
            'name': team.name,
            'points': team.total_points,
            'change': 0  # Placeholder for rank change - would require historical data
        })
    
    # Get top 3 teams for podium display
    top_teams = ranked_teams[:3] if len(ranked_teams) >= 3 else ranked_teams + [None] * (3 - len(ranked_teams))

    return templates.TemplateResponse(
        "leaderboard.html", 
        {
            "request": request,
            "teams": ranked_teams,
            "top_teams": top_teams,
            "timeframe": timeframe,
            "time_label": time_label,
            "user": user  # Add user to the context
        }
    )
