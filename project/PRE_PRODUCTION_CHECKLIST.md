# 🚀 Pre-Production Checklist & Final Setup Guide

## Overview

This checklist covers all steps needed to prepare Youtomation for production deployment. Use this guide in order, checking off items as you complete them.

---

## ✅ Phase 1: Code Preparation (Week −1)

### Code Review
- [ ] Review all Python files for security issues
- [ ] Ensure no hardcoded secrets in code
- [ ] Check all API calls have proper error handling
- [ ] Verify all user inputs are validated
- [ ] Review database queries for N+1 problems
- [ ] Check rate limiting is working correctly

### Testing
- [ ] Run full test suite: `pytest --cov=youtomation_app`
- [ ] Coverage should be 70%+ 
- [ ] All tests passing ✓
- [ ] Integration tests passing ✓
- [ ] Load testing completed
- [ ] Security testing completed

### Code Quality
- [ ] Linting passes: `flake8 youtomation_app youtomation_core`
- [ ] Type checking passes: `mypy youtomation_app youtomation_core`
- [ ] Code formatted with black
- [ ] No TODO/FIXME comments left
- [ ] All functions documented
- [ ] Requirements.txt is up to date

### Documentation Review
- [ ] README.md complete and accurate
- [ ] DEPLOYMENT.md covers all steps
- [ ] QUICKSTART.md tested
- [ ] ARCHITECTURE.md up to date
- [ ] API endpoints documented
- [ ] Error codes documented
- [ ] Configuration options documented

---

## ✅ Phase 2: Environment Setup (Day -2)

### Update Configuration Files

**`.env.example`**: Already provided ✓
- [ ] Review all variables
- [ ] Mark required vs optional
- [ ] Add validation descriptions

**`settings.py`**:
- [ ] `DEBUG = False` (production)
- [ ] `ALLOWED_HOSTS` includes your domain
- [ ] `SECRET_KEY` is unique and secure
- [ ] Database is PostgreSQL
- [ ] Cache backend is Redis
- [ ] HTTPS enforcement enabled
- [ ] Security middleware enabled
- [ ] Logging configured

**`docker-compose.yml`** (for production reference):
- [ ] Review all service configurations
- [ ] Ensure health checks are correct
- [ ] Check volume mounts are appropriate
- [ ] Verify environment variables
- [ ] Database persistence enabled
- [ ] Redis persistence enabled

**`nginx.conf`**:
- [ ] SSL configuration correct
- [ ] Rate limiting zones defined
- [ ] Upstream Django server configured
- [ ] Static files paths correct
- [ ] Gzip compression enabled
- [ ] Security headers present

**`Dockerfile`**:
- [ ] Python version current (3.11+)
- [ ] Non-root user Django created
- [ ] Health check endpoint present
- [ ] Multi-stage build optimized
- [ ] Dependencies installed correctly

**`render.yaml`**:
- [ ] Web service configured
- [ ] Worker services configured
- [ ] Database instance defined
- [ ] Redis instance defined
- [ ] Environment variables mapped
- [ ] Services have proper dependencies

### GitHub Configuration

- [ ] Repository is private (if sensitive)
- [ ] `.gitignore` excludes secrets
- [ ] `.env` file is NOT committed
- [ ] `*.pyc` files excluded
- [ ] Virtual environment excluded
- [ ] `.DS_Store` / `Thumbs.db` excluded

### GitHub Actions Setup

**`.github/workflows/deploy.yml`**: Already provided ✓
- [ ] Workflow syntax validated
- [ ] Test stage configured correctly
- [ ] Build stage configured correctly
- [ ] Deploy stage has correct hook URL

---

## ✅ Phase 3: API Credentials (Day -1)

### Collect & Validate API Keys

**YouTube API**:
- [ ] Google Cloud project created
- [ ] YouTube Data API v3 enabled
- [ ] OAuth 2.0 credentials created (Desktop)
- [ ] Note: `YOUTUBE_CLIENT_ID`
- [ ] Note: `YOUTUBE_CLIENT_SECRET`
- [ ] Note: `YOUTUBE_API_KEY`
- [ ] Test authentication works locally

**Pexels API**:
- [ ] Account created at pexels.com
- [ ] Application created
- [ ] Note: `PEXELS_API_KEY`
- [ ] Test API call works: `curl https://api.pexels.com/v1/search?query=trending&per_page=1 -H "Authorization: YOUR_KEY"`

**Google OAuth** (for user login):
- [ ] In same Google Cloud project as YouTube
- [ ] OAuth consent screen created (External)
- [ ] Scopes: email, profile, openid
- [ ] OAuth 2.0 credentials created (Web)
- [ ] Authorized redirect URIs:
  - [ ] `http://localhost:8000/auth/callback/google/` (local)
  - [ ] `https://yourdomain.com/auth/callback/google/` (prod)
  - [ ] `https://yourdomain.onrender.com/auth/callback/google/` (Render)
