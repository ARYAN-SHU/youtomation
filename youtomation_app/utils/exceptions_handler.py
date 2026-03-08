"""
Error Handling and Exception Middleware
"""
import logging
import traceback
import json
from typing import Optional

from django.http import JsonResponse
from django.core.exceptions import PermissionDenied, SuspiciousOperation
from django.http import Http404
from rest_framework import status as http_status

logger = logging.getLogger(__name__)


class APIException(Exception):
    """Base API exception"""
    
    def __init__(
        self,
        message: str,
        status_code: int = 400,
        error_code: str = 'API_ERROR',
        details: dict = None
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(APIException):
    """Validation error"""
    
    def __init__(self, message: str, details: dict = None):
        super().__init__(
            message=message,
            status_code=400,
            error_code='VALIDATION_ERROR',
            details=details
        )


class AuthenticationError(APIException):
    """Authentication error"""
    
    def __init__(self, message: str = 'Authentication failed'):
        super().__init__(
            message=message,
            status_code=401,
            error_code='AUTHENTICATION_ERROR'
        )


class AuthorizationError(APIException):
    """Authorization error"""
    
    def __init__(self, message: str = 'Permission denied'):
        super().__init__(
            message=message,
            status_code=403,
            error_code='AUTHORIZATION_ERROR'
        )


class RateLimitError(APIException):
    """Rate limit exceeded"""
    
    def __init__(self, reset_after: int = 3600):
        super().__init__(
            message='Rate limit exceeded',
            status_code=429,
            error_code='RATE_LIMIT_EXCEEDED',
            details={'reset_after': reset_after}
        )


class ResourceNotFound(APIException):
    """Resource not found"""
    
    def __init__(self, resource: str = 'Resource'):
        super().__init__(
            message=f'{resource} not found',
            status_code=404,
            error_code='NOT_FOUND'
        )


class ConflictError(APIException):
    """Resource conflict"""
    
    def __init__(self, message: str):
        super().__init__(
            message=message,
            status_code=409,
            error_code='CONFLICT'
        )


class ExceptionMiddleware:
    """Middleware for handling exceptions"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        try:
            response = self.get_response(request)
            return response
        except Exception as exc:
            return self.handle_exception(request, exc)
    
    def handle_exception(self, request, exc: Exception):
        """Handle exception and return appropriate response"""
        
        # Handle custom API exceptions
        if isinstance(exc, APIException):
            return self._json_response(exc)
        
        # Handle Django exceptions
        if isinstance(exc, Http404):
            api_exc = ResourceNotFound('Resource')
            return self._json_response(api_exc)
        
        if isinstance(exc, PermissionDenied):
            api_exc = AuthorizationError('You do not have permission to perform this action')
            return self._json_response(api_exc)
        
        if isinstance(exc, SuspiciousOperation):
            logger.warning(f"Suspicious operation: {str(exc)}")
            api_exc = APIException(
                message='Invalid request',
                status_code=400,
                error_code='INVALID_REQUEST'
            )
            return self._json_response(api_exc)
        
        # Log unexpected exceptions
        logger.error(
            f"Unhandled exception: {type(exc).__name__}: {str(exc)}",
            exc_info=True,
            extra={
                'request_path': request.path,
                'request_method': request.method,
                'user': request.user,
            }
        )
        
        # Return generic error in production
        from django.conf import settings
        if settings.DEBUG:
            traceback_str = traceback.format_exc()
        else:
            traceback_str = None
        
        api_exc = APIException(
            message='An unexpected error occurred',
            status_code=500,
            error_code='INTERNAL_SERVER_ERROR'
        )
        
        response = self._json_response(api_exc)
        if traceback_str and settings.DEBUG:
            response['X-Traceback'] = traceback_str
        
        return response
    
    def _json_response(self, exc: APIException):
        """Create JSON error response"""
        data = {
            'error': {
                'message': exc.message,
                'code': exc.error_code,
            }
        }
        
        if exc.details:
            data['error']['details'] = exc.details
        
        response = JsonResponse(data, status=exc.status_code)
        
        # Add security headers
        from youtomation_app.utils.security import SecurityHeaders
        headers = SecurityHeaders.get_security_headers()
        for key, value in headers.items():
            response[key] = value
        
        return response


def handle_errors(func):
    """Decorator for handling errors in views"""
    from functools import wraps
    
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        try:
            return func(request, *args, **kwargs)
        except APIException as e:
            middleware = ExceptionMiddleware(lambda r: None)
            return middleware._json_response(e)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {str(e)}", exc_info=True)
            api_exc = APIException(
                message='An error occurred',
                status_code=500,
                error_code='INTERNAL_ERROR'
            )
            middleware = ExceptionMiddleware(lambda r: None)
            return middleware._json_response(api_exc)
    
    return wrapper
