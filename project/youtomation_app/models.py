"""
Django Models for Youtomation
Tracks videos, tasks, and metadata
"""
from django.db import models
from django.utils import timezone
import json


class TrendingTopic(models.Model):
    """Store trending topics fetched from Google Trends"""
    title = models.CharField(max_length=255)
    search_volume = models.IntegerField(default=0)
    interest_value = models.IntegerField(default=0)
    geoCode = models.CharField(max_length=10, default='')
    tz = models.IntegerField(default=0)
    categories = models.JSONField(default=list)
    
    fetched_at = models.DateTimeField(auto_now_add=True)
    used = models.BooleanField(default=False)
    used_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-fetched_at']
        indexes = [
            models.Index(fields=['-fetched_at']),
            models.Index(fields=['used']),
        ]
    
    def __str__(self):
        return self.title


class YouTubeVideo(models.Model):
    """Track YouTube videos created and uploaded"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('generating_script', 'Generating Script'),
        ('generating_audio', 'Generating Audio'),
        ('generating_video', 'Generating Video'),
        ('uploading', 'Uploading to YouTube'),
        ('published', 'Published'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    title = models.CharField(max_length=255)
    description = models.TextField()
    script = models.TextField()
    
    trending_topic = models.ForeignKey(TrendingTopic, on_delete=models.SET_NULL, null=True, blank=True)
    
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='pending')
    progress_percentage = models.IntegerField(default=0, help_text='0-100')
    
    # File paths
    script_file = models.FileField(upload_to='scripts/', null=True, blank=True)
    audio_file = models.FileField(upload_to='audio/', null=True, blank=True)
    video_file = models.FileField(upload_to='videos/', null=True, blank=True)
    
    # Video metadata
    duration_seconds = models.IntegerField(null=True, blank=True)
    video_width = models.IntegerField(default=1920)
    video_height = models.IntegerField(default=1080)
    video_fps = models.IntegerField(default=30)
    
    # YouTube metadata
    youtube_video_id = models.CharField(max_length=255, null=True, blank=True)
    youtube_url = models.URLField(null=True, blank=True)
    youtube_upload_date = models.DateTimeField(null=True, blank=True)
    youtube_views = models.IntegerField(default=0)
    youtube_likes = models.IntegerField(default=0)
    
    # Tags and keywords
    tags = models.JSONField(default=list)
    keywords = models.JSONField(default=list)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    generation_started_at = models.DateTimeField(null=True, blank=True)
    generation_completed_at = models.DateTimeField(null=True, blank=True)
    
    # Error tracking
    error_message = models.TextField(null=True, blank=True)
    error_traceback = models.TextField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['youtube_video_id']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.status}"
    
    @property
    def duration_formatted(self):
        """Return formatted duration MM:SS"""
        if self.duration_seconds:
            minutes = self.duration_seconds // 60
            seconds = self.duration_seconds % 60
            return f"{minutes:02d}:{seconds:02d}"
        return ''
    
    @property
    def is_published(self):
        return self.status == 'published' and self.youtube_video_id


class VideoTask(models.Model):
    """Track individual tasks in the video generation pipeline"""
    TASK_TYPES = [
        ('fetch_trending', 'Fetch Trending Topics'),
        ('generate_script', 'Generate Script'),
        ('text_to_speech', 'Text to Speech'),
        ('fetch_stock_videos', 'Fetch Stock Videos'),
        ('generate_video', 'Generate Video'),
        ('upload_youtube', 'Upload to YouTube'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('retry', 'Retry'),
    ]
    
    youtube_video = models.ForeignKey(YouTubeVideo, on_delete=models.CASCADE, related_name='tasks')
    task_type = models.CharField(max_length=50, choices=TASK_TYPES)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='pending')
    
    # Task execution
    celery_task_id = models.CharField(max_length=255, null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.IntegerField(null=True, blank=True)
    
    # Task result/data
    result_data = models.JSONField(default=dict, help_text='Store task results as JSON')
    
    # Error tracking
    retry_count = models.IntegerField(default=0)
    max_retries = models.IntegerField(default=3)
    error_message = models.TextField(null=True, blank=True)
    
    class Meta:
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['youtube_video', 'status']),
            models.Index(fields=['celery_task_id']),
        ]
    
    def __str__(self):
        return f"{self.youtube_video.title} - {self.task_type}"
    
    @property
    def can_retry(self):
        return self.retry_count < self.max_retries


class StockVideo(models.Model):
    """Store metadata about stock videos from Pexels"""
    youtube_video = models.ForeignKey(YouTubeVideo, on_delete=models.CASCADE, related_name='stock_videos')
    
    pexels_video_id = models.CharField(max_length=255)
    title = models.CharField(max_length=255)
    url = models.URLField()
    duration_seconds = models.IntegerField()
    width = models.IntegerField()
    height = models.IntegerField()
    
    # File storage
    video_file = models.FileField(upload_to='stock_videos/')
    downloaded_at = models.DateTimeField(auto_now_add=True)
    
    # Usage
    used_in_final_video = models.BooleanField(default=False)
    order_in_video = models.IntegerField(null=True, blank=True)
    
    class Meta:
        ordering = ['order_in_video']
    
    def __str__(self):
        return f"{self.title} - {self.pexels_video_id}"


class Subtitle(models.Model):
    """Store subtitle information for videos"""
    youtube_video = models.ForeignKey(YouTubeVideo, on_delete=models.CASCADE, related_name='subtitles')
    
    start_time = models.FloatField(help_text='Start time in seconds')
    end_time = models.FloatField(help_text='End time in seconds')
    text = models.CharField(max_length=500)
    
    # Styling
    font_name = models.CharField(max_length=100, default='Arial')
    font_size = models.IntegerField(default=48)
    text_color = models.CharField(max_length=10, default='FFFFFF')
    
    class Meta:
        ordering = ['start_time']
    
    def __str__(self):
        return f"{self.youtube_video.title} - {self.start_time}s"


class ProducerLog(models.Model):
    """Detailed logs for debugging and monitoring"""
    LOG_LEVELS = [
        ('DEBUG', 'Debug'),
        ('INFO', 'Info'),
        ('WARNING', 'Warning'),
        ('ERROR', 'Error'),
        ('CRITICAL', 'Critical'),
    ]
    
    youtube_video = models.ForeignKey(YouTubeVideo, on_delete=models.CASCADE, related_name='logs')
    task = models.ForeignKey(VideoTask, on_delete=models.SET_NULL, null=True, blank=True, related_name='logs')
    
    level = models.CharField(max_length=20, choices=LOG_LEVELS)
    message = models.TextField()
    details = models.JSONField(default=dict)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['youtube_video', '-created_at']),
            models.Index(fields=['level']),
        ]
    
    def __str__(self):
        return f"{self.level} - {self.youtube_video.title}"