- [ ] Note: `GOOGLE_CLIENT_ID`
- [ ] Note: `GOOGLE_CLIENT_SECRET`
- [ ] Test OAuth flow works

**GitHub OAuth** (for user login):
- [ ] Go to GitHub Settings > Developer Settings > OAuth Apps
- [ ] Create new OAuth App
- [ ] Application name: Youtomation
- [ ] Homepage URL: `https://yourdomain.com`
- [ ] Authorization callback URL:
  - [ ] `http://localhost:8000/auth/callback/github/` (local)
  - [ ] `https://yourdomain.com/auth/callback/github/` (prod)
  - [ ] `https://yourdomain.onrender.com/auth/callback/github/` (Render)
- [ ] Note: `GITHUB_CLIENT_ID`
- [ ] Note: `GITHUB_CLIENT_SECRET`
- [ ] Test OAuth flow works

**Email (Gmail SMTP)**:
- [ ] Gmail account created or selected
- [ ] 2-Factor Authentication enabled
- [ ] App Password generated: https://myaccount.google.com/apppasswords
- [ ] Note: `EMAIL_HOST_USER` (email address)
- [ ] Note: `EMAIL_HOST_PASSWORD` (app password)
- [ ] Test email sending works locally

**Django Secret Key**:
- [ ] Generate unique key: `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`
- [ ] Note: `SECRET_KEY` (save in Render secrets, NOT in code)

### Secrets Security

- [ ] No secrets committed to git
- [ ] No secrets in `.env` file in repo
- [ ] `.env` file in `.gitignore`
- [ ] `.env.example` has dummy values only
- [ ] All secrets will be entered via Render dashboard
- [ ] Never share API keys in emails/Slack

---

## ✅ Phase 4: Render Setup (Day 0)

### Create Render Services

**Step 1: PostgreSQL Database**
- [ ] Log in to https://render.com
- [ ] Click "New +"
- [ ] Select PostgreSQL
- [ ] Name: `youtomation-db`
- [ ] Plan: Standard
- [ ] Version: 15
- [ ] Region: closest to users
- [ ] Copy connection string: `DATABASE_URL`

**Step 2: Redis Cache**
- [ ] Click "New +"
- [ ] Select Redis
- [ ] Name: `youtomation-cache`
- [ ] Plan: Starter
- [ ] Eviction Policy: `allkeys-lru`
- [ ] Copy connection string: `REDIS_URL`

**Step 3: Web Service (API)**
- [ ] Click "New +"
- [ ] Select Web Service
- [ ] Connect GitHub repository: `youtomation`
- [ ] Name: `youtomation-api`
- [ ] Environment: Docker
- [ ] Region: closest to users
- [ ] Plan: Standard (minimum for production)
- [ ] Build Command: Default (uses Dockerfile)
- [ ] Start Command: `gunicorn youtomation_core.wsgi --workers 4 --timeout 120`

**Add Environment Variables to Web Service**:
- [ ] `DEBUG=False`
- [ ] `ALLOWED_HOSTS=yourdomain.com,youtomation-api.onrender.com`
- [ ] `SECURE_SSL_REDIRECT=True`
- [ ] `SESSION_COOKIE_SECURE=True`
- [ ] `CSRF_COOKIE_SECURE=True`
- [ ] Database URL (auto-linked)
- [ ] Redis URL (auto-linked)
- [ ] API keys (see Phase 3):
  - [ ] `SECRET_KEY`
  - [ ] `YOUTUBE_API_KEY`
  - [ ] `YOUTUBE_CLIENT_ID`
  - [ ] `YOUTUBE_CLIENT_SECRET`
  - [ ] `PEXELS_API_KEY`
  - [ ] `GOOGLE_CLIENT_ID`
  - [ ] `GOOGLE_CLIENT_SECRET`
  - [ ] `GITHUB_CLIENT_ID`
  - [ ] `GITHUB_CLIENT_SECRET`
  - [ ] `EMAIL_HOST_PASSWORD`

**Get Deploy Hook URL**:
- [ ] Go to Web Service settings
- [ ] Copy "Deploy Hook" URL
- [ ] Save as GitHub secret: `RENDER_DEPLOY_HOOK`

**Step 4: Celery Worker**
- [ ] Click "New +"
- [ ] Select Background Worker
- [ ] Connect same GitHub repository
- [ ] Name: `youtomation-worker`
- [ ] Environment: Docker
- [ ] Start Command: `celery -A youtomation_core worker --loglevel=info --concurrency=4`
- [ ] Plan: Standard
- [ ] Link database and Redis

