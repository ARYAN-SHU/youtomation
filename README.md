# Youtomation - Automated YouTube Video Generation System

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue)](https://www.python.org/downloads/)
[![Django 4.2+](https://img.shields.io/badge/Django-4.2%2B-darkgreen)](https://www.djangoproject.com/)
[![PostgreSQL 15+](https://img.shields.io/badge/PostgreSQL-15%2B-blue)](https://www.postgresql.org/)

## 🎥 Overview

Youtomation is a production-ready Django system that **automatically generates, composes, and uploads YouTube videos twice daily** with:

- ✅ **Trending topic discovery** from Google Trends
- ✅ **AI-powered script generation** with customizable templates
- ✅ **Text-to-speech conversion** (gTTS + Coqui TTS)
- ✅ **Stock video integration** (Pexels API)
- ✅ **Professional video composition** with MoviePy
- ✅ **Automated YouTube upload** with OAuth2
- ✅ **Real-time dashboard** with analytics
- ✅ **Rate limiting & security** (JWT + OAuth)
- ✅ **Containerized deployment** (Docker + Render)
- ✅ **CI/CD pipeline** (GitHub Actions)

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+**
- **PostgreSQL 15+**
- **Redis 7+**
- **Docker & Docker Compose** (for containerized setup)
- **FFmpeg** (for video processing)

### 1. Clone Repository

```bash
git clone https://github.com/yourusername/youtomation.git
cd youtomation
```

### 2. Create Virtual Environment

```bash
# Using Python venv
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Or using conda
conda create -n youtomation python=3.11
conda activate youtomation
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your values
nano .env  # or use your preferred editor
```

**Required Variables:**
```
SECRET_KEY=your-secret-key
DEBUG=False
DATABASE_URL=postgresql://user:password@localhost:5432/youtomation_db
REDIS_URL=redis://localhost:6379/0
YOUTUBE_API_KEY=your-api-key
PEXELS_API_KEY=your-api-key
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
```

See [`.env.example`](.env.example) for all available options.

### 5. Setup Database

```bash
# Apply migrations
python manage.py migrate

# Create superuser for admin access
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic --noinput
```

### 6. Start Services

**Option A: Local Development (Separate Terminals)**

```bash
# Terminal 1: Django development server
python manage.py runserver

# Terminal 2: Celery worker
celery -A youtomation_core worker --loglevel=info

# Terminal 3: Celery Beat scheduler
celery -A youtomation_core beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler

# Terminal 4: Redis (if not running as service)
redis-server
```

**Option B: Docker Compose (All Services)**

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down
```

### 7. Access Application

- **Dashboard**: http://localhost:8000
- **Admin Panel**: http://localhost:8000/admin (use created superuser)
- **API**: http://localhost:8000/api/

## 📋 Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Youtomation System                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────────────────────────────────────────┐ │
│  │           Web Application (Django)                   │ │
│  │  - Dashboard & Video Management UI                  │ │
│  │  - Authentication (JWT + OAuth2)                    │ │
│  │  - Rate Limiting & Security                         │ │
│  │  - API Endpoints                                    │ │
│  └──────────────────────────────────────────────────────┘ │
│                           ↓                                │
│  ┌──────────────────────────────────────────────────────┐ │
│  │      Task Queue (Celery + Redis)                    │ │
│  │  - Trending Topics Fetching                         │ │
│  │  - Script Generation                                │ │
│  │  - Text-to-Speech Conversion                        │ │
│  │  - Stock Video Download                             │ │
│  │  - Video Composition                                │ │
│  │  - YouTube Upload                                   │ │
│  │  - Analytics Fetching                               │ │
│  └──────────────────────────────────────────────────────┘ │
│                           ↓                                │
│  ┌──────────────────────────────────────────────────────┐ │
│  │         External Services Integration                │ │
│  │  - YouTube Data API v3                              │ │
│  │  - Google Trends API (pytrends)                     │ │
│  │  - Pexels API (Stock Videos)                        │ │
│  │  - Google Text-to-Speech                            │ │
│  │  - Coqui TTS                                        │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐ │
│  │         Data Layer (PostgreSQL)                     │ │
│  │  - Videos & Tasks                                   │ │
│  │  - Users & Authentication                           │ │
│  │  - Logs & Analytics                                 │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Video Generation Pipeline

```
1. FETCH TRENDING TOPICS
   └─> Google Trends API (13 regions)
       └─> Select trending search

2. GENERATE SCRIPT
   └─> Template-based + AI enhancement
       └─> Validate word count (650-1100)

3. TEXT-TO-SPEECH
   └─> Google TTS or Coqui TTS
       └─> Generate audio (MP3)

4. FETCH STOCK VIDEOS
   └─> Pexels API search
       └─> Download 3+ videos (HD/SD)

5. COMPOSE VIDEO
   └─> MoviePy video composition
       └─> Audio sync + subtitle overlay
       └─> Generate 4-8 min video (1920x1080@30fps)

6. UPLOAD YOUTUBE
   └─> YouTube Data API v3
       └─> OAuth2 authentication
       └─> Monitor upload progress
       └─> Wait for processing

7. FETCH ANALYTICS
   └─> YouTube Analytics API
       └─> Views, likes, comments tracking
       └─> Every 6 hours
```

### Database Schema

Key models:

- **YouTubeVideo**: Master video record with status tracking
- **VideoTask**: Pipeline step tracking with task IDs
- **TrendingTopic**: Trending searches with usage metrics
- **StockVideo**: Downloaded video metadata
- **Subtitle**: Video subtitles with timing
- **ProducerLog**: Comprehensive activity logging
- **CustomUser**: Extended user model with OAuth
- **UserSession**: JWT session tracking

See [models.py](youtomation_app/models.py) for full schema.

## 🔑 API Endpoints

### Authentication

```bash
# Register new user
POST /auth/register
{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "username": "username"
}

# Login
POST /auth/login
{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
# Response:
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "user": {...}
}

# Refresh token
POST /auth/refresh-token
{
  "refresh_token": "eyJ..."
}

# OAuth callback
GET /auth/callback/google/?code=...&state=...
```

### Videos API

```bash
# List videos (paginated)
GET /api/videos/?page=1&status=published&search=trending

# Get video details
GET /api/videos/{video_id}/

# Get video logs
GET /api/videos/{video_id}/logs/

# Get video status
GET /api/videos/{video_id}/status/
```

### Dashboard

```bash
# Dashboard data
GET /dashboard/

# Trending topics
GET /api/trending-topics/

# Statistics
GET /api/stats/
```

## 🔐 Security Features

1. **Authentication**
   - JWT tokens (access + refresh)
   - OAuth2 (Google, GitHub)
   - Session tracking with IP/User-Agent

2. **Authorization**
   - Role-based access control
   - User-specific video access
   - Admin panel restrictions

3. **Rate Limiting**
   - Adaptive per-user tier limits
   - Anonymous: 100 req/hour
   - Authenticated: 1000 req/hour
   - Premium: 10000 req/hour

4. **Data Protection**
   - XSS prevention (bleach sanitization)
   - CSRF protection
   - SQL injection prevention (Django ORM)
   - Input validation & sanitization

5. **Transport Security**
   - HTTPS/TLS required
   - HSTS headers
   - Security headers (CSP, X-Frame-Options)
   - SSL certificate auto-renewal

## 📊 Dashboard Features

### Overview Tab
- Total videos count
- Active & generating count
- Failed videos
- 24-hour statistics
- Recent videos table

### Videos Tab
- Advanced filtering (status, search)
- Pagination
- Real-time updates (30s refresh)
- Bulk actions

### Video Details
- Multi-tab interface (Overview, Script, Logs, YouTube)
- Task status pipeline
- Error messages & logs
- YouTube metadata

### Analytics
- Views & engagement metrics
- Publishing timeline
- Performance trends

## 🛠️ Configuration

### Django Settings

Core settings in [settings.py](youtomation_core/settings.py):

```python
# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'ATOMIC_REQUESTS': True,
    }
}

# Caching
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://localhost:6379/0',
    }
}

# Celery
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/1'
```

### Celery Beat Schedule

Scheduled tasks:

```python
# Generate videos every 12 hours (0:00 and 12:00 UTC)
generate_and_upload_youtube_video

# Fetch analytics every 6 hours
fetch_youtube_analytics
```

### Rate Limiting

Configure in [rate_limiter.py](youtomation_app/utils/rate_limiter.py):

```python
RATE_LIMITS = {
    'anonymous': 100,      # per hour
    'authenticated': 1000,
    'premium': 10000,
}
```

## 📦 Deployment

### Docker

Build and run locally:

```bash
# Build image
docker build -t youtomation:latest .

# Run container
docker run -p 8000:8000 \
  -e DATABASE_URL=postgresql://... \
  -e REDIS_URL=redis://... \
  youtomation:latest
```

### Docker Compose

Full stack (development):

```bash
docker-compose up -d
```

Services:
- PostgreSQL 15
- Redis 7
- Django (Gunicorn)
- Celery Worker
- Celery Beat
- Nginx

### Production

See [DEPLOYMENT.md](DEPLOYMENT.md) for full Render deployment guide.

## 🧪 Testing

Run tests:

```bash
# All tests
pytest

# With coverage
pytest --cov=youtomation_app --cov-report=html

# Specific test file
pytest tests/test_services.py -v

# With markers
pytest -m "not slow" --tb=short
```

## 📚 Project Structure

```
youtomation/
├── manage.py
├── requirements.txt
├── .env.example
├── Dockerfile
├── docker-compose.yml
├── nginx.conf
├── render.yaml
├── pytest.ini
├── .github/
│   └── workflows/
│       └── deploy.yml           # CI/CD pipeline
│
├── youtomation_core/
│   ├── settings.py              # Django configuration
│   ├── celery.py                # Celery setup
│   ├── urls.py                  # Main URL routing
│   └── wsgi.py                  # WSGI application
│
├── youtomation_app/
│   ├── models.py                # Core models
│   ├── models_auth.py           # Authentication models
│   ├── views.py                 # Dashboard & video views
│   ├── views_auth.py            # Auth endpoints
│   ├── urls.py                  # App URL routing
│   ├── tasks.py                 # Celery tasks
│   ├── admin.py                 # Django admin
│   │
│   ├── services/
│   │   ├── trending_topics.py   # Google Trends
│   │   ├── script_generator.py  # Script generation
│   │   ├── text_to_speech.py    # TTS engines
│   │   ├── stock_videos.py      # Pexels API
│   │   ├── video_generator.py   # MoviePy composer
│   │   └── youtube_uploader.py  # YouTube API
│   │
│   ├── utils/
│   │   ├── auth_backend.py      # JWT + OAuth
│   │   ├── rate_limiter.py      # Rate limiting
│   │   ├── security.py          # Sanitization
│   │   └── exceptions_handler.py # Error handling
│   │
│   └── templates/
│       └── youtomation_app/
│           ├── base.html        # Base template
│           ├── dashboard.html   # Dashboard
│           ├── videos_list.html # Videos table
│           └── video_detail.html # Video page
│
└── tests/
    ├── test_services.py
    ├── test_tasks.py
    ├── test_auth.py
    └── test_views.py
```

## 🐛 Troubleshooting

### Common Issues

**Database connection error:**
```bash
# Check PostgreSQL is running
psql postgresql://user:password@localhost:5432/dbname

# Verify DATABASE_URL in .env
echo $DATABASE_URL
```

**Redis connection error:**
```bash
# Check Redis is running
redis-cli ping  # Should return "PONG"
```

**Celery tasks not processing:**
```bash
# Check worker is running
celery -A youtomation_core inspect active

# Check Beat scheduler
celery -A youtomation_core inspect scheduled
```

**Static files not serving:**
```bash
# Collect static files
python manage.py collectstatic --noinput --clear

# Check STATIC_ROOT directory
ls -la /app/staticfiles/
```

## 📝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/new-feature`
3. Make changes and test: `pytest`
4. Commit with clear message: `git commit -m "Add new feature"`
5. Push: `git push origin feature/new-feature`
6. Create Pull Request

## 📜 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🤝 Support

- **Issues**: GitHub Issues
- **Discussions**: GitHub Discussions
- **Email**: support@youtomation.com
- **Docs**: [Full Documentation](DEPLOYMENT.md)

## 🎯 Roadmap

- [ ] Advanced AI script generation with GPT integration
- [ ] Multi-language support
- [ ] Custom video templates
- [ ] Analytics dashboard improvements
- [ ] Mobile app
- [ ] API webhooks
- [ ] Batch video generation
- [ ] Video editing dashboard

## 📈 Performance

Typical video generation metrics:

- **Script Generation**: 5-10 seconds
- **Text-to-Speech**: 30-60 seconds
- **Stock Video Download**: 2-5 minutes
- **Video Composition**: 3-8 minutes (depending on length)
- **YouTube Upload**: 2-10 minutes (depending on file size)
- **Total Time**: 10-35 minutes per video

## 🔄 Update Guide

To update to latest version:

```bash
# Pull latest changes
git pull origin main

# Install new dependencies
pip install -r requirements.txt

# Apply migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Restart services
docker-compose restart
```

---

**Built with ❤️ for YouTube content creators**
