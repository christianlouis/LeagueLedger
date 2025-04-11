#!/usr/bin/env python3
"""
Generate QR codes for top teams (quiz master).
"""
import qrcode
import io
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from ..db import SessionLocal
from ..models import QRTicket
import uuid

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/generate/{points}")
def generate_qr(points: int, db: Session = Depends(get_db)):
    """
    Generate a QR code for awarding `points` points. 
    Saves a record in the DB, returns the PNG as streaming response.
    """
    code_str = str(uuid.uuid4())

    ticket = QRTicket(code=code_str, points=points)
    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    qr_img = qrcode.make(code_str)
    buf = io.BytesIO()
    qr_img.save(buf, format="PNG")
    buf.seek(0)

    return StreamingResponse(buf, media_type="image/png")
