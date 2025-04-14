#!/usr/bin/env python3
"""
Generate QR codes for top teams (quiz master).
"""
import qrcode
import io
import uuid
import os
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Request, Form, HTTPException, Query
from fastapi.responses import StreamingResponse, HTMLResponse, FileResponse
from sqlalchemy.orm import Session
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image as ReportLabImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib.enums import TA_CENTER
from pydantic import BaseModel

from ..db import SessionLocal
from ..models import QRCode, QRSet, Event
from ..templates_config import templates

router = APIRouter()

# Get base URL from environment variable or use default
BASE_URL = os.environ.get("LEAGUELEDGER_BASE_URL", "https://rover.leagueledger.net")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Models for request validation
class QRSetRequest(BaseModel):
    name: str
    description: Optional[str] = None


class QRCodeRequest(BaseModel):
    title: str
    points: float
    achievement_name: Optional[str] = None
    is_achievement_only: bool = False
    max_uses: Optional[int] = None
    description: Optional[str] = None


@router.get("/", response_class=HTMLResponse)
async def qr_dashboard(request: Request, db: Session = Depends(get_db)):
    """QR code management dashboard."""
    # Get all QR sets
    qr_sets = db.query(QRSet).all()
    
    # Get all events for linking
    events = db.query(Event).all()
    
    return templates.TemplateResponse("qr/dashboard.html", {
        "request": request,
        "qr_sets": qr_sets,
        "events": events
    })


@router.post("/sets")
async def create_qr_set(
    request: Request,
    db: Session = Depends(get_db)
):
    """Create a new QR set."""
    # Process form data
    form_data = await request.form()
    name = form_data.get("name")
    description = form_data.get("description", "")
    
    if not name:
        raise HTTPException(status_code=400, detail="Set name is required")
    
    # Create QR set
    qr_set = QRSet(name=name, description=description)
    db.add(qr_set)
    db.commit()
    db.refresh(qr_set)
    
    return {"id": qr_set.id, "name": qr_set.name, "message": f"QR Set '{name}' created successfully"}


@router.get("/sets/{set_id}", response_class=HTMLResponse)
async def view_qr_set(request: Request, set_id: int, db: Session = Depends(get_db)):
    """View details of a QR set."""
    qr_set = db.query(QRSet).filter(QRSet.id == set_id).first()
    if not qr_set:
        raise HTTPException(status_code=404, detail="QR Set not found")
    
    # Get all QR codes in this set
    qr_codes = db.query(QRCode).filter(QRCode.qr_set_id == set_id).all()
    
    return templates.TemplateResponse("qr/set_detail.html", {
        "request": request,
        "qr_set": qr_set,
        "qr_codes": qr_codes,
        "base_url": BASE_URL
    })


@router.post("/sets/{set_id}/codes")
async def add_qr_code_to_set(
    request: Request,
    set_id: int,
    db: Session = Depends(get_db)
):
    """Add a QR code to a set."""
    # Check if set exists
    qr_set = db.query(QRSet).filter(QRSet.id == set_id).first()
    if not qr_set:
        raise HTTPException(status_code=404, detail="QR Set not found")
    
    # Process form data
    form_data = await request.form()
    title = form_data.get("title")
    points = float(form_data.get("points", 0))
    achievement_name = form_data.get("achievement_name")
    is_achievement_only = form_data.get("is_achievement_only", "").lower() in ("true", "yes", "1", "on")
    description = form_data.get("description", "")
    
    # Generate a unique code
    code_str = str(uuid.uuid4())
    
    # Create QR code
    qr_code = QRCode(
        code=code_str,
        title=title,
        points=points,
        qr_set_id=set_id,
        achievement_name=achievement_name,
        is_achievement_only=is_achievement_only,
        description=description
    )
    
    db.add(qr_code)
    db.commit()
    db.refresh(qr_code)
    
    return {"id": qr_code.id, "code": code_str, "message": "QR Code added to set"}


