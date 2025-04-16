#!/usr/bin/env python3
"""
Admin interface for managing database records.
"""
from fastapi import APIRouter, Depends, Request, Form, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import inspect, func, desc, text
import json
from typing import Dict, Any, List, Type, Optional
import inspect as py_inspect
from datetime import datetime, timedelta
import time
import os
import psutil
from dateutil.relativedelta import relativedelta

from ..db import SessionLocal, Base
from ..models import (
    User, Team, TeamMembership, QRCode, QRSet, TeamAchievement, Event, 
    OAuthAccount, TeamJoinRequest, EventAttendee, UserPoints
)
from ..templates_config import templates
from ..auth.permissions import require_admin

router = APIRouter()

# Dictionary of model classes with their display names
MODELS = {
    'user': (User, "Users"),
    'team': (Team, "Teams"),
    'team_membership': (TeamMembership, "Team Memberships"),
    'qr_code': (QRCode, "QR Codes"),
    'qr_set': (QRSet, "QR Sets"),
    'team_achievement': (TeamAchievement, "Team Achievements"),
    'event': (Event, "Events"),
    'oauth_account': (OAuthAccount, "OAuth Accounts"),
    'team_join_request': (TeamJoinRequest, "Team Join Requests"),
    'event_attendee': (EventAttendee, "Event Attendees"),
    'user_points': (UserPoints, "User Points"),
}

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Get user statistics for the dashboard
def get_user_statistics(db: Session) -> Dict[str, Any]:
    """Get user statistics for the admin dashboard."""
    stats = {}
    
    # Total users
    stats["total_users"] = db.query(User).count()
    
    # Active users (not disabled)
    stats["active_users"] = db.query(User).filter(User.is_active == True).count()
    
    # Verified users
    stats["verified_users"] = db.query(User).filter(User.is_verified == True).count()
    
    # Admin users
    stats["admin_users"] = db.query(User).filter(User.is_admin == True).count()
    
    # New registrations in the last 30 days
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    stats["new_registrations_30d"] = db.query(User).filter(
        User.created_at >= thirty_days_ago
    ).count()
    
    # Monthly user registration data for the chart (last 6 months)
    monthly_data = []
    month_labels = []
    
    # Get the current month and year
    current_date = datetime.now()
    
    # Loop through the last 6 months
    for i in range(5, -1, -1):
        # Calculate month and year for this data point
        month_date = current_date - relativedelta(months=i)
        start_of_month = datetime(month_date.year, month_date.month, 1)
        
        # For the current month, only count until today
        if i == 0:
            end_of_month = current_date
        else:
            # Calculate the end of the month
            if month_date.month == 12:
                end_of_month = datetime(month_date.year + 1, 1, 1) - timedelta(days=1)
            else:
                end_of_month = datetime(month_date.year, month_date.month + 1, 1) - timedelta(days=1)
        
        # Format month as abbreviated month name
        month_name = month_date.strftime('%b')
        month_labels.append(month_name)
        
        # Count users registered in this month
        monthly_count = db.query(User).filter(
            User.created_at >= start_of_month,
            User.created_at <= end_of_month
        ).count()
        
        monthly_data.append(monthly_count)
    
    # Add the data to the stats
    stats["monthly_registrations"] = monthly_data
    stats["month_labels"] = month_labels
    
    return stats

# Get team statistics for the dashboard
def get_team_statistics(db: Session) -> Dict[str, Any]:
    """Get team statistics for the admin dashboard."""
    stats = {}
    
    # Total teams
    stats["total_teams"] = db.query(Team).count()
    
    # Active teams
    stats["active_teams"] = db.query(Team).filter(Team.is_active == True).count()
    
    # Public teams
    stats["public_teams"] = db.query(Team).filter(Team.is_public == True).count()
    
    # Team size distribution - teams grouped by member count
    # Modified query to correctly count team members and group by team
    team_sizes = db.query(
        TeamMembership.team_id,
        func.count(TeamMembership.user_id).label('member_count')
    ).group_by(TeamMembership.team_id).subquery()
    
    # Now we can query the distribution from the subquery
    team_distribution = db.query(
        team_sizes.c.member_count,
        func.count().label('count')
    ).group_by(team_sizes.c.member_count).all()
    
    # Convert to a list of dictionaries for easier handling in the template
    team_dist_list = [{"member_count": size[0], "count": size[1]} for size in team_distribution]
    
    stats["team_distribution"] = team_dist_list
    
    return stats

