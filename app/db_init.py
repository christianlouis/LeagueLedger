#!/usr/bin/env python3
"""
Seed the database with initial testing data.
"""
import random
import uuid
from datetime import datetime, timedelta
from sqlalchemy import inspect
from sqlalchemy.orm import Session
from passlib.context import CryptContext

from .models import User, Team, TeamMembership, QRCode, QRSet, TeamAchievement, Event
from .db import SessionLocal, engine
from .db_migrations import run_migrations

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def table_has_column(engine, table_name, column_name):
    """Check if a table has a specific column."""
    inspector = inspect(engine)
    if table_name not in inspector.get_table_names():
        return False
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns

def init_db():
    """Initialize the database, applying migrations and seeding data."""
    # First, run any needed migrations
    run_migrations(engine)
    
    # Then proceed with seeding if needed
    seed_db()

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
        
        # Create events for QR code linking
        events = [
            Event(name="Music Trivia Night", description="A night of musical quizzes", 
                  event_date=datetime.now() - timedelta(days=60), 
                  location="Irish Rover Pub"),
            Event(name="History Night", description="Test your history knowledge", 
                  event_date=datetime.now() - timedelta(days=45), 
                  location="Irish Rover Pub"),
            Event(name="Movie Trivia Night", description="All about cinema", 
                  event_date=datetime.now() - timedelta(days=30), 
                  location="Irish Rover Pub"),
            Event(name="Sports Quiz", description="For sports enthusiasts", 
                  event_date=datetime.now() - timedelta(days=15), 
                  location="Irish Rover Pub"),
            Event(name="General Knowledge", description="A bit of everything", 
                  event_date=datetime.now() - timedelta(days=7), 
                  location="Irish Rover Pub"),
            Event(name="Irish Rover Pub Quiz April 2025", description="Monthly pub quiz", 
                  event_date=datetime.now(), 
                  location="Irish Rover Pub")
        ]
        db.add_all(events)
        db.commit()
        
        # Create QR sets
        qr_sets = [
            QRSet(
                name="Standard Pub Quiz",
                description="Contains QR codes for 1st place (25 points), 2nd place (15 points), 3rd place (10 points), and 4th place (5 points)",
                created_by=1  # Admin user
            ),
            QRSet(
                name="Trivia Night with Achievements",
                description="Special trivia night with QR codes for winners and achievement codes for trivia categories",
                created_by=2  # John the quizmaster
            )
        ]
        db.add_all(qr_sets)
        db.commit()
        
        # Create QR codes (both used and unused)
        qr_codes = []
        
        # First, create some QR codes in sets (unused)
        # Standard Pub Quiz set
        qr_set_1 = qr_sets[0]
        qr_codes.extend([
            QRCode(
                code=str(uuid.uuid4()),
                points=25,
                title="1st Place",
                description="First place award (25 points)",
                achievement_name="First Place Winner",
                qr_set_id=qr_set_1.id,
                used=False
            ),
            QRCode(
                code=str(uuid.uuid4()),
                points=15,
                title="2nd Place",
                description="Second place award (15 points)",
                achievement_name="Second Place Winner",
                qr_set_id=qr_set_1.id,
                used=False
            ),
            QRCode(
                code=str(uuid.uuid4()),
                points=10,
                title="3rd Place",
                description="Third place award (10 points)",
                achievement_name="Third Place Winner",
                qr_set_id=qr_set_1.id,
                used=False
            ),
            QRCode(
                code=str(uuid.uuid4()),
                points=5,
                title="4th Place",
                description="Fourth place award (5 points)",
                achievement_name=None,
                qr_set_id=qr_set_1.id,
                used=False
            )
        ])
        
        # Trivia Night set with special achievements
        qr_set_2 = qr_sets[1]
        qr_codes.extend([
            QRCode(
                code=str(uuid.uuid4()),
                points=20,
                title="Trivia Champion",
                description="Overall winner of trivia night",
                achievement_name="Trivia Champion",
                qr_set_id=qr_set_2.id,
                used=False
            ),
            QRCode(
                code=str(uuid.uuid4()),
                points=0,
                title="Estimate Winner",
                description="Closest guess to the correct answer",
                achievement_name="Closest Guess Award",
                is_achievement_only=True,
                qr_set_id=qr_set_2.id,
                used=False
            ),
            QRCode(
                code=str(uuid.uuid4()),
                points=0,
                title="Film Buff",
                description="Most movie questions correct",
                achievement_name="Film Buff",
                is_achievement_only=True,
                qr_set_id=qr_set_2.id,
                used=False
            )
        ])
        
        # Now create some already used/redeemed QR codes
        for i in range(15):
            points = random.choice([5, 10, 15, 20, 25])
            team_id = random.randint(1, len(teams))
            user_id = random.randint(1, len(users))
            event_id = random.randint(1, len(events) - 1)  # Exclude the latest event
            
            achievement = None
            if points >= 15:  # Only high points get achievements
                achievement = random.choice(["Winner", "Top Scorer", "Quiz Master", None])
                
            redeemed_at = datetime.now() - timedelta(days=random.randint(7, 90))
            
            qr_codes.append(
                QRCode(
                    code=f"TICKET{i:03d}",
                    points=points,
                    title=f"{points} Points Ticket",
                    achievement_name=achievement,
                    redeemed_by=user_id,
                    redeemed_at_team=team_id,
                    redeemed_at=redeemed_at,
                    event_id=event_id,
                    used=True
                )
            )
            
            # Create achievement record if applicable
            if achievement:
                team_achievement = TeamAchievement(
                    team_id=team_id,
                    name=achievement,
                    event_id=event_id,
                    achieved_at=redeemed_at,
                    qr_code_id=i + 1  # This will be assigned after the QR codes are committed
                )
                db.add(team_achievement)
        
        db.add_all(qr_codes)
        db.commit()
        
        print("Database seeded successfully!")
        
    except Exception as e:
        print(f"Error seeding database: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    init_db()