@router.get("/generate/{points}")
def generate_qr(points: int, db: Session = Depends(get_db)):
    """
    Generate a single QR code for awarding `points` points. 
    Saves a record in the DB, returns the PNG as streaming response.
    """
    code_str = str(uuid.uuid4())

    qr_code = QRCode(code=code_str, points=points)
    db.add(qr_code)
    db.commit()
    db.refresh(qr_code)

    qr_img = qrcode.make(f"{BASE_URL}/redeem/{code_str}")
    buf = io.BytesIO()
    qr_img.save(buf, format="PNG")
    buf.seek(0)

    return StreamingResponse(buf, media_type="image/png")


@router.get("/code/{code}")
def get_qr_image(code: str):
    """
    Generate a QR code image from a code string without creating a database record.
    Useful for viewing existing codes.
    """
    qr_img = qrcode.make(f"{BASE_URL}/redeem/{code}")
    buf = io.BytesIO()
    qr_img.save(buf, format="PNG")
    buf.seek(0)

    return StreamingResponse(buf, media_type="image/png")


@router.get("/sets/{set_id}/generate-admin")
def generate_admin_qr(set_id: int, db: Session = Depends(get_db)):
    """Generate admin QR code for linking to events."""
    qr_set = db.query(QRSet).filter(QRSet.id == set_id).first()
    if not qr_set:
        raise HTTPException(status_code=404, detail="QR Set not found")
    
    # Create unique admin code
    admin_code = f"admin-{set_id}-{uuid.uuid4()}"
    
    # Generate QR code with special admin URL
    qr_img = qrcode.make(f"{BASE_URL}/qr/admin-link/{admin_code}")
    buf = io.BytesIO()
    qr_img.save(buf, format="PNG")
    buf.seek(0)
    
    return StreamingResponse(buf, media_type="image/png", 
                           headers={"Content-Disposition": f"inline; filename=admin-{set_id}.png"})


