#!/usr/bin/env python3
import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.league_context import get_default_league, parse_league_id, qr_code_league_id, resolve_selected_league
from app.models import Base, Event, League, QRCode, QRSet, Team


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_get_default_league_creates_compatible_default(db_session):
    league = get_default_league(db_session)

    assert league.name == "Default League"
    assert league.slug == "default"
    assert league.is_active is True


def test_resolve_selected_league_uses_active_requested_league(db_session):
    get_default_league(db_session)
    requested = League(name="Rover Pub League", slug="rover-pub", is_active=True)
    inactive = League(name="Archived Pub League", slug="archived-pub", is_active=False)
    db_session.add_all([requested, inactive])
    db_session.commit()

    assert resolve_selected_league(db_session, requested.id).id == requested.id
    assert resolve_selected_league(db_session, inactive.id).slug == "default"
    assert resolve_selected_league(db_session, 9999).slug == "default"


def test_parse_league_id_handles_invalid_values():
    assert parse_league_id("42") == 42
    assert parse_league_id("") is None
    assert parse_league_id(None) is None
    assert parse_league_id("not-a-number") is None


def test_qr_code_league_id_prefers_direct_then_set_then_event(db_session):
    direct = League(name="Direct League", slug="direct", is_active=True)
    via_set = League(name="Set League", slug="set", is_active=True)
    via_event = League(name="Event League", slug="event", is_active=True)
    db_session.add_all([direct, via_set, via_event])
    db_session.commit()

    qr_set = QRSet(name="Weekly Set", league_id=via_set.id)
    event = Event(name="Quiz Night", league_id=via_event.id, event_date=datetime(2026, 5, 22))
    team = Team(name="Quiz Team", league_id=direct.id)
    db_session.add_all([qr_set, event, team])
    db_session.commit()

    direct_qr = QRCode(code="direct-code", points=10, league_id=direct.id)
    set_qr = QRCode(code="set-code", points=10, qr_set_id=qr_set.id)
    event_qr = QRCode(code="event-code", points=10, event_id=event.id)
    db_session.add_all([direct_qr, set_qr, event_qr])
    db_session.commit()

    assert qr_code_league_id(direct_qr) == direct.id
    assert qr_code_league_id(set_qr) == via_set.id
    assert qr_code_league_id(event_qr) == via_event.id
