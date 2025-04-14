from sqlalchemy import text, inspect
from .db import engine

def table_exists(conn, table_name):
    """Check if a table exists in the database."""
    result = conn.execute(text(f"""
        SELECT COUNT(*) as count 
        FROM information_schema.tables 
        WHERE table_schema = DATABASE() 
        AND table_name = '{table_name}'
    """))
    return result.scalar() > 0

def column_exists(conn, table_name, column_name):
    """Check if a column exists in a table."""
    result = conn.execute(text(f"""
        SELECT COUNT(*) as count 
        FROM information_schema.columns 
        WHERE table_schema = DATABASE() 
        AND table_name = '{table_name}' 
        AND column_name = '{column_name}'
    """))
    return result.scalar() > 0

def apply_migrations():
    """Apply all pending database migrations."""
    
    # Check and add OAuth columns to users table
    try:
        with engine.connect() as conn:
            # Make sure tables exist before trying to alter them
            if not table_exists(conn, 'users'):
                print("Users table doesn't exist yet. Skipping OAuth columns migration.")
                return
            
            # Check if the OAuth columns exist
            if not column_exists(conn, 'users', 'is_oauth_user'):
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
            if not column_exists(conn, 'users', 'is_admin'):
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
            
            # Only proceed with teams table if it exists
            if table_exists(conn, 'teams'):
                # Check if the owner_id column exists in the teams table
                if not column_exists(conn, 'teams', 'owner_id'):
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
            else:
                print("Teams table doesn't exist yet. Skipping teams migrations.")
                
    except Exception as e:
        print(f"Error applying migrations: {str(e)}")
