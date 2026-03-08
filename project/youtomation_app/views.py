"""
Django Views for Youtomation Dashboard
"""
import logging
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Q, Count, Sum, Avg
from django.utils import timezone
from datetime import timedelta

from youtomation_app.models import YouTubeVideo, VideoTask, ProducerLog, TrendingTopic

logger = logging.getLogger(__name__)


def dashboard(request):
    """Main dashboard view"""
    # Total videos generated
    total_videos = YouTubeVideo.objects.count()
    
    # Videos by status
    status_counts = YouTubeVideo.objects.values('status').annotate(count=Count('id'))
    status_dict = {item['status']: item['count'] for item in status_counts}
    
    generating_count = status_dict.get('generating_script', 0) + \
                      status_dict.get('generating_audio', 0) + \
                      status_dict.get('generating_video', 0) + \
                      status_dict.get('uploading', 0)
    
    active_count = status_dict.get('published', 0)
    failed_count = status_dict.get('failed', 0)
    
    # Videos generated in last 24 hours
    twenty_four_hours_ago = timezone.now() - timedelta(hours=24)
    videos_last_24h = YouTubeVideo.objects.filter(created_at__gte=twenty_four_hours_ago).count()
    
    # Total views and likes from published videos
    total_views = YouTubeVideo.objects.filter(status='published').aggregate(
        views=Sum('youtube_views')
    )['views'] or 0
    
    total_likes = YouTubeVideo.objects.filter(status='published').aggregate(
        likes=Sum('youtube_likes')
    )['likes'] or 0
    
    # Recent videos
    recent_videos = YouTubeVideo.objects.all().order_by('-created_at')[:10]
    
    context = {
        'total_videos': total_videos,
        'generating_count': generating_count,
        'active_count': active_count,
        'failed_count': failed_count,
        'videos_last_24h': videos_last_24h,
        'total_views': total_views,
        'total_likes': total_likes,
        'recent_videos': recent_videos,
        'status_breakdown': status_dict,
    }
    
    return render(request, 'youtomation_app/dashboard.html', context)


def videos_list(request):
    """Videos list view with pagination and filtering"""
    # Get filter parameters
    status_filter = request.GET.get('status', '')
    search_query = request.GET.get('q', '')
    sort_by = request.GET.get('sort', '-created_at')
    
    # Start with all videos
    videos_qs = YouTubeVideo.objects.all()
    
    # Apply filters
    if status_filter:
        videos_qs = videos_qs.filter(status=status_filter)
    
    if search_query:
        videos_qs = videos_qs.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(youtube_video_id__icontains=search_query)
        )
    
    # Apply sorting
    videos_qs = videos_qs.order_by(sort_by)
    
    # Paginate
    paginator = Paginator(videos_qs, 20)  # 20 videos per page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'videos': page_obj.object_list,
        'status_filter': status_filter,
        'search_query': search_query,
        'sort_by': sort_by,
        'statuses': YouTubeVideo.STATUS_CHOICES,
    }
    
    return render(request, 'youtomation_app/videos_list.html', context)


def video_detail(request, video_id):
    """Video detail view"""
    video = get_object_or_404(YouTubeVideo, id=video_id)
    
    # Get related tasks
    tasks = VideoTask.objects.filter(youtube_video=video).order_by('created_at')
    
    # Get logs
    logs = ProducerLog.objects.filter(youtube_video=video).order_by('-created_at')[:50]
    
    context = {
        'video': video,
        'tasks': tasks,
        'logs': logs,
        'has_video_file': bool(video.video_file),
        'has_youtube_url': bool(video.youtube_video_id),
    }
    
    return render(request, 'youtomation_app/video_detail.html', context)


@require_http_methods(["GET"])
def video_status_api(request, video_id):
    """API endpoint to get video status (AJAX)"""
    try:
        video = YouTubeVideo.objects.get(id=video_id)
        
        data = {
            'id': video.id,
            'title': video.title,
            'status': video.status,
            'progress': video.progress_percentage,
            'duration': video.duration_seconds,
            'youtube_video_id': video.youtube_video_id or '',
            'youtube_url': video.youtube_url or '',
            'youtube_views': video.youtube_views,
            'youtube_likes': video.youtube_likes,
        }
        
        return JsonResponse(data)
    except YouTubeVideo.DoesNotExist:
        return JsonResponse({'error': 'Video not found'}, status=404)


@require_http_methods(["GET"])
def video_logs_api(request, video_id):
    """API endpoint to get video logs (AJAX)"""
    try:
        video = YouTubeVideo.objects.get(id=video_id)
        logs = ProducerLog.objects.filter(youtube_video=video).order_by('-created_at')[:100]
        
        logs_data = []
        for log in logs:
            logs_data.append({
                'timestamp': log.created_at.isoformat(),
                'level': log.level,
                'message': log.message,
                'task': log.task.task_type if log.task else 'system',
            })
        
        return JsonResponse({'logs': logs_data})
    except YouTubeVideo.DoesNotExist:
        return JsonResponse({'error': 'Video not found'}, status=404)


@require_http_methods(["GET"])
def trending_topics_api(request):
    """API endpoint to get trending topics"""
    topics = TrendingTopic.objects.filter(used=False).order_by('-fetched_at')[:20]
    
    topics_data = []
    for topic in topics:
        topics_data.append({
            'id': topic.id,
            'title': topic.title,
            'interest_value': topic.interest_value,
            'fetched_at': topic.fetched_at.isoformat(),
        })
    
    return JsonResponse({'topics': topics_data})


def statistics(request):
    """Statistics and analytics view"""
    # Time period filter
    period = request.GET.get('period', '30')  # days
    
    try:
        days = int(period)
    except ValueError:
        days = 30
    
    start_date = timezone.now() - timedelta(days=days)
    
    # Videos created in period
    videos_in_period = YouTubeVideo.objects.filter(created_at__gte=start_date)
    
    # Status breakdown
    status_breakdown = videos_in_period.values('status').annotate(count=Count('id'))
    
    # Videos by date (for chart)
    videos_by_date = videos_in_period.extra(
        select={'date': 'DATE(created_at)'}
    ).values('date').annotate(count=Count('id')).order_by('date')
    
    # Average video duration
    avg_duration = videos_in_period.filter(
        duration_seconds__isnull=False
    ).aggregate(avg=Avg('duration_seconds'))['avg'] or 0
    
    # Total engagement
    total_views = videos_in_period.aggregate(views=Sum('youtube_views'))['views'] or 0
    total_likes = videos_in_period.aggregate(likes=Sum('youtube_likes'))['likes'] or 0
    
    # Success rate
    success_count = videos_in_period.filter(status='published').count()
    failed_count = videos_in_period.filter(status='failed').count()
    total_count = videos_in_period.count()
    success_rate = (success_count / total_count * 100) if total_count > 0 else 0
    
    context = {
        'period': days,
        'start_date': start_date,
        'end_date': timezone.now(),
        'total_videos': videos_in_period.count(),
        'status_breakdown': status_breakdown,
        'videos_by_date': list(videos_by_date),
        'avg_duration': avg_duration,
        'total_views': total_views,
        'total_likes': total_likes,
        'success_count': success_count,
        'failed_count': failed_count,
        'success_rate': success_rate,
    }
    
    return render(request, 'youtomation_app/statistics.html', context)