@router.get("/admin-link/{admin_code}", response_class=HTMLResponse)
async def admin_link_page(request: Request, admin_code: str, db: Session = Depends(get_db)):
    """Page for linking QR sets to events via admin code."""
    # Extract set_id from admin code
    try:
        set_id = int(admin_code.split("-")[1])
    except (IndexError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid admin code")
    
    qr_set = db.query(QRSet).filter(QRSet.id == set_id).first()
    if not qr_set:
        raise HTTPException(status_code=404, detail="QR Set not found")
    
    # Fetch available events
    events = db.query(Event).all()
    
    return templates.TemplateResponse("qr/admin_link.html", {
        "request": request,
        "qr_set": qr_set,
        "admin_code": admin_code,
        "events": events
    })


@router.post("/admin-link/{admin_code}")
async def process_admin_link(
    request: Request,
    admin_code: str,
    db: Session = Depends(get_db)
):
    """Process linking QR codes to an event."""
    # Extract set_id from admin code
    try:
        set_id = int(admin_code.split("-")[1])
    except (IndexError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid admin code")
    
    # Get form data
    form_data = await request.form()
    event_id = form_data.get("event_id")
    event_name = form_data.get("new_event_name")
    
    # If no event ID provided, create a new event with the given name
    if not event_id and event_name:
        # Create new event
        event_date = datetime.now()  # Default to current date, can be improved
        new_event = Event(
            name=event_name,
            description=f"Created via QR admin link on {event_date.strftime('%Y-%m-%d')}",
            event_date=event_date
        )
        db.add(new_event)
        db.commit()
        db.refresh(new_event)
        event_id = new_event.id
    
    if not event_id:
        raise HTTPException(status_code=400, detail="Event ID or new event name is required")
    
    # Update all QR codes in the set
    qr_codes = db.query(QRCode).filter(QRCode.qr_set_id == set_id).all()
    for qr_code in qr_codes:
        qr_code.event_id = event_id
    
    db.commit()
    
    return {"message": f"Successfully linked {len(qr_codes)} QR codes to event ID {event_id}"}


@router.get("/sets/{set_id}/pdf")
def generate_pdf(set_id: int, db: Session = Depends(get_db)):
    """
    Generate a PDF with QR codes for a set.
    """
    # Get QR set
    qr_set = db.query(QRSet).filter(QRSet.id == set_id).first()
    if not qr_set:
        raise HTTPException(status_code=404, detail="QR Set not found")
    
    # Get QR codes for this set
    qr_codes = db.query(QRCode).filter(QRCode.qr_set_id == set_id).all()
    if not qr_codes:
        raise HTTPException(status_code=404, detail="No QR codes found in this set")
    
    # Create PDF buffer
    buffer = io.BytesIO()
    
    # Create PDF document
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=A4,
        title=f"QR Codes - {qr_set.name}",
        rightMargin=1*cm, 
        leftMargin=1*cm,
        topMargin=1*cm, 
        bottomMargin=1*cm
    )
    
    # Container for elements
    elements = []
    
    # Add styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'TitleStyle', 
        parent=styles['Heading1'], 
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    subtitle_style = ParagraphStyle(
        'SubtitleStyle', 
        parent=styles['Heading2'], 
        alignment=TA_CENTER
    )
    code_style = ParagraphStyle(
        'CodeStyle', 
        parent=styles['Normal'], 
        alignment=TA_CENTER,
        fontName='Courier'
    )
    
    # Add title
    elements.append(Paragraph(f"QR Codes for {qr_set.name}", title_style))
    today = datetime.now().strftime('%Y-%m-%d')
    elements.append(Paragraph(f"Generated on {today}", subtitle_style))
    elements.append(Spacer(1, 0.5*inch))
    
    # Generate admin QR code
    admin_code = f"admin-{set_id}-{uuid.uuid4()}"
    admin_qr = qrcode.make(f"{BASE_URL}/qr/admin-link/{admin_code}")
    admin_img_io = io.BytesIO()
    admin_qr.save(admin_img_io, format="PNG")
    admin_img_io.seek(0)
    
    # Add admin QR code to first page
    admin_width = 2 * inch
    admin_img = ReportLabImage(admin_img_io, width=admin_width, height=admin_width)
    
    # Create a 1x3 table for admin QR code
    admin_data = [[admin_img], 
                 [Paragraph("Admin QR Code", subtitle_style)],
                 [Paragraph("Scan to link these QR codes to an event", styles['Normal'])]]
    admin_table = Table(admin_data, colWidths=[4*inch])
    admin_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey)
    ]))
    
    elements.append(admin_table)
    elements.append(Spacer(1, 0.5*inch))
    
    # Create a table with 2 QR codes per row
    table_data = []
    row = []
    
    for idx, qr_code in enumerate(qr_codes):
        # Generate QR code image
        qr_img = qrcode.make(f"{BASE_URL}/redeem/{qr_code.code}")
        img_io = io.BytesIO()
        qr_img.save(img_io, format="PNG")
        img_io.seek(0)
        
        # Create image element
        img_width = 2.5 * inch
        img = ReportLabImage(img_io, width=img_width, height=img_width)
        
        # Create cell content
        title = qr_code.title if qr_code.title else f"{qr_code.points} Points"
        cell_content = [
            img,
            Paragraph(title, subtitle_style),
            Paragraph(f"{qr_code.points} Points", styles['Normal']),
            Paragraph(qr_code.code[:8] + "...", code_style),
            Paragraph(f"{BASE_URL}/redeem/{qr_code.code[:8]}...", code_style)
        ]
        
        row.append(cell_content)
        
        # Create a new row after every 2 cells
        if len(row) == 2 or idx == len(qr_codes) - 1:
            # If we have an odd number at the end, add an empty cell
            if len(row) == 1:
                row.append([])
            
            table_data.append(row)
            row = []
    
    # Create the table
    col_width = doc.width / 2
    qr_table = Table(table_data, colWidths=[col_width, col_width])
    
    # Style the table
    table_style = [
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]
    qr_table.setStyle(TableStyle(table_style))
    
    elements.append(qr_table)
    
    # Build the PDF
    doc.build(elements)
    buffer.seek(0)
    
    # Return PDF as a download
    return StreamingResponse(
        buffer, 
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=qr_codes_{set_id}.pdf"}
    )
