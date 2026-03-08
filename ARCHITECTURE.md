# Youtomation - System Architecture Document

## 1. Overview

Youtomation is a distributed system designed to automatically generate, compose, and upload YouTube videos at scale. The system uses Django as the web application framework, Celery for asynchronous task processing, and multiple external APIs to create a complete video production pipeline.

### Design Principles

1. **Scalability**: Microservices-like architecture with separate workers
2. **Resilience**: Retry logic, error handling, and monitoring
3. **Security**: JWT authentication, OAuth2, rate limiting, input validation
4. **Maintainability**: Clear separation of concerns, comprehensive logging
5. **Performance**: Async processing, caching, optimized database queries

## 2. System Components

### 2.1 Web Application (Django)

**Purpose**: Handle HTTP requests, serve UI, manage authentication, expose APIs

**Key Responsibilities**:
- User authentication and authorization
- HTTP request routing
- Session management
- Serve HTML templates and static files
- Provide RESTful APIs
- Rate limiting and security headers

**Key Files**:
- `settings.py`: Configuration (database, cache, logging, security)
- `urls.py`: URL routing
- `views.py`: Dashboard and video management views
- `views_auth.py`: Authentication endpoints
- `models.py`: Data models

**Technology Stack**:
- Django 4.2 (Web framework)
- Django REST Framework (API)
- Gunicorn (WSGI server)

### 2.2 Task Queue (Celery)

**Purpose**: Process long-running tasks asynchronously

**Key Responsibilities**:
- Execute video generation pipeline
- Fetch analytics from YouTube
- Retry failed tasks
- Track task status
- Schedule periodic tasks

**Architecture**:
```
Task Producer (Django)
        ↓
   Redis Broker
        ↓
    Workers (Celery)
        ↓
    Results Backend (Redis)
```

**Celery Components**:
- **Broker**: Redis (message queue)
- **Result Backend**: Redis (task results)
- **Worker**: Processes tasks from queue
- **Beat**: Scheduler for periodic tasks
- **Flower**: Monitoring UI (optional)

**Task Pipeline**:
```
generate_and_upload_youtube_video (orchestrator)
├── fetch_trending_topics()
├── generate_script()
├── text_to_speech()
├── fetch_stock_videos()
├── generate_video()
└── upload_to_youtube()
    └── fetch_youtube_analytics() [every 6 hours]
```

### 2.3 Database (PostgreSQL)

**Purpose**: Persistent data storage

**Data Models**:

```sql
-- Core Video Management
YouTubeVideo
├── id (UUID)
├── title
├── description
├── script
├── status (pending→generating→uploading→published/failed)
├── youtube_video_id
└── metadata

VideoTask
├── id (UUID)
├── video_id (FK)
├── task_stage (fetch_trending, generate_script, etc.)
├── celery_task_id
└── status

TrendingTopic
├── id
├── search_query
├── region
├── rank
└── interest_metrics

StockVideo
├── id
├── video_id (FK)
├── pexels_id
├── url
└── metadata

Subtitle
├── id
├── video_id (FK)
├── text
├── start_time
└── end_time

ProducerLog
├── id
├── video_id (FK)
├── level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
├── message
└── timestamp

-- Authentication
CustomUser
├── id (UUID)
├── email
├── username
├── password_hash
├── is_active
└── oauth_providers

OAuthProvider
├── id
├── user_id (FK)
├── provider (google, github)
└── provider_user_id

UserSession
├── id
├── user_id (FK)
├── jwt_token_id
├── ip_address
├── user_agent
└── expires_at

APIUsageLog
├── id
├── user_id (FK)
├── endpoint
├── timestamp
└── response_time
```

**Indexes**:
- `YouTubeVideo.status` (frequently filtered)
- `VideoTask.celery_task_id` (task lookup)
- `TrendingTopic.region, rank` (trending queries)
- `ProducerLog.video_id, level` (logging queries)

## 3. Data Flow

### 3.1 Video Generation Flow

```
1. TRIGGER (every 12 hours via Beat)
   ↓
2. fetch_trending_topics()
   - Query Google Trends API
   - Save TrendingTopic records
   - Select random trending topic
   ↓
3. generate_script()
   - Load script template
   - Insert topic into template
   - Validate word count (650-1100)
   - Save to YouTubeVideo.script
   ↓
4. text_to_speech()
   - Parse script for audio segments
   - Call Google TTS or Coqui TTS
   - Generate MP3 audio file
   - Calculate total duration
   ↓
5. fetch_stock_videos()
   - Search Pexels API for topic keywords
   - Download 3+ stock videos
   - Store as StockVideo records
   ↓
6. generate_video()
   - Load stock videos, audio, subtitle data
   - Use MoviePy to compose video
   - Auto-loop videos to match audio duration
   - Overlay subtitles
   - Render to 1920x1080@30fps
   - Output MP4 file
   ↓
7. upload_to_youtube()
   - Authenticate with YouTube API (OAuth)
   - Upload video file (resumable upload)
   - Monitor upload progress
   - Wait for YouTube processing
   - Extract youtube_video_id
   - Set video metadata (title, description, tags)
   - Publish video
   ↓
8. fetch_youtube_analytics() [every 6 hours]
   - Query YouTube Analytics API
   - Fetch views, likes, comments, watch time
   - Store in database
   - Update ProducerLog
   ↓
9. COMPLETE
```

