"""
Rate Limiting Middleware and Utilities
"""
import logging
from typing import Tuple, Optional
from datetime import datetime, timedelta
from functools import wraps

from django.core.cache import cache
from django.http import JsonResponse
from django.utils import timezone
from django.conf import settings
from rest_framework.throttling import BaseThrottle
from rest_framework.response import Response
from rest_framework.status import HTTP_429_TOO_MANY_REQUESTS

logger = logging.getLogger(__name__)


class AdaptiveRateLimiter:
    """Adaptive rate limiter based on user tier and API usage"""
    
    # Default rate limits (requests per time period)
    DEFAULT_LIMITS = {
        'anonymous': 100,      # 100 requests per hour
        'authenticated': 1000,  # 1000 requests per hour
        'premium': 10000,      # 10000 requests per hour
    }
    
    # Time periods (seconds)
    PERIODS = {
        'minute': 60,
        'hour': 3600,
        'day': 86400,
    }
    
    def __init__(self):
        self.cache = cache
    
    def get_client_identifier(self, request) -> str:
        """Get unique identifier for rate limiting"""
        if request.user and request.user.is_authenticated:
            return f"user_{request.user.id}"
        else:
            # Use IP address for anonymous users
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip = x_forwarded_for.split(',')[0]
            else:
                ip = request.META.get('REMOTE_ADDR')
            return f"ip_{ip}"
    
    def get_user_rate_limit(self, user) -> int:
        """Get rate limit for user based on tier"""
        if not user or not user.is_authenticated:
            return self.DEFAULT_LIMITS['anonymous']
        
        # Could be based on subscription tier, API key, etc.
        return self.DEFAULT_LIMITS['authenticated']
    
    def is_rate_limited(
        self,
        request,
        period: str = 'hour'
    ) -> Tuple[bool, Optional[dict]]:
        """
        Check if request is rate limited
        
        Args:
            request: Django request object
            period: 'minute', 'hour', or 'day'
            
        Returns:
            Tuple of (is_limited, limit_info)
        """
        try:
            client_id = self.get_client_identifier(request)
            limit = self.get_user_rate_limit(request.user)
            period_seconds = self.PERIODS.get(period, 3600)
            
            cache_key = f"rate_limit:{client_id}:{period}"
            current_count = self.cache.get(cache_key, 0)
            
            if current_count >= limit:
                logger.warning(f"Rate limit exceeded for {client_id}")
                
                return True, {
                    'limit': limit,
                    'current': current_count,
                    'period': period,
                    'reset_after': period_seconds,
                }
            
            # Increment counter
            self.cache.set(cache_key, current_count + 1, period_seconds)
            
            return False, {
                'limit': limit,
                'current': current_count + 1,
                'remaining': limit - current_count - 1,
                'period': period,
            }
            
        except Exception as e:
            logger.error(f"Error in rate limiter: {str(e)}")
            return False, None
    
    def reset_limit(self, request, period: str = 'hour'):
        """Reset rate limit for a user/IP"""
        client_id = self.get_client_identifier(request)
        cache_key = f"rate_limit:{client_id}:{period}"
        self.cache.delete(cache_key)
        logger.info(f"Reset rate limit for {client_id}")


class RateLimitMiddleware:
    """Middleware to enforce rate limiting"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.limiter = AdaptiveRateLimiter()
        
        # Paths to exclude from rate limiting
        self.exclude_paths = [
            '/admin/',
            '/static/',
            '/media/',
            '/health/',
        ]
    
    def __call__(self, request):
        # Check if path should be rate limited
        if not self._should_rate_limit(request.path):
            return self.get_response(request)
        
        # Check rate limit
        is_limited, limit_info = self.limiter.is_rate_limited(request, 'hour')
        
        if is_limited:
            response = JsonResponse(
                {
                    'error': 'Rate limit exceeded',
                    'limit': limit_info['limit'],
                    'reset_after': limit_info['reset_after'],
                },
                status=429
            )
            response['Retry-After'] = limit_info['reset_after']
            return response
        
        response = self.get_response(request)
        
        # Add rate limit headers
        if limit_info:
            response['X-RateLimit-Limit'] = str(limit_info['limit'])
            response['X-RateLimit-Remaining'] = str(limit_info.get('remaining', 0))
            response['X-RateLimit-Period'] = limit_info['period']
        
        return response
    
    def _should_rate_limit(self, path: str) -> bool:
        """Check if path should be rate limited"""
        for exclude_path in self.exclude_paths:
            if path.startswith(exclude_path):
                return False
        return True


class BurstRateLimiter(BaseThrottle):
    """DRF throttle class for burst rate limiting"""
    
    def __init__(self):
        self.limiter = AdaptiveRateLimiter()
    
    def throttle_success(self, request, view):
        """Return `True` if the request should be throttled."""
        is_limited, _ = self.limiter.is_rate_limited(request, 'minute')
        return not is_limited
    
    def throttle_failure(self, request, view):
        """Handles throttled requests."""
        return False
    
    def get_throttle_key(self, request):
        """Return unique throttle key for request."""
        return self.limiter.get_client_identifier(request)


def rate_limit(period: str = 'hour', limit: Optional[int] = None):
    """
    Decorator for rate limiting view functions
    
    Args:
        period: 'minute', 'hour', or 'day'
        limit: Custom limit (overrides default)
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            limiter = AdaptiveRateLimiter()
            is_limited, limit_info = limiter.is_rate_limited(request, period)
            
            if is_limited:
                return JsonResponse(
                    {
                        'error': 'Rate limit exceeded',
                        'reset_after': limit_info['reset_after'],
                    },
                    status=429
                )
            
            response = view_func(request, *args, **kwargs)
            
            # Add headers
            if isinstance(response, JsonResponse) or hasattr(response, '__setitem__'):
                response['X-RateLimit-Limit'] = str(limit_info['limit'])
                response['X-RateLimit-Remaining'] = str(limit_info.get('remaining', 0))
            
            return response
        
        return wrapper
    return decorator
