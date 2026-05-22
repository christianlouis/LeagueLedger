#!/usr/bin/env python3
import re
from typing import Optional

from sqlalchemy.orm import Session

from .models import League, QRCode

DEFAULT_LEAGUE_NAME = "Default League"
DEFAULT_LEAGUE_SLUG = "default"


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or DEFAULT_LEAGUE_SLUG


def get_default_league(db: Session) -> League:
    league = db.query(League).filter(League.slug == DEFAULT_LEAGUE_SLUG).first()
    if league:
        return league

    league = db.query(League).order_by(League.id).first()
    if league:
        return league

    league = League(
        name=DEFAULT_LEAGUE_NAME,
        slug=DEFAULT_LEAGUE_SLUG,
        description="Default league for existing LeagueLedger data.",
        publisher_name="LeagueLedger",
        is_active=True,
    )
    db.add(league)
    db.commit()
    db.refresh(league)
    return league


def get_active_leagues(db: Session):
    leagues = db.query(League).filter(League.is_active == True).order_by(League.name).all()
    if leagues:
        return leagues
    return [get_default_league(db)]


def parse_league_id(value) -> Optional[int]:
    try:
        return int(value) if value else None
    except (TypeError, ValueError):
        return None


def resolve_selected_league(db: Session, league_id: Optional[int]) -> League:
    if league_id:
        league = db.query(League).filter(League.id == league_id, League.is_active == True).first()
        if league:
            return league
    return get_default_league(db)


def qr_code_league_id(qr_code: QRCode) -> Optional[int]:
    if qr_code.league_id:
        return qr_code.league_id
    if qr_code.qr_set and qr_code.qr_set.league_id:
        return qr_code.qr_set.league_id
    if qr_code.event and qr_code.event.league_id:
        return qr_code.event.league_id
    return None
