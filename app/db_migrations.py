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
        # Create league structures and attach existing records to a default league
        add_league_support(connection)

        # Add additional_oauth_providers column if it doesn't exist
        add_oauth_providers_column(connection)
        
        # Add first_name and last_name columns if they don't exist
        add_name_columns(connection)
        
        # Add privacy_settings column if it doesn't exist
        add_privacy_settings_column(connection)
        
        # Add picture_manually_deleted column if it doesn't exist
        add_picture_manually_deleted_column(connection)
        
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

def add_league_support(connection):
    """Add leagues and backfill existing single-league data."""
    try:
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        if 'leagues' not in tables:
            print("Creating leagues table")
            if engine.name == 'sqlite':
                connection.execute(text("""
                    CREATE TABLE leagues (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name VARCHAR(100) UNIQUE NOT NULL,
                        slug VARCHAR(120) UNIQUE NOT NULL,
                        description TEXT,
                        publisher_name VARCHAR(100),
                        is_active BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
            else:
                connection.execute(text("""
                    CREATE TABLE leagues (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        name VARCHAR(100) UNIQUE NOT NULL,
                        slug VARCHAR(120) UNIQUE NOT NULL,
                        description TEXT,
                        publisher_name VARCHAR(100),
                        is_active BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                    )
                """))
            connection.commit()

        league_id = ensure_default_league(connection)

        for table_name in ('teams', 'qr_sets', 'qr_codes', 'events'):
            add_nullable_league_id(connection, table_name)

        backfill_league_ids(connection, league_id)
        drop_global_team_name_unique(connection)
    except Exception as e:
        print(f"Error adding league support: {str(e)}")

def ensure_default_league(connection):
    """Return the default league id, creating it if needed."""
    row = connection.execute(
        text("SELECT id FROM leagues WHERE slug = :slug"),
        {"slug": "default"}
    ).first()
    if row:
        return row[0]

    connection.execute(
        text("""
            INSERT INTO leagues (name, slug, description, publisher_name, is_active)
            VALUES (:name, :slug, :description, :publisher_name, :is_active)
        """),
        {
            "name": "Default League",
            "slug": "default",
            "description": "Default league for existing LeagueLedger data.",
            "publisher_name": "LeagueLedger",
            "is_active": True,
        }
    )
    connection.commit()
    return connection.execute(
        text("SELECT id FROM leagues WHERE slug = :slug"),
        {"slug": "default"}
    ).scalar()

def add_nullable_league_id(connection, table_name):
    """Add a nullable league_id column to an existing table."""
    inspector = inspect(engine)
    if table_name not in inspector.get_table_names():
        return

    columns = [col['name'] for col in inspector.get_columns(table_name)]
    if 'league_id' in columns:
        print(f"Column league_id already exists in {table_name}")
        return

    print(f"Adding league_id column to {table_name}")
    if engine.name == 'sqlite':
        connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN league_id INTEGER NULL"))
    else:
        connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN league_id INT NULL"))
    connection.commit()

def backfill_league_ids(connection, default_league_id):
    """Attach legacy data to the default league."""
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    for table_name in ('teams', 'qr_sets', 'events'):
        if table_name in tables and 'league_id' in [col['name'] for col in inspector.get_columns(table_name)]:
            connection.execute(
                text(f"UPDATE {table_name} SET league_id = :league_id WHERE league_id IS NULL"),
                {"league_id": default_league_id}
            )

    if 'qr_codes' in tables and 'league_id' in [col['name'] for col in inspector.get_columns('qr_codes')]:
        connection.execute(text("""
            UPDATE qr_codes
            SET league_id = (
                SELECT qr_sets.league_id
                FROM qr_sets
                WHERE qr_sets.id = qr_codes.qr_set_id
            )
            WHERE league_id IS NULL
            AND qr_set_id IS NOT NULL
        """))
        connection.execute(text("""
            UPDATE qr_codes
            SET league_id = (
                SELECT events.league_id
                FROM events
                WHERE events.id = qr_codes.event_id
            )
            WHERE league_id IS NULL
            AND event_id IS NOT NULL
        """))
        connection.execute(
            text("UPDATE qr_codes SET league_id = :league_id WHERE league_id IS NULL"),
            {"league_id": default_league_id}
        )

    connection.commit()

def drop_global_team_name_unique(connection):
    """Best-effort removal of the legacy global team-name uniqueness constraint."""
    if engine.name == 'sqlite':
        return

    inspector = inspect(engine)
    if 'teams' not in inspector.get_table_names():
        return

    for constraint in inspector.get_unique_constraints('teams'):
        if constraint.get('column_names') == ['name']:
            constraint_name = constraint.get('name')
            if constraint_name:
                print(f"Dropping global teams.name unique constraint {constraint_name}")
                connection.execute(text(f"ALTER TABLE teams DROP INDEX {constraint_name}"))
                connection.commit()
            break

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

def add_privacy_settings_column(connection):
    """Add privacy_settings column to users table"""
    try:
        # Use database-agnostic way to check if column exists
        inspector = inspect(engine)
        columns = [col['name'] for col in inspector.get_columns('users')]
        
        if 'privacy_settings' not in columns:
            print("Adding privacy_settings column to users table")
            
            # Add column with database-specific syntax
            if engine.name == 'sqlite':
                connection.execute(text("""
                    ALTER TABLE users
                    ADD COLUMN privacy_settings JSON
                """))
            else:  # MySQL
                connection.execute(text("""
                    ALTER TABLE users
                    ADD COLUMN privacy_settings JSON NULL
                """))
                
            connection.commit()
            print("Successfully added privacy_settings column to users table")
        else:
            print("Column privacy_settings already exists")
    except Exception as e:
        print(f"Error adding privacy_settings column: {str(e)}")

def add_picture_manually_deleted_column(connection):
    """Add picture_manually_deleted column to users table"""
    try:
        # Use database-agnostic way to check if column exists
        inspector = inspect(engine)
        columns = [col['name'] for col in inspector.get_columns('users')]
        
        if 'picture_manually_deleted' not in columns:
            print("Adding picture_manually_deleted column to users table")
            
            # Add column with database-specific syntax
            if engine.name == 'sqlite':
                connection.execute(text("""
                    ALTER TABLE users
                    ADD COLUMN picture_manually_deleted BOOLEAN DEFAULT FALSE
                """))
            else:  # MySQL
                connection.execute(text("""
                    ALTER TABLE users
                    ADD COLUMN picture_manually_deleted BOOLEAN DEFAULT FALSE
                """))
                
            connection.commit()
            print("Successfully added picture_manually_deleted column to users table")
        else:
            print("Column picture_manually_deleted already exists")
    except Exception as e:
        print(f"Error adding picture_manually_deleted column: {str(e)}")
