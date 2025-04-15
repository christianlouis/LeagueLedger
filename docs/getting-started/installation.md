# Installation Guide

This guide will walk you through the process of installing LeagueLedger on your system.

## Prerequisites

Before installing LeagueLedger, make sure you have the following prerequisites:

- Python 3.10 or higher
- pip (Python package manager)
- Git (optional, for cloning the repository)
- Docker and Docker Compose (optional, for containerized deployment)

## Option 1: Installation with Docker (Recommended)

The easiest way to get LeagueLedger up and running is using Docker and Docker Compose.

### Step 1: Clone the Repository

```bash
git clone https://github.com/yourusername/leagueledger.git
cd leagueledger
```

### Step 2: Create Environment File

Create a `.env` file in the project root or copy from the example:

```bash
cp .env.example .env
```

Edit the `.env` file to configure your environment variables.

### Step 3: Start with Docker Compose

```bash
docker-compose up -d
```

This will start all the required services including:
- Web application
- MySQL database
- PHPMyAdmin for database management
- Mailpit for email testing

### Step 4: Access the Application

Once the containers are running, you can access:
- LeagueLedger web interface at [http://localhost:8000](http://localhost:8000)
- PHPMyAdmin at [http://localhost:8001](http://localhost:8001)
- Mailpit (email testing) at [http://localhost:8025](http://localhost:8025)

## Option 2: Manual Installation

For development or if you prefer not to use Docker, you can install LeagueLedger manually.

### Step 1: Clone the Repository

```bash
git clone https://github.com/yourusername/leagueledger.git
cd leagueledger
```

### Step 2: Create a Virtual Environment

```bash
python -m venv venv
```

Activate the virtual environment:

=== "Windows"
    ```
    venv\Scripts\activate
    ```

=== "macOS/Linux"
    ```
    source venv/bin/activate
    ```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables

Create a `.env` file in the project root with the following content:

```
SECRET_KEY=your-secure-secret-key
DATABASE_URL=sqlite:///./leagueledger.db

# Email configuration
MAIL_USERNAME=your-email@example.com
MAIL_PASSWORD=your-email-password
MAIL_FROM=noreply@example.com
MAIL_PORT=587
MAIL_SERVER=smtp.example.com
MAIL_TLS=True
MAIL_SSL=False
MAIL_FROM_NAME=LeagueLedger
```

Customize the values as needed.

### Step 5: Initialize the Database

```bash
python -c "from app.db_init import init_db; init_db()"
```

### Step 6: Run the Application

```bash
uvicorn app.main:app --reload
```

The application should now be accessible at [http://localhost:8000](http://localhost:8000).

## Verifying the Installation

After installation, you can verify that LeagueLedger is working correctly by:

1. Opening your browser and navigating to [http://localhost:8000](http://localhost:8000)
2. Creating a new user account via the registration page
3. Logging in with your new credentials

The default admin credentials for the seeded database are:
- Username: `admin`
- Password: `password`

!!! warning "Security Note"
    If using the seeded database in production, make sure to change the default admin password immediately.

## Next Steps

- [Configuration Guide](configuration.md): Configure LeagueLedger for your specific needs
- [Quick Start Guide](quick-start.md): Get started with using LeagueLedger
- [Social Login Setup](../integrations/social-login.md): Set up authentication with social media providers