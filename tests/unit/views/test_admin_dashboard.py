#!/usr/bin/env python3
from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base, Event, EventAttendee, Team, TeamMembership, User
from app.views.admin import (
    get_event_statistics,
    get_system_health,
    get_team_statistics,
    get_user_statistics,
)


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


def seed_users(db):
    now = datetime.utcnow()
    users = [
        User(
            username="admin",
            email="admin@example.com",
            hashed_password="hash",
            is_active=True,
            is_verified=True,
            is_admin=True,
            created_at=now - timedelta(days=2),
        ),
        User(
            username="verified",
            email="verified@example.com",
            hashed_password="hash",
            is_active=True,
            is_verified=True,
            is_admin=False,
            created_at=now - timedelta(days=10),
        ),
        User(
            username="inactive",
            email="inactive@example.com",
            hashed_password="hash",
            is_active=False,
            is_verified=False,
            is_admin=False,
            created_at=now - timedelta(days=60),
        ),
    ]
    db.add_all(users)
    db.commit()
    return users


def test_get_user_statistics(db_session):
    seed_users(db_session)

    stats = get_user_statistics(db_session)

    assert stats["total_users"] == 3
    assert stats["active_users"] == 2
    assert stats["verified_users"] == 2
    assert stats["admin_users"] == 1
    assert stats["new_registrations_30d"] == 2
    assert len(stats["monthly_registrations"]) == 6
    assert len(stats["month_labels"]) == 6


def test_get_team_statistics(db_session):
    users = seed_users(db_session)
    teams = [
        Team(name="Open Team", is_active=True, is_public=True),
        Team(name="Private Team", is_active=True, is_public=False),
        Team(name="Archived Team", is_active=False, is_public=False),
    ]
    db_session.add_all(teams)
    db_session.commit()
    db_session.add_all([
        TeamMembership(user_id=users[0].id, team_id=teams[0].id),
        TeamMembership(user_id=users[1].id, team_id=teams[0].id),
        TeamMembership(user_id=users[2].id, team_id=teams[1].id),
    ])
    db_session.commit()

    stats = get_team_statistics(db_session)

    assert stats["total_teams"] == 3
    assert stats["active_teams"] == 2
    assert stats["public_teams"] == 1
    assert {"member_count": 2, "count": 1} in stats["team_distribution"]
    assert {"member_count": 1, "count": 1} in stats["team_distribution"]


def test_get_event_statistics(db_session):
    users = seed_users(db_session)
    now = datetime.now()
    past_event = Event(name="Past Quiz", event_date=now - timedelta(days=1))
    future_event = Event(name="Future Quiz", event_date=now + timedelta(days=7))
    db_session.add_all([past_event, future_event])
    db_session.commit()
    db_session.add_all([
        EventAttendee(event_id=past_event.id, user_id=users[0].id),
        EventAttendee(event_id=past_event.id, user_id=users[1].id),
    ])
    db_session.commit()

    stats = get_event_statistics(db_session)

    assert stats["total_events"] == 2
    assert stats["past_events"] == 1
    assert stats["upcoming_events_count"] == 1
    assert [event.name for event in stats["upcoming_events"]] == ["Future Quiz"]
    assert stats["attendance_rates"][0].event_name == "Past Quiz"
    assert stats["attendance_rates"][0].attendee_count == 2


def test_get_system_health(db_session):
    health_info = get_system_health(db_session)

    assert health_info["database_status"] == "online"
    assert "uptime" in health_info
    assert health_info["recent_errors"] == []
