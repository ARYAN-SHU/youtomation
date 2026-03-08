"""
Authentication Views for JWT and OAuth
"""
import logging
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import *
import json

from youtomation_app.utils.auth_backend import JWTAuthBackend, OAuthBackend
from youtomation_app.models_auth import CustomUser, UserSession
from youtomation_app.utils.security import get_client_ip, sanitize_email

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["POST"])
def register(request):
    """Register new user"""
    try:
        data = json.loads(request.body)
        
        email = sanitize_email(data.get('email', ''))
        password = data.get('password', '')
        first_name = data.get('first_name', '')
        last_name = data.get('last_name', '')
        
        # Validation
        if not email or not password:
            return JsonResponse(
                {'error': 'Email and password are required'},
                status=HTTP_400_BAD_REQUEST
            )
        
        if len(password) < 8:
            return JsonResponse(
                {'error': 'Password must be at least 8 characters'},
                status=HTTP_400_BAD_REQUEST
            )
        
        # Check if user exists
        if CustomUser.objects.filter(email=email).exists():
            return JsonResponse(
                {'error': 'User with this email already exists'},
                status=HTTP_400_BAD_REQUEST
            )
        
        # Create user
        user = CustomUser.objects.create_user(
            email=email,
            username=email.split('@')[0],
            password=password,
            first_name=first_name,
            last_name=last_name,
        )
        
        # Generate tokens
        jwt_backend = JWTAuthBackend()
        tokens = jwt_backend.generate_tokens(user)
        
        # Create session
        expiry = timezone.now() + timezone.timedelta(hours=1)
        session = UserSession.objects.create(
            user=user,
            token=tokens['access'],
            refresh_token=tokens['refresh'],
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
            expires_at=expiry,
        )
        
        logger.info(f"User registered: {email}")
        
        return JsonResponse({
            'success': True,
            'user': {
                'id': str(user.id),
                'email': user.email,
                'first_name': user.first_name,
            },
            'tokens': tokens,
        }, status=HTTP_201_CREATED)
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        return JsonResponse({'error': 'Registration failed'}, status=HTTP_500_INTERNAL_SERVER_ERROR)