# Get event statistics for the dashboard
def get_event_statistics(db: Session) -> Dict[str, Any]:
    """Get event statistics for the admin dashboard."""
    stats = {}
    
    # Total events
    stats["total_events"] = db.query(Event).count()
    
    # Past events
    today = datetime.now().date()
    stats["past_events"] = db.query(Event).filter(Event.event_date < today).count()
    
    # Upcoming events
    stats["upcoming_events_count"] = db.query(Event).filter(Event.event_date >= today).count()
    
    # List of upcoming events
    upcoming_events = db.query(Event).filter(
        Event.event_date >= today
    ).order_by(Event.event_date).limit(5).all()
    
    stats["upcoming_events"] = upcoming_events
    
    # Events with highest attendance
    attendance_rates = db.query(
        Event.id.label('event_id'),
        Event.name.label('event_name'),
        func.count(EventAttendee.id).label('attendee_count')
    ).join(EventAttendee).group_by(Event.id, Event.name).order_by(
        desc('attendee_count')
    ).limit(5).all()
    
    stats["attendance_rates"] = attendance_rates
    
    return stats

# Get system health information
def get_system_health(db: Session) -> Dict[str, Any]:
    """Get system health information for the admin dashboard."""
    health_info = {}
    
    # Database status
    try:
        result = db.execute(text("SELECT 'online' as status")).fetchall()
        health_info["database_status"] = "online" if result else "offline"
    except Exception as e:
        health_info["database_status"] = "error"
        health_info["database_error"] = str(e)
    
    # System uptime
    try:
        uptime_seconds = time.time() - psutil.boot_time()
        days, remainder = divmod(uptime_seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        health_info["uptime"] = f"{int(days)} days, {int(hours)} hours, {int(minutes)} minutes"
    except Exception:
        health_info["uptime"] = "Unknown"
    
    # Recent errors (would be fetched from a logging system in production)
    # For this example, we'll return a placeholder
    health_info["recent_errors"] = []
    
    return health_info

def get_model_info(model_class: Type[Base]) -> Dict[str, Dict[str, Any]]:
    """Get column information for a model."""
    mapper = inspect(model_class)
    columns = {}
    
    for column in mapper.columns:
        is_primary = column.primary_key
        is_foreign_key = bool(column.foreign_keys)
        foreign_key_target = None
        
        if is_foreign_key:
            for fk in column.foreign_keys:
                foreign_key_target = fk.target_fullname

        columns[column.name] = {
            'type': str(column.type),
            'nullable': column.nullable,
            'primary_key': is_primary,
            'foreign_key': is_foreign_key,
            'foreign_key_target': foreign_key_target,
        }
    
    return columns

def get_relationships(model_class: Type[Base]) -> Dict[str, str]:
    """Get relationship information for a model."""
    relationships = {}
    for name, rel in py_inspect.getmembers(model_class, lambda o: hasattr(o, 'prop')):
        if hasattr(rel.prop, 'target'):
            relationships[name] = rel.prop.target.name
    return relationships

@router.get("/", response_class=HTMLResponse)
@require_admin(redirect_url="/auth/login?next=/admin/")
async def admin_home(request: Request, db: Session = Depends(get_db)):
    """Admin dashboard home."""
    # Get statistics
    user_stats = get_user_statistics(db)
    team_stats = get_team_statistics(db)
    event_stats = get_event_statistics(db)
    system_health = get_system_health(db)
    
    return templates.TemplateResponse(
        "admin/dashboard.html", 
        {
            "request": request, 
            "user": request.user,
            "user_stats": user_stats,
            "team_stats": team_stats,
            "event_stats": event_stats,
            "system_health": system_health
        }
    )

@router.get("/models", response_class=HTMLResponse)
@require_admin(redirect_url="/auth/login?next=/admin/models")
async def admin_models(request: Request, db: Session = Depends(get_db)):
    """Admin models overview."""
    # Since we're using Starlette's authentication, the user is now available in request.user
    model_list = [(key, name) for key, (_, name) in MODELS.items()]
    return templates.TemplateResponse(
        "admin/index.html", 
        {"request": request, "models": model_list, "user": request.user}
    )

@router.get("/{model_name}", response_class=HTMLResponse)
@require_admin(redirect_url="/auth/login")
async def list_records(
    request: Request, 
    model_name: str, 
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=5, le=100),
    db: Session = Depends(get_db)
):
    """List records for a model with pagination."""
    if model_name not in MODELS:
        raise HTTPException(status_code=404, detail=f"Model {model_name} not found")
    
    model_class, display_name = MODELS[model_name]
    
    # Get total count for pagination
    total_records = db.query(model_class).count()
    total_pages = (total_records + per_page - 1) // per_page
    
    # Get records with pagination
    records = db.query(model_class).offset((page - 1) * per_page).limit(per_page).all()
    
    # Get column information
    columns_info = get_model_info(model_class)
    
    # Prepare column names for display
    column_names = list(columns_info.keys())
    
    # Extract values for each record
    records_data = []
    for record in records:
        record_data = {}
        for col in column_names:
            record_data[col] = getattr(record, col)
        records_data.append(record_data)
    
    return templates.TemplateResponse(
        "admin/list.html", 
        {
            "request": request, 
            "model_name": model_name,
            "display_name": display_name,
            "records": records_data,
            "columns": column_names,
            "columns_info": columns_info,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
            "total_records": total_records,
            "user": request.user  # Add user to the context
        }
    )

