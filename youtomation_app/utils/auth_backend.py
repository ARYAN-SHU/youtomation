"""
JWT and OAuth Authentication Backend
"""
import logging
import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
import requests

logger = logging.getLogger(__name__)

User = get_user_model()


class JWTAuthBackend:
    """JWT Token authentication backend"""
    
    def __init__(self):
        self.secret_key = settings.SECRET_KEY
        self.algorithm = 'HS256'
        self.access_token_lifetime = getattr(settings, 'JWT_ACCESS_TOKEN_LIFETIME', timedelta(hours=1))
        self.refresh_token_lifetime = getattr(settings, 'JWT_REFRESH_TOKEN_LIFETIME', timedelta(days=7))
    
    def generate_tokens(self, user: User) -> Dict[str, str]:
        """
        Generate access and refresh JWT tokens
        
        Args:
            user: User object
            
        Returns:
            Dictionary with 'access' and 'refresh' tokens
        """
        try:
            now = timezone.now()
            access_expiry = now + self.access_token_lifetime
            refresh_expiry = now + self.refresh_token_lifetime
            
            access_payload = {
                'user_id': str(user.id),
                'email': user.email,
                'type': 'access',
                'iat': int(now.timestamp()),
                'exp': int(access_expiry.timestamp()),
            }
            
            refresh_payload = {
                'user_id': str(user.id),
                'type': 'refresh',
                'iat': int(now.timestamp()),
                'exp': int(refresh_expiry.timestamp()),
            }
            
            access_token = jwt.encode(access_payload, self.secret_key, algorithm=self.algorithm)
            refresh_token = jwt.encode(refresh_payload, self.secret_key, algorithm=self.algorithm)
            
            logger.info(f"Generated JWT tokens for user: {user.email}")
            
            return {
                'access': access_token,
                'refresh': refresh_token,
                'access_expires_in': int(self.access_token_lifetime.total_seconds()),
                'refresh_expires_in': int(self.refresh_token_lifetime.total_seconds()),
            }
            
        except Exception as e:
            logger.error(f"Error generating JWT tokens: {str(e)}")
            raise
    
    def verify_token(self, token: str) -> Optional[Dict]:
        """
        Verify and decode JWT token
        
        Args:
            token: JWT token string
            
        Returns:
            Decoded payload or None if invalid
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("JWT token has expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {str(e)}")
            return None
    
    def refresh_access_token(self, refresh_token: str) -> Optional[str]:
        """
        Generate new access token from refresh token
        
        Args:
            refresh_token: Refresh token string
            
        Returns:
            New access token or None if invalid
        """
        try:
            payload = self.verify_token(refresh_token)
            
            if not payload or payload.get('type') != 'refresh':
                logger.warning("Invalid refresh token")
                return None
            
            user_id = payload.get('user_id')
            user = User.objects.get(id=user_id)
            
            tokens = self.generate_tokens(user)
            return tokens['access']
            
        except Exception as e:
            logger.error(f"Error refreshing access token: {str(e)}")
            return None
    
    def get_user_from_token(self, token: str) -> Optional[User]:
        """
        Get user from JWT token
        
        Args:
            token: JWT token string
            
        Returns:
            User object or None
        """
        try:
            payload = self.verify_token(token)
            if not payload:
                return None
            
            user_id = payload.get('user_id')
            user = User.objects.get(id=user_id)
            return user
            
        except User.DoesNotExist:
            logger.warning(f"User not found for token")
            return None
        except Exception as e:
            logger.error(f"Error getting user from token: {str(e)}")
            return None


class OAuthBackend:
    """OAuth2 authentication backend"""
    
    def __init__(self):
        self.jwt_backend = JWTAuthBackend()
    
    def authenticate_google(self, access_token: str) -> Optional[User]:
        """
        Authenticate and get/create user from Google OAuth
        
        Args:
            access_token: Google access token
            
        Returns:
            User object or None
        """
        try:
            # Get user info from Google
            response = requests.get(
                'https://www.googleapis.com/oauth2/v2/userinfo',
                headers={'Authorization': f'Bearer {access_token}'},
                timeout=10
            )
            response.raise_for_status()
            
            user_info = response.json()
            google_id = user_info.get('id')
            email = user_info.get('email')
            name = user_info.get('name', email.split('@')[0])
            picture = user_info.get('picture')
            
            # Get or create user
            user, created = User.objects.get_or_create(
                google_id=google_id,
                defaults={
                    'email': email,
                    'first_name': name.split()[0] if name else '',
                    'last_name': name.split()[-1] if name and len(name.split()) > 1 else '',
                    'avatar_url': picture,
                    'username': email.split('@')[0],
                }
            )
            
            if not created:
                # Update existing user
                if not user.avatar_url and picture:
                    user.avatar_url = picture
                user.save()
            
            logger.info(f"Google OAuth successful for user: {email}")
            return user
            
        except requests.RequestException as e:
            logger.error(f"Error fetching Google user info: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Google OAuth error: {str(e)}")
            return None
    
    def authenticate_github(self, access_token: str) -> Optional[User]:
        """
        Authenticate and get/create user from GitHub OAuth
        
        Args:
            access_token: GitHub access token
            
        Returns:
            User object or None
        """
        try:
            # Get user info from GitHub
            response = requests.get(
                'https://api.github.com/user',
                headers={
                    'Authorization': f'token {access_token}',
                    'Accept': 'application/vnd.github.v3+json'
                },
                timeout=10
            )
            response.raise_for_status()
            
            user_info = response.json()
            github_id = user_info.get('id')
            email = user_info.get('email') or f"{user_info.get('login')}@github.com"
            name = user_info.get('name', user_info.get('login'))
            picture = user_info.get('avatar_url')
            login = user_info.get('login')
            
            # Get or create user
            user, created = User.objects.get_or_create(
                github_id=github_id,
                defaults={
                    'email': email,
                    'first_name': name.split()[0] if name else '',
                    'last_name': name.split()[-1] if name and len(name.split()) > 1 else '',
                    'avatar_url': picture,
                    'username': login,
                }
            )
            
            if not created:
                # Update existing user
                if not user.avatar_url and picture:
                    user.avatar_url = picture
                user.save()
            
            logger.info(f"GitHub OAuth successful for user: {login}")
            return user
            
        except requests.RequestException as e:
            logger.error(f"Error fetching GitHub user info: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"GitHub OAuth error: {str(e)}")
            return None
    
    def get_authorization_url(self, provider: str, redirect_uri: str) -> Optional[str]:
        """
        Get OAuth authorization URL
        
        Args:
            provider: 'google' or 'github'
            redirect_uri: Redirect URI after authorization
            
        Returns:
            Authorization URL or None
        """
        try:
            from youtomation_app.models_auth import OAuthProvider
            import secrets
            
            oauth_provider = OAuthProvider.objects.get(name=provider, is_active=True)
            
            # Generate state parameter
            state = secrets.token_urlsafe(32)
            
            params = {
                'client_id': oauth_provider.client_id,
                'redirect_uri': redirect_uri,
                'response_type': 'code',
                'scope': oauth_provider.scope,
                'state': state,
            }
            
            # Add provider-specific parameters
            if provider == 'google':
                params['access_type'] = 'offline'
                params['prompt'] = 'consent'
            
            from urllib.parse import urlencode
            auth_url = f"{oauth_provider.authorization_url}?{urlencode(params)}"
            
            return auth_url
            
        except Exception as e:
            logger.error(f"Error getting authorization URL: {str(e)}")
            return None
    
    def exchange_code_for_token(self, provider: str, code: str, redirect_uri: str) -> Optional[str]:
        """
        Exchange authorization code for access token
        
        Args:
            provider: 'google' or 'github'
            code: Authorization code
            redirect_uri: Redirect URI used in authorization
            
        Returns:
            Access token or None
        """
        try:
            from youtomation_app.models_auth import OAuthProvider
            
            oauth_provider = OAuthProvider.objects.get(name=provider, is_active=True)
            
            data = {
                'grant_type': 'authorization_code',
                'code': code,
                'redirect_uri': redirect_uri,
                'client_id': oauth_provider.client_id,
                'client_secret': oauth_provider.client_secret,
            }
            
            if provider == 'github':
                data['Accept'] = 'application/json'
            
            response = requests.post(
                oauth_provider.token_url,
                data=data,
                timeout=10
            )
            response.raise_for_status()
            
            token_data = response.json()
            access_token = token_data.get('access_token')
            
            logger.info(f"Exchanged authorization code for {provider} access token")
            return access_token
            
        except Exception as e:
            logger.error(f"Error exchanging code for token: {str(e)}")
            return None
