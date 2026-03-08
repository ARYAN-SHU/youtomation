# Youtomation - Production Deployment Guide

## Overview

This guide covers deployment of Youtomation to a production environment using Docker, Render.com, and GitHub Actions CI/CD.

## Architecture

The production system consists of:

- **Web Service**: Django + Gunicorn running on Render
- **Celery Worker**: Background task processing (video generation, uploads)
- **Celery Scheduler**: Task scheduling (every 12 hours for video generation)
- **Database**: PostgreSQL 15 on Render
- **Cache/Broker**: Redis on Render
- **Reverse Proxy**: Nginx with SSL/TLS termination
- **CI/CD**: GitHub Actions for automated testing and deployment

## Prerequisites

Before deploying, ensure you have:

1. **GitHub Repository**: Push your code to GitHub
2. **Render Account**: Create account at https://render.com
3. **API Keys**: Collect all required API keys (see `.env.example`)
4. **Domain (Optional)**: Domain name for custom URL
5. **Git Configured**: Local git setup for version control

## Step 1: Prepare API Credentials

### 1.1 YouTube API

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create new project
3. Enable YouTube Data API v3
4. Create OAuth 2.0 credentials (Desktop application)
5. Download credentials JSON
6. Note down: `Client ID`, `Client Secret`

### 1.2 Pexels API

