# Docker Deployment

This guide covers deploying LeagueLedger using Docker and Docker Compose, which is the recommended approach for both development and production environments.

## Prerequisites

Before deploying LeagueLedger with Docker, ensure you have:

- **Docker**: Version 20.10.0 or higher
- **Docker Compose**: Version 2.0.0 or higher
- **Git**: For cloning the repository (optional)
- **Basic Docker knowledge**: Understanding of containers and Docker Compose

## Quick Deployment

For a quick deployment using default settings:

```bash
# Clone the repository
git clone https://github.com/yourusername/leagueledger.git
cd leagueledger

# Create and configure the environment file
cp .env.example .env
# Edit the .env file with your preferred text editor

# Start the containers
docker-compose up -d
```

## Docker Compose Configuration

LeagueLedger's Docker setup includes multiple services defined in `docker-compose.yml`:

### Services Overview

- **app**: The main LeagueLedger application
- **db**: MySQL database for persistent storage
- **phpmyadmin**: Web interface for database management
- **mailpit**: Email testing service that captures all outgoing emails

### Important Configuration Parameters

#### Application Service

```yaml
app:
  build: .
  container_name: pubquiz_app
  restart: unless-stopped
  depends_on:
    db:
      condition: service_healthy
  environment:
    # Database configuration
    DB_HOST: "db"
    DB_PORT: "3306"
    DB_NAME: "pubquiz_db"
    DB_USER: "pubquiz_user"
    DB_PASS: "pubquiz_pass"
    # ... other environment variables
  ports:
    - "8000:8000"
  volumes:
    - ./:/app:delegated
```

#### Database Service

```yaml
db:
  image: mysql:8.0
  container_name: pubquiz_mysql
  restart: always
  environment:
    MYSQL_DATABASE: "pubquiz_db"
    MYSQL_USER: "pubquiz_user"
    MYSQL_PASSWORD: "pubquiz_pass"
    MYSQL_ROOT_PASSWORD: "root_pass"
  ports:
    - "3306:3306"
  # ... other settings
```

## Environment Configuration

The `.env` file contains important configuration options:

```
# Database Configuration
DATABASE_URL=mysql+pymysql://pubquiz_user:pubquiz_pass@db:3306/pubquiz_db

# Security
SECRET_KEY=your-secure-secret-key

# Email Configuration
MAIL_USERNAME=your-email@example.com
MAIL_PASSWORD=your-email-password
MAIL_FROM=noreply@example.com
MAIL_PORT=587
MAIL_SERVER=smtp.example.com
MAIL_TLS=True
MAIL_SSL=False
MAIL_FROM_NAME=LeagueLedger

# OAuth Configuration
# ... provider-specific settings
```

## Production Deployment Considerations

For production deployments, make the following adjustments:

### 1. Secure Database Configuration

Update the MySQL environment variables in `docker-compose.yml`:

```yaml
db:
  environment:
    MYSQL_DATABASE: "your_production_db"
    MYSQL_USER: "your_production_user"
    MYSQL_PASSWORD: "your_strong_password"
    MYSQL_ROOT_PASSWORD: "your_very_strong_root_password"
```

### 2. Persistent Storage

Add volumes for persistent data storage:

```yaml
db:
  volumes:
    - leagueledger_db_data:/var/lib/mysql

volumes:
  leagueledger_db_data:
```

### 3. Email Configuration

For production, replace Mailpit with a real SMTP server in your `.env` file:

```
MAIL_USERNAME=your-production-email@yourdomain.com
MAIL_PASSWORD=your-email-password
MAIL_FROM=noreply@yourdomain.com
MAIL_PORT=587
MAIL_SERVER=smtp.yourdomain.com
MAIL_TLS=True
MAIL_SSL=False
MAIL_FROM_NAME=LeagueLedger
```

### 4. HTTPS Setup

For secure access, you should add an HTTPS proxy such as Traefik or Nginx:

```yaml
services:
  app:
    # ... existing configuration
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.leagueledger.rule=Host(`leagueledger.yourdomain.com`)"
      - "traefik.http.routers.leagueledger.entrypoints=websecure"
      - "traefik.http.routers.leagueledger.tls.certresolver=myresolver"

  traefik:
    image: traefik:v2.9
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - "/var/run/docker.sock:/var/run/docker.sock:ro"
      - "./traefik/config:/etc/traefik"
      - "./traefik/letsencrypt:/letsencrypt"
    # ... additional Traefik configuration
```

### 5. OAuth Callback URLs

Update the OAuth provider configuration in your `.env` file to use your production domain:

```
# OAuth Callback URLs
LEAGUELEDGER_BASE_URL=https://leagueledger.yourdomain.com
```

## Container Management

### Starting Services

```bash
# Start all services in the background
docker-compose up -d

# Start a specific service
docker-compose up -d app
```

### Stopping Services

```bash
# Stop all services
docker-compose down

# Stop services without removing containers
docker-compose stop
```

### Viewing Logs

```bash
# View logs for all services
docker-compose logs

# Follow logs for a specific service
docker-compose logs -f app

# See the last 100 lines of logs
docker-compose logs --tail=100 app
```

### Restarting Services

```bash
# Restart all services
docker-compose restart

# Restart a specific service
docker-compose restart app
```

## Database Management

### Accessing the Database

You can access the database using phpMyAdmin at:
```
http://localhost:8001
```

Or connect directly to MySQL:
```bash
docker-compose exec db mysql -upubquiz_user -ppubquiz_pass pubquiz_db
```

### Database Backups

Create a backup:
```bash
docker-compose exec db mysqldump -uroot -proot_pass pubquiz_db > backup_$(date +%Y-%m-%d_%H-%M-%S).sql
```

Restore a backup:
```bash
cat backup_file.sql | docker-compose exec -T db mysql -uroot -proot_pass pubquiz_db
```

## Troubleshooting

### Common Issues

#### Container Fails to Start

Check the logs:
```bash
docker-compose logs app
```

#### Database Connection Issues

Verify the database is running and healthy:
```bash
docker-compose ps db
```

Ensure environment variables are correct:
```bash
docker-compose exec app env | grep DB_
```

#### Email Not Working

Check Mailpit interface at `http://localhost:8025` to see if emails are being captured.

If using a real SMTP server, verify credentials and connectivity:
```bash
docker-compose exec app python -c "from app.utils.mail import test_mail_connection; test_mail_connection()"
```

## Updating LeagueLedger

To update to a newer version:

```bash
# Pull the latest changes
git pull

# Rebuild and restart containers
docker-compose up -d --build
```

## Scaling for Production

For high-traffic production environments, consider:

1. **Horizontal Scaling**: Run multiple instances behind a load balancer
2. **Database Scaling**: Move the database to a managed service
3. **Redis Cache**: Add a Redis container for improved performance
4. **CDN Integration**: Use a CDN for static assets

A more advanced `docker-compose.prod.yml` might include:

```yaml
version: "3.9"

services:
  app:
    deploy:
      replicas: 3
    environment:
      REDIS_URL: "redis://redis:6379/0"
  
  redis:
    image: redis:7.0
    volumes:
      - redis_data:/data

  db:
    volumes:
      - db_data:/var/lib/mysql

volumes:
  db_data:
  redis_data:
```

## Next Steps

- [Production Setup](production.md): Additional production environment considerations
- [Scaling](scaling.md): Detailed guidance on scaling LeagueLedger
- [Backup & Recovery](backup-recovery.md): Comprehensive backup strategies