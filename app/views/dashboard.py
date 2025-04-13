#!/usr/bin/env python3
from fastapi import APIRouter, Request, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from fastapi.responses import HTMLResponse, RedirectResponse

from ..db import get_db
from ..templates_config import templates
from .. import models

router = APIRouter()

@router.get("/")
def user_dashboard(request: Request, db: Session = Depends(get_db)):
    """User dashboard showing teams, events and stats"""
    try:
        # Fetch user data directly from the database
        user = db.query(models.User).filter_by(email="admin@example.com").first()  # Example user lookup
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        user_id = user.id

        # Initialize default values in case of errors
        team_count = 0
        total_points = 0
        event_count = 0
        recent_events = []
        user_teams = []

        # Check if TeamMember model exists before querying
        if hasattr(models, "TeamMember"):
            # Get the team count for this user
            team_count = db.query(func.count(models.TeamMember.team_id))\
                .filter(models.TeamMember.user_id == user_id)\
                .scalar() or 0

            # Get user teams
            user_teams = db.query(models.Team)\
                .join(models.TeamMember)\
                .filter(models.TeamMember.user_id == user_id)\
                .all()

        # Check if UserPoints model exists before querying
        if hasattr(models, "UserPoints"):
            # Get the total points safely
            total_points_result = db.query(func.sum(models.UserPoints.points))\
                .filter(models.UserPoints.user_id == user_id)\
                .first()

            if total_points_result and total_points_result[0]:
                total_points = total_points_result[0]

        # Check if EventAttendee model exists before querying
        if hasattr(models, "EventAttendee") and hasattr(models, "Event"):
            # Get event count safely
            event_count_result = db.query(func.count(models.EventAttendee.event_id))\
                .filter(models.EventAttendee.user_id == user_id)\
                .first()

            if event_count_result and event_count_result[0]:
                event_count = event_count_result[0]

            # Recent events - only if both models exist
            recent_events = db.query(models.Event)\
                .join(models.EventAttendee)\
                .filter(models.EventAttendee.user_id == user_id)\
                .order_by(models.Event.event_date.desc())\
                .limit(5)\
                .all()

        return templates.TemplateResponse(
            "dashboard/index.html", 
            {
                "request": request,
                "user": user,
                "team_count": team_count,
                "total_points": total_points,
                "event_count": event_count,
                "recent_events": recent_events,
                "user_teams": user_teams
            }
        )
    except Exception as e:
        print(f"Dashboard error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Dashboard error: {str(e)}")

@router.get("/scan", response_class=HTMLResponse)
def scan_qr_page(request: Request):
    """Render the QR code scanning page."""
    return templates.TemplateResponse("scan_qr.html", {"request": request})
