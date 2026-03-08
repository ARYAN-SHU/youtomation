"""
Security Utilities and Validators
"""
import logging
import re
from typing import Optional, Tuple
from urllib.parse import urlparse
import bleach

logger = logging.getLogger(__name__)


def get_client_ip(request) -> str:
    """Get client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR', '0.0.0.0')
    return ip


def sanitize_email(email: str) -> str:
    """Sanitize and validate email"""
    email = email.lower().strip()
    # Basic email validation
    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
        raise ValueError('Invalid email format')
    return email


def sanitize_input(user_input: str, max_length: int = 1000) -> str:
    """Sanitize user input to prevent XSS attacks"""
    if not user_input:
        return ''
    
    # Truncate
    user_input = user_input[:max_length]
    
    # Remove potentially dangerous HTML tags
    allowed_tags = {'b', 'i', 'em', 'strong', 'p', 'br', 'a', 'ul', 'ol', 'li'}
    allowed_attributes = {'a': ['href', 'title']}
    
    cleaned = bleach.clean(
        user_input,
        tags=allowed_tags,
        attributes=allowed_attributes,
        strip=True
    )
    
    return cleaned


def validate_url(url: str) -> Tuple[bool, Optional[str]]:
    """Validate URL safety"""
    try:
        result = urlparse(url)
        
        # Check for valid scheme
        if result.scheme not in ('http', 'https'):
            return False, 'Invalid URL scheme'
        
        # Check for localhost/private IPs
        if result.netloc in ('localhost', '127.0.0.1', '0.0.0.0'):
            return False, 'Private URLs not allowed'
        
        return True, None
    except Exception as e:
        return False, str(e)


def validate_password(password: str) -> Tuple[bool, list]:
    """Validate password strength"""
    errors = []
    
    if len(password) < 8:
        errors.append('Password must be at least 8 characters')
    
    if not re.search(r'[A-Z]', password):
        errors.append('Password must contain at least one uppercase letter')
    
    if not re.search(r'[a-z]', password):
        errors.append('Password must contain at least one lowercase letter')
    
    if not re.search(r'[0-9]', password):
        errors.append('Password must contain at least one digit')
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        errors.append('Password must contain at least one special character')
    
    return len(errors) == 0, errors


def hash_sensitive_data(data: str) -> str:
    """Hash sensitive data for logging"""
    import hashlib
    return hashlib.sha256(data.encode()).hexdigest()[:16]


class SecurityHeaders:
    """Security headers for responses"""
    
    @staticmethod
    def get_security_headers() -> dict:
        """Get recommended security headers"""
        return {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
            'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline' cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' cdn.tailwindcss.com; img-src 'self' data:;",
            'Referrer-Policy': 'strict-origin-when-cross-origin',
            'Permissions-Policy': 'geolocation=(), microphone=(), camera=()',
        }


def add_security_headers(response):
    """Middleware to add security headers"""
    headers = SecurityHeaders.get_security_headers()
    for key, value in headers.items():
        response[key] = value
    return response
