from sqlalchemy import text, inspect, Column, String, JSON, MetaData, Table
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

def run_migrations(engine):
    """
    Run database migrations that can't be handled by SQLAlchemy's create_all()
    """
    # Create a MetaData object
    metadata = MetaData()
    metadata.bind = engine
    connection = engine.connect()
    
    try:
        print("Running migrations...")
        
        # Check if the columns already exist before adding them
        # Add additional_oauth_providers column if it doesn't exist
        add_oauth_providers_column(connection)
        
        # Add first_name and last_name columns if they don't exist
        add_name_columns(connection)
        
        print("Migrations completed successfully")
        
    except Exception as e:
        print(f"Error during migrations: {str(e)}")
    finally:
        connection.close()
        
def add_oauth_providers_column(connection):
    """Add additional_oauth_providers column to users table"""
    try:
        # Use database-agnostic way to check if column exists
        inspector = inspect(engine)
        columns = [col['name'] for col in inspector.get_columns('users')]
        
        if 'additional_oauth_providers' not in columns:
            print("Adding additional_oauth_providers column to users table")
            
            # Add column with database-specific syntax
            if engine.name == 'sqlite':
                connection.execute(text("""
                    ALTER TABLE users
                    ADD COLUMN additional_oauth_providers JSON
                """))
            else:  # MySQL
                connection.execute(text("""
                    ALTER TABLE users
                    ADD COLUMN additional_oauth_providers JSON NULL
                """))
                
            connection.commit()
        else:
            print("Column additional_oauth_providers already exists")
    except Exception as e:
        print(f"Error adding additional_oauth_providers column: {str(e)}")

def add_name_columns(connection):
    """Add first_name and last_name columns to users table"""
    try:
        # Use database-agnostic way to check if columns exist
        inspector = inspect(engine)
        columns = [col['name'] for col in inspector.get_columns('users')]
        
        # Add first_name if needed
        if 'first_name' not in columns:
            print("Adding first_name column to users table")
            connection.execute(text("""
                ALTER TABLE users
                ADD COLUMN first_name VARCHAR(50) NULL
            """))
            connection.commit()
        else:
            print("Column first_name already exists")
        
        # Add last_name if needed
        if 'last_name' not in columns:
            print("Adding last_name column to users table")
            connection.execute(text("""
                ALTER TABLE users
                ADD COLUMN last_name VARCHAR(50) NULL
            """))
            connection.commit()
        else:
            print("Column last_name already exists")
    except Exception as e:
        print(f"Error adding name columns: {str(e)}")