@router.get("/{model_name}/new", response_class=HTMLResponse)
@require_admin(redirect_url="/auth/login")
async def create_record_form(
    request: Request, 
    model_name: str,
    db: Session = Depends(get_db)
):
    """Show form for creating a new record."""
    if model_name not in MODELS:
        raise HTTPException(status_code=404, detail=f"Model {model_name} not found")
    
    model_class, display_name = MODELS[model_name]
    
    # Get column information
    columns_info = get_model_info(model_class)
    
    # For foreign keys, fetch possible values
    foreign_key_options = {}
    for col_name, info in columns_info.items():
        if info['foreign_key'] and info['foreign_key_target']:
            target_table, target_col = info['foreign_key_target'].split('.')
            # Try to find the corresponding model class
            for model_key, (model_cls, _) in MODELS.items():
                if model_cls.__tablename__ == target_table:
                    # Fetch options for this foreign key
                    options = db.query(model_cls).all()
                    foreign_key_options[col_name] = [(getattr(option, 'id'), str(option)) for option in options]
    
    return templates.TemplateResponse(
        "admin/edit.html", 
        {
            "request": request, 
            "model_name": model_name,
            "display_name": display_name,
            "columns_info": columns_info,
            "record": None,  # No record for new form
            "foreign_key_options": foreign_key_options,
            "is_new": True,
            "user": request.user  # Use request.user from Starlette authentication
        }
    )

@router.post("/{model_name}/new")
@require_admin(redirect_url="/auth/login")
async def create_record(
    request: Request,
    model_name: str,
    db: Session = Depends(get_db)
):
    """Create a new record."""
    if model_name not in MODELS:
        raise HTTPException(status_code=404, detail=f"Model {model_name} not found")
    
    model_class, _ = MODELS[model_name]
    
    # Get form data from request
    form_data = await request.form()
    
    # Convert form data to appropriate types
    columns_info = get_model_info(model_class)
    record_data = {}
    
    for field_name, value in form_data.items():
        if field_name in columns_info:
            col_type = columns_info[field_name]['type'].lower()
            
            # Skip empty values for nullable fields
            if value == '' and columns_info[field_name]['nullable']:
                continue
                
            # Convert values based on column type
            if 'int' in col_type:
                if value:
                    record_data[field_name] = int(value)
            elif 'bool' in col_type or 'boolean' in col_type:
                record_data[field_name] = value.lower() in ('true', 'yes', 'y', '1', 'on', 'checked')
            else:
                record_data[field_name] = value
    
    # Skip primary key for new records if it's auto-increment
    for col_name, info in columns_info.items():
        if info['primary_key'] and col_name not in record_data:
            pass  # Skip primary key
    
    # Create record
    new_record = model_class(**record_data)
    db.add(new_record)
    db.commit()
    
    return RedirectResponse(f"/admin/{model_name}", status_code=303)