### 3.2 Authentication Flow

```
NEW USER:
email + password
    ↓
validate input
    ↓
hash password
    ↓
create CustomUser
    ↓
return JWT tokens (access + refresh)

EXISTING USER:
email + password
    ↓
lookup user
    ↓
verify password
    ↓
create UserSession
    ↓
return JWT tokens

OAUTH (Google/GitHub):
user clicks "Login with Google"
    ↓
redirect to Google login
    ↓
user authorizes app
    ↓
Google redirects with authorization code
    ↓
exchange code for tokens
    ↓
fetch user info from Google
    ↓
create or update CustomUser + OAuthProvider
    ↓
create JWT tokens
    ↓
redirect to dashboard

REFRESH TOKEN:
refresh_token (expired access token)
    ↓
verify refresh_token
    ↓
check UserSession is valid
    ↓
issue new access_token
    ↓
return new access_token
```

### 3.3 Rate Limiting Flow

```
HTTP REQUEST
    ↓
RateLimitMiddleware
    ↓
extract client_identifier (user_id or IP)
    ↓
check Redis counter
    ↓
if counter > limit
    ↓
    return 429 Too Many Requests
    ↓
if counter <= limit
    ↓
    increment counter in Redis
    ↓
    set TTL to 1 hour
    ↓
    add X-RateLimit-* headers
    ↓
    pass request to view
```

## 4. API Design

### 4.1 RESTful Endpoints

```
Authentication:
POST   /auth/register                    - Create new user
POST   /auth/login                       - User login
POST   /auth/refresh-token               - Refresh JWT token
GET    /auth/callback/google/            - Google OAuth callback
GET    /auth/callback/github/            - GitHub OAuth callback
POST   /auth/logout                      - User logout
GET    /auth/current-user/               - Get current user profile

Videos:
GET    /api/videos/                      - List videos (paginated, filtered)
GET    /api/videos/{id}/                 - Get video details
GET    /api/videos/{id}/logs/            - Get video logs
GET    /api/videos/{id}/status/          - Get video pipeline status
DELETE /api/videos/{id}/                 - Delete video

Dashboard:
GET    /dashboard/                       - Dashboard overview
GET    /api/trending-topics/             - Get trending topics
GET    /api/stats/                       - Get statistics

Health:
GET    /health/                          - Full health check
GET    /health/quick/                    - Fast health check
GET    /version/                         - App version
GET    /status/                          - System status
```

### 4.2 Response Format

**Success Response (200 OK):**
```json
{
    "data": {...},
    "meta": {
        "pagination": {
            "page": 1,
            "per_page": 20,
            "total": 100
        }
    }
}
```

**Error Response (4xx/5xx):**
```json
{
    "error": "error_code",
    "message": "Human readable message",
    "details": [...]
}
```

## 5. Security Architecture

### 5.1 Authentication Layers

1. **JWT Tokens**
   - Algorithm: HS256
   - Access Token: 1 hour expiry
   - Refresh Token: 7 days expiry
   - Header: `Authorization: Bearer <token>`

2. **OAuth2 Providers**
   - Google OAuth
   - GitHub OAuth
   - Each provider linked to CustomUser

3. **Session Tracking**
   - IP address logging
   - User-agent logging
   - Token revocation on logout

### 5.2 Authorization & Permissions

```python
# User-scoped access
user can only access their own videos

# Permission levels
- Anonymous: View public endpoints, rate limited (100/hr)
- Authenticated: Full access to own data, rate limited (1000/hr)
- Premium: Higher rate limits (10000/hr)
- Admin: Full system access

# Role-based checks in views
@permission_required('can_view_video')
def video_detail(request, video_id):
    video = get_object_or_404(YouTubeVideo, id=video_id, user=request.user)
```

### 5.3 Data Protection

1. **Input Validation**
   - Email validation with regex
   - URL validation (no private IPs)
   - Password strength requirements

2. **XSS Prevention**
   - bleach library for HTML sanitization
   - CSRF tokens in forms
   - Content Security Policy headers

3. **SQL Injection Prevention**
   - Django ORM parameterized queries
   - No raw SQL queries

4. **Rate Limiting**
   - Per-user and per-IP tracking
   - Adaptive limits by user tier
   - Cache-based counters with TTL

5. **Transport Security**
   - HTTPS/TLS enforcement
   - HSTS headers (31536000 seconds)
   - Secure cookies
   - SSL certificate auto-renewal

## 6. Performance Optimization

### 6.1 Database Optimization

```python
# Query optimization
users = User.objects.select_related('profile').prefetch_related('videos')

# Bulk operations
User.objects.bulk_create([...])  # Faster than loop create

# Indexing strategy
- Index on frequently filtered fields (status, user_id)
- Index on join fields (foreign keys)
- Composite indexes for common queries
```

### 6.2 Caching Strategy

