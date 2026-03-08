from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import cache_page
from django.core.cache import cache
from django.db import connection
from django.db.utils import OperationalError
import redis
import os
import logging

logger = logging.getLogger(__name__)


@require_http_methods(["GET"])
@cache_page(5)  # Cache for 5 seconds
def health_check(request):
    """
    Comprehensive health check endpoint for monitoring.
    Returns 200 if all services are healthy, 503 if any critical service is down.
    """
    health_status = {
        'status': 'healthy',
        'timestamp': None,
        'services': {}
    }
    
    # Check Database
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        health_status['services']['database'] = {
            'status': 'healthy',
            'latency_ms': round(connection.queries[-1]['time'] * 1000, 2) if connection.queries else 0
        }
    except OperationalError as e:
        logger.error(f"Database health check failed: {e}")
        health_status['services']['database'] = {
            'status': 'unhealthy',
            'error': str(e)
        }
        health_status['status'] = 'degraded'

    # Check Redis Cache
    try:
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        r = redis.from_url(redis_url)
        r.ping()
        health_status['services']['cache'] = {
            'status': 'healthy',
            'ping': 'pong'
        }
    except (redis.ConnectionError, redis.RedisError) as e:
        logger.error(f"Redis health check failed: {e}")
        health_status['services']['cache'] = {
            'status': 'unhealthy',
            'error': str(e)
        }
        health_status['status'] = 'degraded'

    # Check Django Settings
    try:
        from django.conf import settings
        health_status['services']['django'] = {
            'status': 'healthy',
            'debug': settings.DEBUG,
            'environment': getattr(settings, 'ENVIRONMENT', 'unknown')
        }
    except Exception as e:
        logger.error(f"Django health check failed: {e}")
        health_status['services']['django'] = {
            'status': 'unhealthy',
            'error': str(e)
        }
        health_status['status'] = 'degraded'

    # Check Celery if available
    try:
        from celery import current_app as celery_app
        celery_app.connection()
        health_status['services']['celery'] = {
            'status': 'healthy',
            'broker': 'connected'
        }
    except Exception as e:
        logger.warning(f"Celery health check failed: {e}")
        health_status['services']['celery'] = {
            'status': 'disconnected',
            'note': 'Celery may not be running (optional for health check)'
        }

    # Determine HTTP status code
    http_status = 503 if health_status['status'] == 'unhealthy' else 200

    # Add timestamp
    from django.utils import timezone
    health_status['timestamp'] = timezone.now().isoformat()

    return JsonResponse(health_status, status=http_status)


@require_http_methods(["GET"])
def quick_health(request):
    """
    Fast health check endpoint for load balancers (minimal checks).
    """
    try:
        # Quick database check
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return JsonResponse({'status': 'ok'}, status=200)
    except Exception as e:
        logger.error(f"Quick health check failed: {e}")
        return JsonResponse({'status': 'error'}, status=503)


@require_http_methods(["GET"])
def version(request):
    """
    Returns the application version and build information.
    """
    import sys
    from django.conf import settings
    
    version_info = {
        'app': 'Youtomation',
        'version': getattr(settings, 'APP_VERSION', 'unknown'),
        'build': getattr(settings, 'BUILD_NUMBER', 'unknown'),
        'environment': getattr(settings, 'ENVIRONMENT', 'development'),
        'python': f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        'django': __import__('django').get_version(),
    }
    return JsonResponse(version_info)


@require_http_methods(["GET"])
def status(request):
    """
    Detailed status endpoint for monitoring dashboards.
    Includes metrics and current system state.
    """
    from django.core.cache import cache
    from django.conf import settings
    import psutil
    import os
    
    try:
        stats = {
            'status': 'running',
            'system': {
                'cpu_percent': psutil.cpu_percent(interval=1),
                'memory': {
                    'percent': psutil.virtual_memory().percent,
                    'available_gb': round(psutil.virtual_memory().available / (1024**3), 2)
                },
                'disk': {
                    'percent': psutil.disk_usage('/').percent,
                    'free_gb': round(psutil.disk_usage('/').free / (1024**3), 2)
                }
            },
            'services': {
                'database': 'connected' if connection.ensure_connection() is None else 'disconnected',
                'cache': cache.get('health_check_test') is not None if cache.set('health_check_test', 'ok', 1) else 'connected',
                'workers': getattr(settings, 'CELERY_WORKER_COUNT', 'unknown')
            },
            'process': {
                'pid': os.getpid(),
                'memory_mb': round(psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024, 2)
            }
        }
        return JsonResponse(stats)
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        return JsonResponse({
            'status': 'error',
            'error': str(e)
        }, status=500)