@router.get("/{model_name}/{record_id}", response_class=HTMLResponse)
@require_admin(redirect_url="/auth/login")
async def edit_record_form(
    request: Request, 
    model_name: str,
    record_id: int,
    db: Session = Depends(get_db)
):
    """Show form for editing an existing record."""
    if model_name not in MODELS:
        raise HTTPException(status_code=404, detail=f"Model {model_name} not found")
    
    model_class, display_name = MODELS[model_name]
    
    # Get the record
    record = db.query(model_class).filter_by(id=record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail=f"Record not found")
    
    # Get column information
    columns_info = get_model_info(model_class)
    
    # For foreign keys, fetch possible values
    foreign_key_options = {}
    for col_name, info in columns_info.items():
        if info['foreign_key'] and info['foreign_key_target']:
            target_table, target_col = info['foreign_key_target'].split('.')
            # Try to find the corresponding model class
            for model_key, (model_cls, _) in MODELS.items():
                if model_cls.__tablename__ == target_table:
                    # Fetch options for this foreign key
                    options = db.query(model_cls).all()
                    foreign_key_options[col_name] = [(getattr(option, 'id'), str(option)) for option in options]
    
    # Prepare record data
    record_data = {}
    for col_name in columns_info:
        record_data[col_name] = getattr(record, col_name)
    
    return templates.TemplateResponse(
        "admin/edit.html", 
        {
            "request": request, 
            "model_name": model_name,
            "display_name": display_name,
            "columns_info": columns_info,
            "record": record_data,
            "foreign_key_options": foreign_key_options,
            "is_new": False,
            "user": request.user  # Use request.user from Starlette authentication
        }
    )

@router.post("/{model_name}/{record_id}")
@require_admin(redirect_url="/auth/login")
async def update_record(
    request: Request,
    model_name: str,
    record_id: int,
    db: Session = Depends(get_db)
):
    """Update an existing record."""
    if model_name not in MODELS:
        raise HTTPException(status_code=404, detail=f"Model {model_name} not found")
    
    model_class, _ = MODELS[model_name]
    
    # Get the record
    record = db.query(model_class).filter_by(id=record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail=f"Record not found")
    
    # Get form data from request
    form_data = await request.form()
    
    # Convert form data to appropriate types and update record
    columns_info = get_model_info(model_class)
    
    for field_name, value in form_data.items():
        if field_name in columns_info and not columns_info[field_name]['primary_key']:
            col_type = columns_info[field_name]['type'].lower()
            
            # Handle nullable fields
            if value == '' and columns_info[field_name]['nullable']:
                setattr(record, field_name, None)
                continue
                
            # Convert values based on column type
            if 'int' in col_type:
                if value:
                    setattr(record, field_name, int(value))
            elif 'bool' in col_type or 'boolean' in col_type:
                bool_value = value.lower() in ('true', 'yes', 'y', '1', 'on', 'checked')
                setattr(record, field_name, bool_value)
            else:
                setattr(record, field_name, value)
    
    # Save changes
    db.commit()
    
    return RedirectResponse(f"/admin/{model_name}", status_code=303)

@router.get("/{model_name}/{record_id}/delete")
@require_admin(redirect_url="/auth/login")
async def delete_record(
    request: Request,
    model_name: str,
    record_id: int,
    db: Session = Depends(get_db)
):
    """Delete a record."""
    if model_name not in MODELS:
        raise HTTPException(status_code=404, detail=f"Model {model_name} not found")
    
    model_class, _ = MODELS[model_name]
    
    # Get the record
    record = db.query(model_class).filter_by(id=record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail=f"Record not found")
    
    # Delete record
    db.delete(record)
    db.commit()
    
    return RedirectResponse(f"/admin/{model_name}", status_code=303)
