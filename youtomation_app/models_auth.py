"""
Authentication Models for OAuth + JWT
"""
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
import uuid


class CustomUser(AbstractUser):
    """Extended user model with additional fields"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # OAuth fields
    google_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    github_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    
    # Profile
    avatar_url = models.URLField(null=True, blank=True)
    bio = models.TextField(null=True, blank=True)
    
    # API key for programmatic access
    api_key = models.CharField(max_length=255, unique=True, null=True, blank=True)
    api_key_created_at = models.DateTimeField(null=True, blank=True)
    
    # User settings
    max_videos_per_day = models.IntegerField(default=2)
    video_quality = models.CharField(
        max_length=20,
        choices=[('720p', '720p'), ('1080p', '1080p'), ('4k', '4K')],
        default='1080p'
    )
    
    # Tracking
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    last_video_generated_at = models.DateTimeField(null=True, blank=True)
    videos_generated_in_period = models.IntegerField(default=0)
    
    # Preferences
    email_notifications = models.BooleanField(default=True)
    auto_publish = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
    
    def __str__(self):
        return self.email
    
    def generate_api_key(self):
        """Generate new API key"""
        import secrets
        self.api_key = secrets.token_urlsafe(32)
        self.api_key_created_at = timezone.now()
        self.save()
        return self.api_key


class OAuthProvider(models.Model):
    """OAuth provider configuration"""
    name = models.CharField(max_length=50)  # 'google', 'github'
    client_id = models.CharField(max_length=255)
    client_secret = models.CharField(max_length=255)
    redirect_uri = models.URLField()
    authorization_url = models.URLField()
    token_url = models.URLField()
    userinfo_url = models.URLField()
    scope = models.CharField(max_length=500)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('name',)
    
    def __str__(self):
        return f"{self.name.title()} OAuth"


class UserSession(models.Model):
    """Track user sessions for JWT tokens"""
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='sessions')
    token = models.TextField()  # JWT token
    refresh_token = models.TextField(null=True, blank=True)
    
    ip_address = models.GenericIPAddressField()
    user_agent = models.CharField(max_length=500)
    
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    last_activity_at = models.DateTimeField(auto_now=True)
    
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['token']),
        ]
    
    def __str__(self):
        return f"Session for {self.user.email}"
    
    @property
    def is_expired(self):
        return timezone.now() > self.expires_at


class APIUsageLog(models.Model):
    """Track API usage for rate limiting"""
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='api_logs')
    endpoint = models.CharField(max_length=255)
    method = models.CharField(max_length=10)
    status_code = models.IntegerField()
    response_time_ms = models.IntegerField()
    
    ip_address = models.GenericIPAddressField()
    user_agent = models.CharField(max_length=500)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return f"{self.method} {self.endpoint} - {self.status_code}"
