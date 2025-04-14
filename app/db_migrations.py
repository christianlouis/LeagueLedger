from sqlalchemy import text
from .db import engine

def apply_migrations():
    """Apply all pending database migrations."""
    
    # Check and add OAuth columns to users table
    try:
        with engine.connect() as conn:
            # Check if the OAuth columns exist
            result = conn.execute(text("""
                SELECT COUNT(*) as count 
                FROM information_schema.columns 
                WHERE table_schema = DATABASE() 
                AND table_name = 'users' 
                AND column_name = 'is_oauth_user'
            """))
            
            if result.fetchone()[0] == 0:
                print("Adding OAuth columns to users table...")
                
                # Add the OAuth columns
                conn.execute(text("""
                    ALTER TABLE users 
                    ADD COLUMN is_oauth_user BOOLEAN DEFAULT FALSE,
                    ADD COLUMN oauth_id VARCHAR(255) NULL,
                    ADD COLUMN oauth_provider VARCHAR(50) NULL,
                    ADD COLUMN picture VARCHAR(255) NULL
                """))
                
                conn.commit()
                print("OAuth columns added successfully.")
            else:
                print("OAuth columns already exist in users table.")
            
            # Check if the is_admin column exists in the users table
            result = conn.execute(text("""
                SELECT COUNT(*) as count 
                FROM information_schema.columns 
                WHERE table_schema = DATABASE() 
                AND table_name = 'users' 
                AND column_name = 'is_admin'
            """))
            
            if result.fetchone()[0] == 0:
                print("Adding is_admin column to users table...")
                
                # Add the is_admin column to users table
                conn.execute(text("""
                    ALTER TABLE users 
                    ADD COLUMN is_admin BOOLEAN DEFAULT FALSE
                """))
                
                conn.commit()
                print("is_admin column added successfully to users table.")
            else:
                print("is_admin column already exists in users table.")
            
            # Check if the owner_id column exists in the teams table
            result = conn.execute(text("""
                SELECT COUNT(*) as count 
                FROM information_schema.columns 
                WHERE table_schema = DATABASE() 
                AND table_name = 'teams' 
                AND column_name = 'owner_id'
            """))
            
            if result.fetchone()[0] == 0:
                print("Adding owner_id column to teams table...")
                
                # Add the owner_id column to teams table
                conn.execute(text("""
                    ALTER TABLE teams 
                    ADD COLUMN owner_id INT NULL,
                    ADD CONSTRAINT fk_teams_owner
                    FOREIGN KEY (owner_id) REFERENCES users(id)
                    ON DELETE SET NULL
                """))
                
                conn.commit()
                print("owner_id column added successfully to teams table.")
            else:
                print("owner_id column already exists in teams table.")
                
    except Exception as e:
        print(f"Error applying migrations: {str(e)}")
        raise
