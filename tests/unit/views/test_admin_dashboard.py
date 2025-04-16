#!/usr/bin/env python3
import pytest
from unittest import mock
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient
from datetime import datetime, timedelta

from app.main import app
from app.models import User, Team, Event, QRCode
from app.views.admin import get_user_statistics, get_team_statistics
from app.views.admin import get_event_statistics, get_system_health

# Fixture for mocking the database session
@pytest.fixture
def mock_db():
    """Create a mock database session for testing."""
    mock_session = mock.MagicMock(spec=Session)
    return mock_session

# Test cases for user statistics
def test_get_user_statistics(mock_db):
    """Test getting user statistics."""
    # Setup mock query results
    mock_db.query().count.side_effect = [100, 80, 20]
    mock_db.query().filter().count.return_value = 10
    
    # Get last 30 days
    thirty_days_ago = datetime.now() - timedelta(days=30)
    mock_db.query().filter().filter().count.return_value = 15
    
    # Get the statistics
    stats = get_user_statistics(mock_db)
    
    # Assert the expected results
    assert stats["total_users"] == 100
    assert stats["active_users"] == 80
    assert stats["verified_users"] == 20
    assert stats["admin_users"] == 10
    assert stats["new_registrations_30d"] == 15

# Test cases for team statistics
def test_get_team_statistics(mock_db):
    """Test getting team statistics."""
    # Setup mock query results
    mock_db.query().count.side_effect = [50, 45]
    mock_db.query().filter().count.return_value = 5
    
    # Team distribution mock
    mock_team_distribution = [
        {"member_count": 0, "count": 5},
        {"member_count": 1, "count": 10},
        {"member_count": 2, "count": 15},
        {"member_count": 3, "count": 10},
        {"member_count": 4, "count": 7},
        {"member_count": 5, "count": 3}
    ]
    mock_db.query().group_by().all.return_value = mock_team_distribution
    
    # Get the statistics
    stats = get_team_statistics(mock_db)
    
    # Assert the expected results
    assert stats["total_teams"] == 50
    assert stats["active_teams"] == 45
    assert stats["public_teams"] == 5
    assert stats["team_distribution"] == mock_team_distribution

# Test cases for event statistics
def test_get_event_statistics(mock_db):
    """Test getting event statistics."""
    # Setup mock query results
    mock_db.query().count.side_effect = [30, 25, 5]
    
    # Setup mock for upcoming events
    today = datetime.now().date()
    upcoming_events = [
        mock.MagicMock(name="Event 1", event_date=today + timedelta(days=1), location="Location 1"),
        mock.MagicMock(name="Event 2", event_date=today + timedelta(days=3), location="Location 2"),
        mock.MagicMock(name="Event 3", event_date=today + timedelta(days=7), location="Location 3")
    ]
    mock_db.query().filter().order_by().limit().all.return_value = upcoming_events
    
    # Setup mock for attendance rates
    mock_attendance_rates = [
        {"event_id": 1, "event_name": "Event A", "attendee_count": 25},
        {"event_id": 2, "event_name": "Event B", "attendee_count": 18},
        {"event_id": 3, "event_name": "Event C", "attendee_count": 30}
    ]
    mock_db.query().join().group_by().order_by().limit().all.return_value = mock_attendance_rates
    
    # Get the statistics
    stats = get_event_statistics(mock_db)
    
    # Assert the expected results
    assert stats["total_events"] == 30
    assert stats["past_events"] == 25
    assert stats["upcoming_events_count"] == 5
    assert len(stats["upcoming_events"]) == 3
    assert stats["attendance_rates"] == mock_attendance_rates

# Test cases for system health
def test_get_system_health(mock_db):
    """Test getting system health information."""
    # Mock database status
    mock_db.execute().fetchall.return_value = [{"status": "online"}]
    
    # Get the health information
    health_info = get_system_health(mock_db)
    
    # Assert expected results
    assert health_info["database_status"] == "online"
    assert "uptime" in health_info
    assert "recent_errors" in health_info

# Integration test for admin dashboard endpoint
@mock.patch("app.views.admin.get_db")
def test_admin_dashboard_endpoint(mock_get_db, mock_db):
    """Test the admin dashboard endpoint."""
    # Setup mock DB to be returned from get_db
    mock_get_db.return_value = mock_db
    
    # Mock user stats
    mock_user_stats = {
        "total_users": 100,
        "active_users": 80,
        "verified_users": 20,
        "admin_users": 10,
        "new_registrations_30d": 15
    }
    
    # Mock team stats
    mock_team_stats = {
        "total_teams": 50,
        "active_teams": 45,
        "public_teams": 5,
        "team_distribution": []
    }
    
    # Mock event stats
    mock_event_stats = {
        "total_events": 30,
        "past_events": 25,
        "upcoming_events_count": 5,
        "upcoming_events": [],
        "attendance_rates": []
    }
    
    # Mock system health
    mock_system_health = {
        "database_status": "online",
        "uptime": "3 days, 2 hours",
        "recent_errors": []
    }
    
    # Setup mock return values for our statistics functions
    with mock.patch("app.views.admin.get_user_statistics", return_value=mock_user_stats), \
         mock.patch("app.views.admin.get_team_statistics", return_value=mock_team_stats), \
         mock.patch("app.views.admin.get_event_statistics", return_value=mock_event_stats), \
         mock.patch("app.views.admin.get_system_health", return_value=mock_system_health), \
         mock.patch("app.views.admin.require_admin", return_value=lambda f: f):
        
        client = TestClient(app)
        response = client.get("/admin/dashboard")
        
        # Assert the response
        assert response.status_code == 200
        assert "user_stats" in response.context
        assert "team_stats" in response.context
        assert "event_stats" in response.context
        assert "system_health" in response.context