**Step 5: Celery Scheduler (Beat)**
- [ ] Click "New +"
- [ ] Select Background Worker
- [ ] Connect same GitHub repository
- [ ] Name: `youtomation-scheduler`
- [ ] Environment: Docker
- [ ] Start Command: `celery -A youtomation_core beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler`
- [ ] Plan: Starter
- [ ] Link database and Redis

### Configure GitHub Secrets

In GitHub repository settings > Secrets:
- [ ] `RENDER_DEPLOY_HOOK` (from Web Service)
- [ ] `SLACK_WEBHOOK_URL` (optional, for notifications)

### Verify Render Services

- [ ] All services created
- [ ] All services have environment variables
- [ ] Database is initialized
- [ ] Redis is initialized
- [ ] Services linked together

---

## ✅ Phase 5: Initial Deployment (Day 1)

### Deploy Code

**Option A: Automatic via GitHub**
1. [ ] Commit all files to GitHub: `git add . && git commit -m "Production deployment"`
2. [ ] Push to main branch: `git push origin main`
3. [ ] GitHub Actions automatically:
   - [ ] Tests code
   - [ ] Builds Docker image
   - [ ] Deploys to Render
   - [ ] Runs health checks

**Option B: Manual via Render**
1. [ ] Go to Render Web Service
2. [ ] Click "Manual Deploy"
3. [ ] Wait for build to complete (5-10 minutes)

### Monitor Deployment

- [ ] Check logs for errors: Render Dashboard > Logs
- [ ] Health check endpoint responding: `/health/`
- [ ] No database connection errors
- [ ] No Redis connection errors
- [ ] Static files served correctly
- [ ] Nginx reverse proxy working

### Post-Deployment Setup

Run in Render shell (Web Service > Shell):

```bash
# Run migrations
python manage.py migrate

# Create superuser for admin
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic --noinput

# Verify database
python manage.py shell
# >>> from django.apps import apps
# >>> print([app.name for app in apps.get_app_configs()])
```

---

## ✅ Phase 6: Security Hardening (Day 2)

### SSL/HTTPS Configuration

- [ ] Render automatically provides SSL certificate
- [ ] Certificate auto-renews (automatic on Render)
- [ ] Force HTTPS in settings (already configured)
- [ ] No mixed content warnings

### Security Headers Verification

```bash
curl -I https://yourdomain.com
# Verify headers:
# - Strict-Transport-Security
# - X-Content-Type-Options: nosniff
# - X-Frame-Options: SAMEORIGIN
# - X-XSS-Protection: 1; mode=block
```

### CORS Configuration

- [ ] Review CORS settings in `settings.py`
- [ ] Configure for your frontend domain
- [ ] Test cross-origin requests

### Admin Panel Security

- [ ] Superuser created with strong password
- [ ] Admin URL changed from `/admin/` (optional, via settings)
- [ ] IP allowlist for admin (optional)
- [ ] Never share admin credentials

### Third-Party Integrations

- [ ] YouTube OAuth callback URL verified
- [ ] Google OAuth callback URL verified
- [ ] GitHub OAuth callback URL verified
- [ ] Pexels API rate limits understood
- [ ] Email sending tested end-to-end

---

## ✅ Phase 7: Integration Testing (Day 3)

### End-to-End Testing

**Manual Testing Checklist:**
- [ ] User registration works
- [ ] Email verification works (if enabled)
- [ ] User login works
- [ ] OAuth login (Google/GitHub) works
- [ ] Dashboard loads with statistics
- [ ] Can view videos list
- [ ] Can view video details
- [ ] API endpoints respond correctly
- [ ] Rate limiting working (test with multiple requests)

**Video Generation Pipeline Test:**
- [ ] Manual task execution test
- [ ] Check ProducerLog for entries
- [ ] Verify database records created
- [ ] Check YouTube integration works
- [ ] Verify analytics fetching works

**API Testing:**
- [ ] GET /api/videos/ returns list
- [ ] GET /api/videos/{id}/ returns detail
- [ ] Health check endpoint responding
- [ ] Rate limit headers present
- [ ] Error responses formatted correctly

### Load Testing (Optional)

```bash
# Install Apache Bench
pip install apache-bench

# Basic load test
ab -n 1000 -c 10 https://yourdomain.com/health/

# More sophisticated testing
pip install locust
# Create locustfile.py for realistic scenarios
```

---

## ✅ Phase 8: Monitoring Setup (Day 4)

### Health Check Monitoring

- [ ] `/health/` endpoint monitored
- [ ] `/status/` endpoint monitored
- [ ] Set up alerts if health check fails
- [ ] Verify monitoring service access