@csrf_exempt
@require_http_methods(["POST"])
def login(request):
    """Login user with email and password"""
    try:
        data = json.loads(request.body)
        
        email = data.get('email', '').lower().strip()
        password = data.get('password', '')
        
        if not email or not password:
            return JsonResponse(
                {'error': 'Email and password are required'},
                status=HTTP_400_BAD_REQUEST
            )
        
        # Authenticate user
        user = CustomUser.objects.filter(email=email).first()
        
        if not user or not user.check_password(password):
            logger.warning(f"Failed login attempt for: {email}")
            return JsonResponse(
                {'error': 'Invalid email or password'},
                status=HTTP_401_UNAUTHORIZED
            )
        
        # Generate tokens
        jwt_backend = JWTAuthBackend()
        tokens = jwt_backend.generate_tokens(user)
        
        # Create session
        expiry = timezone.now() + timezone.timedelta(hours=1)
        session = UserSession.objects.create(
            user=user,
            token=tokens['access'],
            refresh_token=tokens['refresh'],
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
            expires_at=expiry,
        )
        
        # Update last login
        user.last_login = timezone.now()
        user.last_login_ip = get_client_ip(request)
        user.save()
        
        logger.info(f"User logged in: {email}")
        
        return JsonResponse({
            'success': True,
            'user': {
                'id': str(user.id),
                'email': user.email,
                'first_name': user.first_name,
            },
            'tokens': tokens,
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return JsonResponse({'error': 'Login failed'}, status=HTTP_500_INTERNAL_SERVER_ERROR)


@csrf_exempt
@require_http_methods(["POST"])
def refresh_token(request):
    """Refresh access token using refresh token"""
    try:
        data = json.loads(request.body)
        refresh_token = data.get('refresh_token', '')
        
        if not refresh_token:
            return JsonResponse(
                {'error': 'Refresh token is required'},
                status=HTTP_400_BAD_REQUEST
            )
        
        jwt_backend = JWTAuthBackend()
        new_access_token = jwt_backend.refresh_access_token(refresh_token)
        
        if not new_access_token:
            return JsonResponse(
                {'error': 'Invalid or expired refresh token'},
                status=HTTP_401_UNAUTHORIZED
            )
        
        logger.info("Access token refreshed")
        
        return JsonResponse({
            'success': True,
            'access': new_access_token,
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}")
        return JsonResponse({'error': 'Token refresh failed'}, status=HTTP_500_INTERNAL_SERVER_ERROR)


@csrf_exempt
@require_http_methods(["GET"])
def oauth_callback(request):
    """Handle OAuth callback"""
    try:
        provider = request.GET.get('provider', '')
        code = request.GET.get('code', '')
        state = request.GET.get('state', '')
        
        if not provider or not code:
            return JsonResponse(
                {'error': 'Missing required parameters'},
                status=HTTP_400_BAD_REQUEST
            )
        
        # Get OAuth provider
        from youtomation_app.models_auth import OAuthProvider
        oauth_provider = OAuthProvider.objects.filter(name=provider, is_active=True).first()
        
        if not oauth_provider:
            return JsonResponse({'error': 'Provider not found'}, status=HTTP_404_NOT_FOUND)
        
        oauth_backend = OAuthBackend()
        
        # Exchange code for token
        access_token = oauth_backend.exchange_code_for_token(
            provider,
            code,
            oauth_provider.redirect_uri
        )
        
        if not access_token:
            return JsonResponse(
                {'error': 'Failed to exchange authorization code'},
                status=HTTP_400_BAD_REQUEST
            )
        
        # Get user from OAuth provider
        if provider == 'google':
            user = oauth_backend.authenticate_google(access_token)
        elif provider == 'github':
            user = oauth_backend.authenticate_github(access_token)
        else:
            return JsonResponse({'error': 'Unknown provider'}, status=HTTP_400_BAD_REQUEST)
        
        if not user:
            return JsonResponse(
                {'error': 'Failed to authenticate user'},
                status=HTTP_400_BAD_REQUEST
            )
        
        # Generate JWT tokens
        jwt_backend = JWTAuthBackend()
        tokens = jwt_backend.generate_tokens(user)
        
        # Create session
        expiry = timezone.now() + timezone.timedelta(hours=1)
        UserSession.objects.create(
            user=user,
            token=tokens['access'],
            refresh_token=tokens['refresh'],
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
            expires_at=expiry,
        )
        
        logger.info(f"OAuth login successful for {provider}: {user.email}")
        
        return JsonResponse({
            'success': True,
            'user': {
                'id': str(user.id),
                'email': user.email,
                'first_name': user.first_name,
            },
            'tokens': tokens,
        })
        
    except Exception as e:
        logger.error(f"OAuth callback error: {str(e)}")
        return JsonResponse({'error': 'OAuth callback failed'}, status=HTTP_500_INTERNAL_SERVER_ERROR)


@require_http_methods(["POST"])
@permission_classes([IsAuthenticated])
def logout(request):
    """Logout user"""
    try:
        # Get auth header
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
            
            # Invalidate session
            UserSession.objects.filter(token=token).update(is_active=False)
        
        logger.info(f"User logged out: {request.user.email}")
        
        return JsonResponse({
            'success': True,
            'message': 'Logged out successfully'
        })
        
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        return JsonResponse({'error': 'Logout failed'}, status=HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def current_user(request):
    """Get current user profile"""
    user = request.user
    
    return Response({
        'id': str(user.id),
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'avatar_url': user.avatar_url,
        'bio': user.bio,
        'created_at': user.created_at.isoformat(),
        'email_notifications': user.email_notifications,
        'auto_publish': user.auto_publish,
    })
