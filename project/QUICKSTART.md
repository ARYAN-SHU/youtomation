# Quick Start - Local Development Setup

This guide covers setting up Youtomation for local development.

## 5-Minute Setup

### Prerequisites

Ensure you have installed:
- Python 3.11+ ([download](https://www.python.org/downloads/))
- PostgreSQL 15+ ([download](https://www.postgresql.org/download/))
- Redis ([installation guide](https://redis.io/download))
- Git

### Step 1: Clone & Setup

```bash
# Clone repository
git clone https://github.com/yourusername/youtomation.git
cd youtomation

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit with your values (minimal setup)
# Required:
# - SECRET_KEY (generate with: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")
# - DATABASE_URL=postgresql://localhost/youtomation_db
# - REDIS_URL=redis://localhost:6379/0
# - YOUTUBE_API_KEY, PEXELS_API_KEY, etc. (get from service UIs)
```

### Step 3: Database Setup

```bash
# Create database (PostgreSQL)
createdb youtomation_db

# Run migrations
python manage.py migrate

# Create admin user
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic --noinput
```

### Step 4: Run Services

**In separate terminals:**

```bash
# Terminal 1: Django
python manage.py runserver

# Terminal 2: Celery Worker
celery -A youtomation_core worker --loglevel=info

# Terminal 3: Celery Beat
celery -A youtomation_core beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

### Step 5: Access Application

- **Dashboard**: http://localhost:8000
- **Admin**: http://localhost:8000/admin
- **API**: http://localhost:8000/api/

Done! ✅

---

## Get API Keys

### YouTube API

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create project
3. Enable YouTube Data API v3
4. Create OAuth 2.0 credentials (Desktop app)
5. Copy Client ID and Secret to `.env`

### Pexels API

1. Visit [pexels.com/api](https://www.pexels.com/api/)
2. Create account and request API key
3. Copy to `.env`

### Google OAuth

1. Use same Google Cloud project
2. Create OAuth 2.0 credentials (Web application)
3. Add redirect URI: `http://localhost:8000/auth/callback/google/`
4. Copy Client ID and Secret to `.env`

### GitHub OAuth (Optional)

1. Go to GitHub Settings > Developer Settings > OAuth Apps
2. Create new OAuth App
3. Set Authorization callback URL: `http://localhost:8000/auth/callback/github/`
4. Copy Client ID and Secret to `.env`

---

## Docker Development

If you prefer Docker:

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f django

# Stop services
docker-compose down
```

---

## Common Commands

```bash
# Run tests
pytest

# Create new app
python manage.py startapp myapp

# Make migrations
python manage.py makemigrations

# Database shell
python manage.py dbshell

# Django shell
python manage.py shell

# Check dependencies for updates
pip list --outdated

# Create superuser
python manage.py createsuperuser

# Check Celery workers
celery -A youtomation_core inspect active

# Monitor Celery tasks
celery -A youtomation_core events
```

---

## Troubleshooting

### Database Connection Error

```bash
# Check PostgreSQL is running
psql -V

# Create database if not exists
createdb youtomation_db

# Check connection
psql postgresql://localhost/youtomation_db
```

### Redis Connection Error

```bash
# Check Redis is running
redis-cli ping

# Start Redis (if not running)
redis-server
```

### Permission Denied Error

```bash
# On Linux/Mac, give execution permission
chmod +x manage.py
chmod -R 755 youtomation_app/
```

### Module Not Found Error

```bash
# Ensure virtual environment is activated
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Reinstall dependencies
pip install -r requirements.txt
```

### Celery Tasks Not Running

```bash
# Check Beat is running
celery -A youtomation_core inspect scheduled

# Check worker is listening
celery -A youtomation_core inspect active_queues

# Clear task cache
celery -A youtomation_core purge
```

---

## Next Steps

1. **Read Full Docs**: See [README.md](README.md)
2. **Learn Architecture**: See [ARCHITECTURE.md](ARCHITECTURE.md)
3. **Deploy to Production**: See [DEPLOYMENT.md](DEPLOYMENT.md)
4. **Contributing**: See [CONTRIBUTING.md](CONTRIBUTING.md)

---

## Need Help?

- Create issue on GitHub
- Check logs: `docker-compose logs`
- Join discussions on GitHub
- Email: support@youtomation.com

Happy coding! 🚀
