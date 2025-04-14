#!/usr/bin/env python3
import os
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

# Get database connection details from environment variables with fallbacks
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = os.environ.get("DB_PORT", "3306")
DB_NAME = os.environ.get("DB_NAME", "pubquiz_db")
DB_USER = os.environ.get("DB_USER", "pubquiz_user")
DB_PASS = os.environ.get("DB_PASS", "pubquiz_pass")

# Create database URL
SQLALCHEMY_DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Create engine with appropriate parameters
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Import Base from models to ensure we use the same instance
from .models import Base

def init_db():
    """Initialize the database with all tables."""
    # No need to import models here as we're already importing Base from models
    # This ensures all models are loaded because they're defined in the models module
    
    # Create all tables if they don't exist
    Base.metadata.create_all(bind=engine)
    
    # Check for missing columns and add them
    print("Checking for schema updates...")
    migrate_schema()

def migrate_schema():
    """Apply schema migrations for existing tables."""
    try:
        connection = engine.connect()
        inspector = inspect(engine)
        
        # Check if tables exist first
        tables = inspector.get_table_names()
        
        # Check User table
        if 'users' in tables:
            columns = [col['name'] for col in inspector.get_columns('users')]
            
            # Add all missing columns for User table
            user_columns = {
                'created_at': "ALTER TABLE users ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                'is_active': "ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT TRUE",
                'is_verified': "ALTER TABLE users ADD COLUMN is_verified BOOLEAN DEFAULT FALSE",
                'verification_token': "ALTER TABLE users ADD COLUMN verification_token VARCHAR(255)",
                'reset_token': "ALTER TABLE users ADD COLUMN reset_token VARCHAR(255)",
                'reset_token_expires_at': "ALTER TABLE users ADD COLUMN reset_token_expires_at TIMESTAMP NULL",
                'last_login': "ALTER TABLE users ADD COLUMN last_login TIMESTAMP NULL",
                'is_admin': "ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT FALSE"  # Add is_admin column
            }
            
            for col_name, sql in user_columns.items():
                if col_name not in columns:
                    print(f"Adding {col_name} column to users table")
                    try:
                        connection.execute(text(sql))
                        connection.commit()
                    except Exception as e:
                        print(f"Error adding column {col_name}: {e}")
        else:
            print("Users table doesn't exist yet, skipping User table migrations")
        
        # Check Team table
        if 'teams' in tables:
            columns = [col['name'] for col in inspector.get_columns('teams')]
            if 'is_public' not in columns:
                print("Adding is_public column to teams table")
                connection.execute(text(
                    "ALTER TABLE teams ADD COLUMN is_public BOOLEAN DEFAULT FALSE"
                ))
            if 'created_at' not in columns:
                print("Adding created_at column to teams table")
                connection.execute(text(
                    "ALTER TABLE teams ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
                ))
            if 'description' not in columns:
                print("Adding description column to teams table")
                connection.execute(text(
                    "ALTER TABLE teams ADD COLUMN description TEXT"
                ))
        else:
            print("Teams table doesn't exist yet, skipping Team table migrations")
        
        # Check TeamMembership table
        if 'team_membership' in tables:
            columns = [col['name'] for col in inspector.get_columns('team_membership')]
            if 'joined_at' not in columns:
                print("Adding joined_at column to team_membership table")
                connection.execute(text(
                    "ALTER TABLE team_membership ADD COLUMN joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
                ))
        else:
            print("TeamMembership table doesn't exist yet, skipping TeamMembership table migrations")
        
        # Check QRCode table (formerly QRTicket)
        if 'qr_codes' in tables:
            columns = [col['name'] for col in inspector.get_columns('qr_codes')]
            if 'created_at' not in columns:
                print("Adding created_at column to qr_codes table")
                connection.execute(text(
                    "ALTER TABLE qr_codes ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
                ))
            if 'redeemed_at' not in columns:
                print("Adding redeemed_at column to qr_codes table")
                connection.execute(text(
                    "ALTER TABLE qr_codes ADD COLUMN redeemed_at TIMESTAMP NULL"
                ))
        else:
            print("QRCodes table doesn't exist yet, skipping QRCode table migrations")
        
        # Handle legacy QRTicket table migration if it exists
        if 'qr_tickets' in tables and 'qr_codes' in tables:
            print("Migrating data from legacy qr_tickets table to qr_codes table")
            try:
                # Check if migration has already been done
                ticket_count = connection.execute(text("SELECT COUNT(*) FROM qr_tickets")).scalar()
                if ticket_count > 0:
                    # Migrate data from qr_tickets to qr_codes
                    connection.execute(text("""
                        INSERT INTO qr_codes (code, points, redeemed_by, redeemed_at_team, used, redeemed_at)
                        SELECT code, points, redeemed_by, redeemed_at_team, used, redeemed_at 
                        FROM qr_tickets
                    """))
                    connection.commit()
                    print(f"Migrated {ticket_count} tickets from qr_tickets to qr_codes")
            except Exception as e:
                print(f"Error during qr_tickets migration: {e}")
        
        # Create tables that don't exist only if users table exists first
        # This ensures we can properly create foreign keys
        if 'users' in tables:
            # Create OAuthAccount table if it doesn't exist
            if 'oauth_accounts' not in tables:
                print("Creating oauth_accounts table")
                connection.execute(text("""
                    CREATE TABLE oauth_accounts (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        user_id INT,
                        provider VARCHAR(50),
                        provider_user_id VARCHAR(255),
                        access_token VARCHAR(255),
                        expires_at TIMESTAMP NULL,
                        refresh_token VARCHAR(255),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(id)
                    )
                """))
                connection.commit()
            
            # Create teams table if it doesn't exist
            if 'teams' not in tables:
                print("Creating teams table")
                connection.execute(text("""
                    CREATE TABLE teams (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        name VARCHAR(100) UNIQUE NOT NULL,
                        description TEXT,
                        is_public BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        owner_id INT,
                        FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE SET NULL
                    )
                """))
                connection.commit()
            
            # Create team_members table if it doesn't exist and teams table exists
            if 'team_members' not in tables and 'teams' in tables:
                print("Creating team_members table")
                connection.execute(text("""
                    CREATE TABLE team_members (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        user_id INT NOT NULL,
                        team_id INT NOT NULL,
                        is_captain BOOLEAN DEFAULT FALSE,
                        joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                        FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE
                    )
                """))
                connection.commit()
                
            # Create team_membership table if it doesn't exist and teams table exists
            if 'team_membership' not in tables and 'teams' in tables:
                print("Creating team_membership table")
                connection.execute(text("""
                    CREATE TABLE team_membership (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        user_id INT,
                        team_id INT,
                        is_admin BOOLEAN DEFAULT FALSE,
                        joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(id),
                        FOREIGN KEY (team_id) REFERENCES teams(id)
                    )
                """))
                connection.commit()

            # Create Event table if it doesn't exist
            if 'events' not in tables:
                print("Creating events table")
                connection.execute(text("""
                    CREATE TABLE events (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        name VARCHAR(100) NOT NULL,
                        description TEXT,
                        location VARCHAR(200),
                        event_date TIMESTAMP NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                    )
                """))
                connection.commit()

            # Create event_attendees table if it doesn't exist and events table exists
            if 'event_attendees' not in tables and 'events' in tables:
                print("Creating event_attendees table")
                connection.execute(text("""
                    CREATE TABLE event_attendees (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        event_id INT NOT NULL,
                        user_id INT NOT NULL,
                        check_in_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE,
                        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                    )
                """))
                connection.commit()

            # Create user_points table if it doesn't exist
            if 'user_points' not in tables:
                print("Creating user_points table")
                connection.execute(text("""
                    CREATE TABLE user_points (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        user_id INT NOT NULL,
                        points FLOAT NOT NULL DEFAULT 0,
                        reason VARCHAR(200),
                        awarded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                    )
                """))
                connection.commit()
        
        # Create QRSet table if it doesn't exist
        if 'qr_sets' not in tables:
            print("Creating qr_sets table")
            connection.execute(text("""
                CREATE TABLE qr_sets (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_by INT,
                    FOREIGN KEY (created_by) REFERENCES users(id)
                )
            """))
            connection.commit()
        
        print("Schema migrations completed successfully")
    except Exception as e:
        print(f"Error during schema migration: {e}")
    finally:
        connection.close()

# Add the missing get_db function
def get_db():
    """Database dependency for FastAPI endpoints"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
