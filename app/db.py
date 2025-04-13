#!/usr/bin/env python3
import os
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, declarative_base

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

# Create base class for models
Base = declarative_base()

def init_db():
    """Initialize the database with all tables."""
    # Import all models to ensure they're loaded
    from . import models
    
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
        
        # Check User table
        if 'users' in inspector.get_table_names():
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
        
        # Check Team table
        if 'teams' in inspector.get_table_names():
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
        
        # Check TeamMembership table
        if 'team_membership' in inspector.get_table_names():
            columns = [col['name'] for col in inspector.get_columns('team_membership')]
            if 'joined_at' not in columns:
                print("Adding joined_at column to team_membership table")
                connection.execute(text(
                    "ALTER TABLE team_membership ADD COLUMN joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
                ))
        
        # Check QRTicket table
        if 'qr_tickets' in inspector.get_table_names():
            columns = [col['name'] for col in inspector.get_columns('qr_tickets')]
            if 'created_at' not in columns:
                print("Adding created_at column to qr_tickets table")
                connection.execute(text(
                    "ALTER TABLE qr_tickets ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
                ))
            if 'redeemed_at' not in columns:
                print("Adding redeemed_at column to qr_tickets table")
                connection.execute(text(
                    "ALTER TABLE qr_tickets ADD COLUMN redeemed_at TIMESTAMP NULL"
                ))
            if 'event_name' not in columns:
                print("Adding event_name column to qr_tickets table")
                connection.execute(text(
                    "ALTER TABLE qr_tickets ADD COLUMN event_name VARCHAR(255)"
                ))
        
        # Create OAuthAccount table if it doesn't exist
        if 'oauth_accounts' not in inspector.get_table_names():
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
        
        # Create TeamAchievement table if it doesn't exist
        if 'team_achievements' not in inspector.get_table_names():
            print("Creating team_achievements table")
            connection.execute(text("""
                CREATE TABLE team_achievements (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    team_id INT,
                    name VARCHAR(255) NOT NULL,
                    event_name VARCHAR(255),
                    description TEXT,
                    achieved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (team_id) REFERENCES teams(id)
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