1. Visit [Pexels API](https://www.pexels.com/api/)
2. Create account and application
3. Copy API key

### 1.3 Google OAuth

1. In Google Cloud Console, use same project as YouTube API
2. Create OAuth consent screen (External user type)
3. Add scopes: email, profile, openid
4. Create OAuth 2.0 Credentials (Web application)
5. Add authorized redirect URIs:
   - `https://yourdomain.com/auth/callback/google/`
   - `https://yourdomain.onrender.com/auth/callback/google/`
6. Note: `Client ID`, `Client Secret`

### 1.4 GitHub OAuth

1. Go to [GitHub Settings > Developer Settings > OAuth Apps](https://github.com/settings/developers)
2. Create new OAuth App
3. Application name: Youtomation
4. Homepage URL: `https://yourdomain.com`
5. Authorization callback URL: `https://yourdomain.com/auth/callback/github/`
6. Note: `Client ID`, `Client Secret`

### 1.5 Email (Gmail SMTP)

1. Use Gmail account or create new one
2. Enable 2-Factor Authentication
3. Generate App Password: https://myaccount.google.com/apppasswords
4. Note: Email address and App Password

### 1.6 Secret Key

Generate a secure Django secret key:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

## Step 2: GitHub Repository Setup

### 2.1 Create Repository

```bash
git init
git remote add origin https://github.com/yourusername/youtomation.git
git branch -M main
git add .
git commit -m "Initial commit: Youtomation production-ready"
git push -u origin main
```

### 2.2 Create GitHub Secrets

Navigate to: Repository > Settings > Secrets and variables > Actions

Create the following secrets:

```
RENDER_DEPLOY_HOOK=https://api.render.com/deploy/srv-xxxxx?key=xxxxx
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/T00000000/B00000000/XXXX
```

Get `RENDER_DEPLOY_HOOK` after creating the Render service (see Step 3).

## Step 3: Deploy to Render

### 3.1 Connect GitHub Repository

1. Log in to [Render Dashboard](https://dashboard.render.com)
2. Click "New +"
3. Select "Web Service"
4. Connect GitHub repository
5. Select `youtomation` repository

### 3.2 Configure Web Service

**Basic Settings:**
- Name: `youtomation-api`
- Environment: `Docker`
- Region: `Oregon` (or closest to your users)
- Plan: `Standard` (or higher)

**Build Settings:**
- Docker Context: `./`
- Dockerfile Path: `./Dockerfile`

**Environment Variables:**

Add all variables from `.env.example`. These can be set via:

1. **Dashboard UI**: Add each variable individually
2. **render.yaml**: Use Infrastructure as Code (recommended)

Key variables to set:

```
YOUTUBE_API_KEY=xxxx
PEXELS_API_KEY=xxxx
GOOGLE_CLIENT_ID=xxxx
GOOGLE_CLIENT_SECRET=xxxx
GITHUB_CLIENT_ID=xxxx
GITHUB_CLIENT_SECRET=xxxx
SECRET_KEY=xxxx
EMAIL_HOST_PASSWORD=xxxx
```

### 3.3 Create Database

1. Click "New +"
2. Select "PostgreSQL"
3. Name: `youtomation-db`
4. Plan: `Standard`
5. PostgreSQL Version: `15`

    Render will provide `DATABASE_URL` automatically.

### 3.4 Create Redis Cache

1. Click "New +"
2. Select "Redis"
3. Name: `youtomation-cache`
4. Plan: `Starter` (or higher for production)
5. Eviction Policy: `allkeys-lru`

    Render will provide `REDIS_URL` automatically.

### 3.5 Create Celery Worker

1. Click "New +"
2. Select "Background Worker"
3. Name: `youtomation-worker`
4. Connect same GitHub repository
5. Start Command: `celery -A youtomation_core worker --loglevel=info --concurrency=4`
6. Plan: `Standard`
7. Attach same database and Redis

### 3.6 Create Celery Scheduler

1. Click "New +"
2. Select "Background Worker"
3. Name: `youtomation-scheduler`
4. Connect same GitHub repository
5. Start Command: `celery -A youtomation_core beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler`
6. Plan: `Starter`
7. Attach same database and Redis

### 3.7 Deploy Hook

After creating the web service:

1. Go to Web Service settings
2. Copy "Deploy Hook" URL
3. Add to GitHub Secrets as `RENDER_DEPLOY_HOOK`

## Step 4: Configure SSL/TLS

### 4.1 Render-Provided SSL

Render automatically provides free SSL certificates for all `.onrender.com` domains.

### 4.2 Custom Domain SSL

If using custom domain:

1. Update domain DNS records to point to Render
2. Render will automatically provision Let's Encrypt certificate
3. SSL is free and auto-renews

Render provides CNAME record in service settings.

## Step 5: Post-Deployment Tasks

### 5.1 Database Migrations

After first deployment, run migrations:

```bash
# Via Render shell (Web Service > Shell)
python manage.py migrate
```

Or build a custom command in Docker:

```dockerfile
RUN python manage.py migrate
```

### 5.2 Create Superuser

```bash
# Via Render shell
python manage.py createsuperuser
```

Then access Django Admin: `https://yourdomain.com/admin/`

### 5.3 Collect Static Files

Already included in Dockerfile:

```dockerfile
RUN python manage.py collectstatic --noinput
```

### 5.4 Schedule Celery Tasks

```bash
# Via Render shell
python manage.py shell
```

```python
from django_celery_beat.models import PeriodicTask, CrontabSchedule
from datetime import timedelta

# Video generation every 12 hours
schedule, _ = CrontabSchedule.objects.get_or_create(hour='*/12', minute='0')
PeriodicTask.objects.get_or_create(
    name='Generate and Upload YouTube Videos',
    task='youtomation_app.tasks.generate_and_upload_youtube_video',
    crontab=schedule,
    defaults={'enabled': True}
)

# Analytics fetching every 6 hours
schedule, _ = CrontabSchedule.objects.get_or_create(hour='*/6', minute='0')
PeriodicTask.objects.get_or_create(
    name='Fetch YouTube Analytics',
    task='youtomation_app.tasks.fetch_youtube_analytics',
    crontab=schedule,
    defaults={'enabled': True}
)
```

## Step 6: Configure GitHub Actions

### 6.1 Required Secrets

GitHub Actions needs:

```
RENDER_DEPLOY_HOOK=https://api.render.com/deploy/srv-xxxxx?key=xxxxx
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/T00000000/B00000000/XXXX (optional)
```

### 6.2 CI/CD Pipeline

Workflow automatically:

1. Tests code on every push
2. Builds Docker image
3. Scans for vulnerabilities
4. Deploys to Render (only main branch)
5. Runs health checks
6. Notifies on Slack (if configured)

## Step 7: Monitoring & Maintenance

### 7.1 Log Monitoring

1. **Web Service Logs**: Dashboard > Web Service > Logs
2. **Worker Logs**: Dashboard > Worker > Logs
3. **Sentry Integration** (optional): Add `SENTRY_DSN` for error tracking

### 7.2 Database Backups

Render automatically backs up PostgreSQL:

- Enable automated backups in database settings
- Retain for 7-30 days
- Manual backup available via dashboard

### 7.3 Redis Persistence

Already configured in `docker-compose.yml`:

```yaml
appendonly yes
appendfsync everysec
```

### 7.4 Scaling

**Increase Capacity:**

1. Web Service: Upgrade plan (Standard → Pro → Pro+)
2. Celery Worker: Increase concurrency in command
3. Database: Upgrade from Standard
4. Redis: Upgrade to larger capacity

**Multiple Workers:**

Create multiple `Background Worker` services with same command for horizontal scaling.

## Step 8: Troubleshooting

### 8.1 Deployment Failed

Check logs:

```bash
# View full logs
Render Dashboard > Service > Logs

# Check build output for errors
Render Dashboard > Service > Build Logs

# Review recent commits for breaking changes
git diff HEAD~1
```

### 8.2 Database Connection Issues

```bash
# Verify DATABASE_URL
Render Dashboard > Web Service > Environment Variables

# Check database status
Render Dashboard > PostgreSQL > Settings

# Test connection from shell
python manage.py shell
from django.db import connection
connection.ensure_connection()
```

### 8.3 API Keys Not Working

1. Verify keys in Render environment variables
2. Check API service status (YouTube, Pexels, etc.)
3. Verify redirect URIs match exactly
4. Check IP allowlist (if configured)

### 8.4 Celery Tasks Not Running

```bash
# Check if Beat scheduler is running
Render Dashboard > Celery Scheduler > Status

# Check if Worker is running
Render Dashboard > Celery Worker > Status

# View task status
python manage.py shell
from celery.result import AsyncResult
AsyncResult('task-id').status
```

## Step 9: Production Checklist

Before going live, verify:

- [ ] All environment variables set correctly
- [ ] SSL certificate installed and auto-renewal configured
- [ ] Database backups enabled
- [ ] Celery tasks scheduled and working
- [ ] Static files serving correctly
- [ ] Email sending tested
- [ ] API integrations validated
- [ ] Rate limiting configured
- [ ] Error logging setup (Sentry)
- [ ] Monitoring alerts configured
- [ ] Team access configured
- [ ] Disaster recovery plan documented

## Step 10: Continuous Improvement

### Performance Optimization

1. **Caching**: Implement Redis caching for frequently accessed data
2. **CDN**: Use Cloudflare or similar for static file distribution
3. **Database**: Add indexes to frequently queried fields
4. **Async Tasks**: Optimize Celery task execution times

### Security Updates

1. **Weekly**: Check dependency updates
2. **Monthly**: Security audit and penetration testing
3. **Real-time**: Sentry alerts for critical errors
4. **Quarterly**: Full security audit

### Capacity Planning

1. Monitor Render metrics dashboard
2. Plan for video generation growth
3. Scale Celery workers as needed
4. Upgrade database as data grows

## Support & Resources

- **Render Docs**: https://render.com/docs
- **Django Docs**: https://docs.djangoproject.com
- **Celery Docs**: https://docs.celeryproject.org
- **YouTube API**: https://developers.google.com/youtube
- **PostgreSQL**: https://www.postgresql.org/docs/

## Deployment Commands Quick Reference

```bash
# Local testing
docker-compose up -d

# Build Docker image
docker build -t youtomation:latest .

# Push to Docker registry
docker push yourusername/youtomation:latest

# Deploy via GitHub
git push origin main  # Triggers CI/CD

# Manual Render deployment
curl -X POST https://api.render.com/deploy/srv-xxxxx?key=xxxxx

# SSH into Render service
render connect service-name

# View live logs
render logs service-name --lines 100 --follow
```
