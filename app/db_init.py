#!/usr/bin/env python3
"""
Seed the database with initial testing data.
"""
import random
from datetime import datetime, timedelta
from sqlalchemy import inspect
from sqlalchemy.orm import Session

from .models import User, Team, TeamMembership, QRTicket
from .db import SessionLocal
from .auth import get_password_hash

def table_has_column(engine, table_name, column_name):
    """Check if a table has a specific column."""
    inspector = inspect(engine)
    if table_name not in inspector.get_table_names():
        return False
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns

def seed_db():
    """Seed the database with test data."""
    db = SessionLocal()
    
    try:
        # Only seed if tables are empty
        if db.query(User).count() > 0:
            print("Database already has data. Skipping seeding.")
            return
        
        # Create users with properly hashed passwords
        users = [
            User(
                username="admin",
                email="admin@example.com",
                hashed_password=get_password_hash("password"),
                is_admin=True  # Set admin privileges
            ),
            User(
                username="john_quizmaster",
                email="john@example.com",
                hashed_password=get_password_hash("password123")
            ),
            User(
                username="sarah_johnson",
                email="sarah@example.com",
                hashed_password=get_password_hash("password123")
            ),
            User(
                username="mike_peters",
                email="mike@example.com",
                hashed_password=get_password_hash("password123")
            ),
            User(
                username="emma_wilson",
                email="emma@example.com",
                hashed_password=get_password_hash("password123")
            ),
            User(
                username="robert_brown",
                email="robert@example.com",
                hashed_password=get_password_hash("password123")
            ),
        ]
        db.add_all(users)
        db.commit()
        
        # Create teams
        has_is_public = table_has_column(db.bind, 'teams', 'is_public')
        has_created_at = table_has_column(db.bind, 'teams', 'created_at')
        has_description = table_has_column(db.bind, 'teams', 'description')
        
        teams = []
        for i, name in enumerate(["Quiz Wizards", "Trivia Titans", "Beer Brainiacs", "Knowledge Knights"]):
            team_attrs = {"name": name}
            if has_is_public:
                team_attrs["is_public"] = i % 2 == 1  # Alternate public/private
            if has_description:
                team_attrs["description"] = f"A team of quiz enthusiasts called {name}"
            teams.append(Team(**team_attrs))
        
        db.add_all(teams)
        db.commit()
        
        # Create team memberships
        has_joined_at = table_has_column(db.bind, 'team_membership', 'joined_at')
        
        memberships = []
        membership_data = [
            # Quiz Wizards
            (1, 1, True, 160),  # Admin user is team admin of Quiz Wizards
            (2, 1, True, 155),
            (3, 1, False, 130),
            (4, 1, False, 90),
            (5, 1, False, 45),
            # Trivia Titans
            (2, 2, True, 150),
            (1, 2, False, 145),
            # Beer Brainiacs
            (3, 3, True, 120),
        ]
        
        for user_id, team_id, is_admin, days_ago in membership_data:
            membership_attrs = {
                "user_id": user_id,
                "team_id": team_id,
                "is_admin": is_admin
            }
            if has_joined_at:
                membership_attrs["joined_at"] = datetime.now() - timedelta(days=days_ago)
            memberships.append(TeamMembership(**membership_attrs))
        
        db.add_all(memberships)
        db.commit()
        
        # Create QR tickets
        has_created_at = table_has_column(db.bind, 'qr_tickets', 'created_at')
        has_redeemed_at = table_has_column(db.bind, 'qr_tickets', 'redeemed_at')
        has_event_name = table_has_column(db.bind, 'qr_tickets', 'event_name')
        
        event_names = [
            "Music Trivia Night", 
            "History Night", 
            "Movie Trivia Night", 
            "Sports Quiz", 
            "General Knowledge"
        ]
        
        # Create some basic tickets
        tickets = []
        for i in range(15):
            points = random.choice([5, 10, 15, 20, 25])
            team_id = random.randint(1, len(teams))
            user_id = random.randint(1, len(users))
            
            ticket_attrs = {
                "code": f"TICKET{i:03d}",
                "points": points,
                "redeemed_by": user_id,
                "redeemed_at_team": team_id,
                "used": True
            }
            
            if has_event_name:
                ticket_attrs["event_name"] = random.choice(event_names)
                
            tickets.append(QRTicket(**ticket_attrs))
        
        db.add_all(tickets)
        db.commit()
        
        print("Database seeded successfully!")
        
    except Exception as e:
        print(f"Error seeding database: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_db()
