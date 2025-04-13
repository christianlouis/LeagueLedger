#!/usr/bin/env python3
"""
Admin interface for managing database records.
"""
from fastapi import APIRouter, Depends, Request, Form, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import inspect
import json
from typing import Dict, Any, List, Type, Optional
import inspect as py_inspect

from ..db import SessionLocal, Base
from ..models import User, Team, TeamMembership, QRTicket
from ..templates_config import templates
from ..auth import require_admin

router = APIRouter()

# Dictionary of model classes with their display names
MODELS = {
    'user': (User, "Users"),
    'team': (Team, "Teams"),
    'team_membership': (TeamMembership, "Team Memberships"),
    'qr_ticket': (QRTicket, "QR Tickets"),
}

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

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
@require_admin
async def admin_home(request: Request):
    """Admin dashboard home."""
    model_list = [(key, name) for key, (_, name) in MODELS.items()]
    return templates.TemplateResponse(
        "admin/index.html", 
        {"request": request, "models": model_list}
    )

@router.get("/{model_name}", response_class=HTMLResponse)
@require_admin
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
        }
    )

@router.get("/{model_name}/new", response_class=HTMLResponse)
@require_admin
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
            "is_new": True
        }
    )

@router.post("/{model_name}/new")
@require_admin
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
@require_admin
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
            "is_new": False
        }
    )

@router.post("/{model_name}/{record_id}")
@require_admin
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
@require_admin
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