### Logging Configuration

- [ ] Logs being collected in Render
- [ ] Sentry integration (optional):
  - [ ] Create Sentry project
  - [ ] Add `SENTRY_DSN` to environment
  - [ ] Test error reporting
- [ ] Log retention policy set
- [ ] Log rotation configured

### Database Monitoring

- [ ] Enable database monitoring
- [ ] Set up slow query alerts
- [ ] Monitor connection count
- [ ] Track query performance
- [ ] Backup jobs running

### Application Monitoring

- [ ] CPU usage monitored
- [ ] Memory usage monitored
- [ ] Disk usage monitored
- [ ] Network I/O monitored
- [ ] Request throughput monitored

### Alerts Configuration

- [ ] Service health alerts
- [ ] Error rate alerts
- [ ] Performance alerts
- [ ] Disk space alerts
- [ ] Database alerts
- [ ] Slack webhook configured (optional)

---

## ✅ Phase 9: Documentation Update (Day 5)

### Update Documentation

- [ ] Production domain name in README
- [ ] Database credentials secured
- [ ] API key instructions updated
- [ ] Render setup documented
- [ ] Troubleshooting guide updated
- [ ] Team runbook created

### Create Team Documentation

- [ ] How to access production logs
- [ ] How to scale services
- [ ] How to update code
- [ ] How to handle incidents
- [ ] How to backup/restore data
- [ ] Contact information

### Backup Plan

- [ ] Database backup strategy documented
- [ ] Backup testing scheduled
- [ ] Recovery procedure documented
- [ ] RPO target: 1 day
- [ ] RTO target: 1 hour
- [ ] Backup retention: 30 days

---

## ✅ Phase 10: Launch Approval (Day 6)

### Final Checklist

**Technical:**
- [ ] All tests passing
- [ ] No known security issues
- [ ] Performance acceptable
- [ ] Monitoring in place
- [ ] Backups working
- [ ] Disaster recovery tested

**Operational:**
- [ ] Team trained
- [ ] Documentation complete
- [ ] Runbooks prepared
- [ ] Escalation procedures defined
- [ ] On-call schedule ready

**Business:**
- [ ] API keys finalized
- [ ] Domain DNS configured
- [ ] SSL certificate valid
- [ ] Terms of service reviewed
- [ ] Privacy policy updated
- [ ] Legal review complete

### Sign-Off

- [ ] Product Owner: ✓
- [ ] Tech Lead: ✓
- [ ] Security Team: ✓
- [ ] Operations Team: ✓
- [ ] QA Lead: ✓

---

## ✅ Phase 11: Launch & Go-Live (Day 7)

### Pre-Launch

- [ ] Final backup taken
- [ ] Maintenance window scheduled (if needed)
- [ ] Team on standby
- [ ] Monitoring dashboards open
- [ ] Communication channels ready

### Launch

- [ ] Update DNS records to point to Render
- [ ] Monitor health closely (first 24 hours)
- [ ] Monitor error rates (first 24 hours)
- [ ] Monitor performance (first 24 hours)
- [ ] Check user feedback

### Post-Launch

**Immediate (1 hour):**
- [ ] System stable
- [ ] No critical errors
- [ ] Users can access

**Daily (1 week):**
- [ ] Review logs daily
- [ ] Monitor error rates
- [ ] Check performance metrics
- [ ] User feedback collection

**Weekly (1 month):**
- [ ] Review analytics
- [ ] Optimize performance
- [ ] Update documentation
- [ ] Plan improvements

---

## 📋 Rollback Plan

If issues occur during deployment:

```bash
# Option 1: Revert to previous code
git revert <commit-hash>
git push origin main
# GitHub Actions will automatically deploy previous version

# Option 2: Emergency Render rollback
# In Render Dashboard:
# 1. Go to Web Service
# 2. Click "Deployments" 
# 3. Select previous successful deployment
# 4. Click "Redeploy"

# Option 3: Render database restore
# In Render Dashboard:
# 1. Go to PostgreSQL
# 2. Click "Backups"
# 3. Select backup point
# 4. Click "Restore"
```

---

## 🎉 Completion

Once all phases complete and system is stable:

- [ ] Archive this checklist with completion date
- [ ] Create post-launch retrospective
- [ ] Document lessons learned
- [ ] Plan next features
- [ ] Schedule team celebration

---

**Deployment Status**: ✅ **READY FOR PRODUCTION**

**Next Steps**: Follow the checklist phases in order, updating as you progress. Estimated timeline: 1 week.

**Questions?** See [DEPLOYMENT.md](DEPLOYMENT.md) or [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

---

**Good luck with your launch! 🚀**