```python
# Redis cache for:
- User sessions
- Rate limit counters
- User profiles
- Dashboard statistics (5min TTL)
- API responses (varies by endpoint)

# Cache invalidation
- TTL-based (automatic expiry)
- Event-based (on model change)
- Manual invalidation in views
```

### 6.3 Async Processing

```python
# Celery for long-running tasks:
- Video generation (10-30 minutes)
- YouTube uploads (5-10 minutes)
- Analytics fetching (2-5 minutes)

# Benefits:
- Non-blocking HTTP responses
- Parallel task execution
- Task retry and error handling
- Scalable worker pool
```

### 6.4 Static File Serving

```
Django → Nginx (reverse proxy)
          ├── /static/ → served from disk (gzipped)
          ├── /media/ → served from disk (videos, logs)
          └── /api/* → proxied to Django
```

## 7. Error Handling Architecture

### 7.1 Exception Hierarchy

```
APIException (base)
├── ValidationError (400)
├── AuthenticationError (401)
├── AuthorizationError (403)
├── RateLimitError (429)
├── ResourceNotFound (404)
├── ConflictError (409)
└── ServerError (500)
```

### 7.2 Error Handling Flow

```
HTTP Request
    ↓
View/Service
    ↓
Exception raised
    ↓
ExceptionMiddleware catches
    ↓
Determine error type
    ↓
Log with context
    ↓
Format JSON response
    ↓
Add security headers
    ↓
Return HTTP response
```

### 7.3 Celery Task Error Handling

```python
@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60
)
def my_task(self, data):
    try:
        # Process task
        pass
    except TemporaryError as exc:
        # Retry on temporary errors
        raise self.retry(exc=exc, countdown=60)
    except Exception as exc:
        # Log permanent errors
        log_error(exc)
        raise
```

## 8. Deployment Architecture

### 8.1 Production Stack

```
        User
          ↓
      Internet
          ↓
   SSL/TLS Cert
          ↓
      Nginx Proxy
   (80 → 443, rate limit)
          ↓
    Gunicorn Workers (×4)
    (1000ms timeout)
          ↓
    Django Application
          ↓
    PostgreSQL Database
    (with backups)
          ↓
    Redis Cache & Broker
    (with persistence)
          ↓
    Celery Workers (×N)
          ↓
    Celery Beat Scheduler
          ↓
    External APIs
    (YouTube, Google, Pexels)
```

### 8.2 Container Architecture

```
Docker Image (multi-stage):
├── Build stage
│   └── Install dependencies
├── Runtime stage
│   ├── Python 3.11-slim
│   ├── Non-root user (django)
│   ├── Health check endpoint
│   └── Gunicorn WSGI server
```

### 8.3 Orchestration (Render)

```
Render Services:
├── Web Service (youtomation-api)
│   └── Django + Gunicorn
├── Background Worker (worker)
│   └── Celery worker
├── Background Scheduler (beat)
│   └── Celery Beat
├── PostgreSQL Database
│   └── 15-alpine
├── Redis Cache
│   └── 7-alpine
└── Load Balancers (managed by Render)
```

## 9. Monitoring & Observability

### 9.1 Logging

```
Application Logs:
- Level: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Format: JSON for structured logging
- Destination: Sentry (errors), stdout (all)
- ProducerLog table stores video generation logs
```

### 9.2 Metrics

```
Health Check Endpoints:
- /health/ - Comprehensive (database, cache, services)
- /health/quick/ - Fast check (database only)
- /version/ - Version and build info
- /status/ - System resources (CPU, memory, disk)
```

### 9.3 Debugging

```
Celery Monitoring:
- celery -A youtomation_core inspect active
- celery -A youtomation_core inspect scheduled
- celery -A youtomation_core events

Database Inspection:
- Django shell: python manage.py shell
- psql: command line database client
- Query logs: LOGGING settings
```

## 10. Scaling Strategy

### 10.1 Horizontal Scaling

```
Scale by adding more:
1. Celery Workers (for video generation)
2. Web Servers (for API requests)
3. Database Read Replicas (for analytics)
4. Cache Clusters (Redis cluster mode)
```

### 10.2 Vertical Scaling

```
Upgrade individual services:
1. Larger EC2 instance for web
2. More memory for Celery workers
3. Larger database (RDS upgrade)
4. CDN for static files
```

### 10.3 Rate Limiting Strategy

```
Current Limits:
- Anonymous: 100 requests/hour
- Authenticated: 1000 requests/hour
- Premium: 10000 requests/hour

Adjustable per endpoint:
- /api/ - 1000 req/hr
- /auth/login - 10 req/hr (strict)
- /admin/ - unlimited (authenticated only)
```

## 11. Future Enhancements

- [ ] GraphQL API
- [ ] Real-time updates (WebSockets)
- [ ] Advanced metrics dashboard
- [ ] Machine learning for trending prediction
- [ ] Multi-language support
- [ ] Custom video templates
- [ ] Mobile app
- [ ] Webhook integrations
- [ ] Batch processing
- [ ] Video editing UI

---

**Document Version**: 1.0
**Last Updated**: 2024
**Maintainer**: Development Team
