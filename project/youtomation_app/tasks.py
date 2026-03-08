"""
Celery Tasks for Youtomation
Orchestrates the complete video generation and upload pipeline
"""
import logging
import os
from datetime import datetime, timedelta
from celery import shared_task, group, chain, chord
from django.utils import timezone
from django.conf import settings

from youtomation_app.models import YouTubeVideo, VideoTask, StockVideo, Subtitle, ProducerLog, TrendingTopic
from youtomation_app.services.trending_topics import TrendingTopicsService
from youtomation_app.services.script_generator import ScriptGeneratorService
from youtomation_app.services.text_to_speech import TextToSpeechService
from youtomation_app.services.stock_videos import StockVideosService
from youtomation_app.services.video_generator import VideoGeneratorService
from youtomation_app.services.youtube_uploader import YouTubeUploaderService
from youtomation_app.utils.exceptions import VideoGenerationException

logger = logging.getLogger(__name__)


# ===== UTILITY FUNCTIONS =====
def create_video_task(youtube_video: YouTubeVideo, task_type: str) -> VideoTask:
    """Create a new video task"""
    task = VideoTask.objects.create(
        youtube_video=youtube_video,
        task_type=task_type,
        status='pending'
    )
    return task


def update_task_status(task: VideoTask, status: str, result_data: dict = None, error_msg: str = None):
    """Update task status"""
    task.status = status
    if result_data:
        task.result_data = result_data
    if error_msg:
        task.error_message = error_msg
    if status == 'running' and not task.started_at:
        task.started_at = timezone.now()
    elif status == 'completed':
        task.completed_at = timezone.now()
        if task.started_at:
            task.duration_seconds = int((task.completed_at - task.started_at).total_seconds())
    task.save()


def log_producer_event(youtube_video: YouTubeVideo, level: str, message: str, task: VideoTask = None, details: dict = None):
    """Log producer event"""
    ProducerLog.objects.create(
        youtube_video=youtube_video,
        task=task,
        level=level,
        message=message,
        details=details or {}
    )


# ===== MAIN CELERY TASKS =====

@shared_task(bind=True, max_retries=3)
def fetch_trending_topics(self):
    """Fetch trending topics from Google Trends"""
    try:
        logger.info("Starting fetch_trending_topics task")
        
        service = TrendingTopicsService(language='en', hl='en-US')
        
        # Fetch trending searches for multiple regions
        regions = ['US', 'GB', 'IN', 'CA', 'AU']
        all_topics = []
        
        for region in regions:
            try:
                trending = service.get_trending_searches(geo=region)
                all_topics.extend(trending[:3])  # Get top 3 per region
                logger.info(f"Fetched {len(trending[:3])} topics for {region}")
            except Exception as e:
                logger.error(f"Error fetching topics for {region}: {str(e)}")
                continue
        
        # Save to database
        saved_count = 0
        for topic_data in all_topics:
            topic, created = TrendingTopic.objects.get_or_create(
                title=topic_data['title'],
                defaults={
                    'interest_value': topic_data.get('rank', 0),
                    'geoCode': topic_data.get('geo', ''),
                }
            )
            if created:
                saved_count += 1
        
        logger.info(f"Saved {saved_count} new trending topics")
        return {'status': 'success', 'topics_saved': saved_count}
        
    except Exception as exc:
        logger.error(f"Error in fetch_trending_topics: {str(exc)}")
        raise self.retry(exc=exc, countdown=300)  # Retry in 5 minutes


@shared_task(bind=True, max_retries=2)
def generate_script(self, youtube_video_id: int, topic: str):
    """Generate video script from topic"""
    try:
        logger.info(f"Generating script for video {youtube_video_id}, topic: {topic}")
        
        youtube_video = YouTubeVideo.objects.get(id=youtube_video_id)
        task_obj = create_video_task(youtube_video, 'generate_script')
        
        try:
            youtube_video.status = 'generating_script'
            youtube_video.save()
            
            update_task_status(task_obj, 'running')
            
            # Generate script
            service = ScriptGeneratorService()
            script = service.generate_script_template(
                topic=topic,
                style='educational',
                word_count=850
            )
            
            # Validate script
            validation = service.validate_script(script)
            if not validation['is_valid']:
                error_msg = '; '.join(validation['issues'])
                raise VideoGenerationException(f"Script validation failed: {error_msg}")
            
            # Save script
            youtube_video.script = script
            youtube_video.save()
            
            update_task_status(
                task_obj,
                'completed',
                result_data={'script_length': len(script.split())}
            )
            
            log_producer_event(
                youtube_video,
                'INFO',
                f"Script generated successfully ({len(script.split())} words)",
                task=task_obj
            )
            
            return {'status': 'success', 'video_id': youtube_video_id, 'script_length': len(script.split())}
            
        except Exception as e:
            logger.error(f"Error generating script: {str(e)}")
            youtube_video.status = 'failed'
            youtube_video.error_message = str(e)
            youtube_video.save()
            
            update_task_status(task_obj, 'failed', error_msg=str(e))
            log_producer_event(youtube_video, 'ERROR', f"Script generation failed: {str(e)}", task=task_obj)
            
            raise
        
    except Exception as exc:
        logger.error(f"Error in generate_script task: {str(exc)}")
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=2)
def text_to_speech(self, youtube_video_id: int):
    """Convert script to audio"""
    try:
        logger.info(f"Converting script to speech for video {youtube_video_id}")
        
        youtube_video = YouTubeVideo.objects.get(id=youtube_video_id)
        task_obj = create_video_task(youtube_video, 'text_to_speech')
        
        try:
            youtube_video.status = 'generating_audio'
            youtube_video.save()
            
            update_task_status(task_obj, 'running')
            
            # Initialize TTS service
            tts_engine = settings.TTS_ENGINE
            tts = TextToSpeechService(engine=tts_engine, language='en')
            
            # Sanitize script
            script = tts.sanitize_text(youtube_video.script)
            
            # Generate audio
            audio_filename = f"video_{youtube_video_id}_audio.mp3"
            audio_path = os.path.join(settings.MEDIA_ROOT, 'audio', audio_filename)
            
            success = tts.generate_audio(script, audio_path)
            if not success:
                raise VideoGenerationException("TTS generation failed")
            
            # Save audio file reference
            youtube_video.audio_file.name = f'audio/{audio_filename}'
            youtube_video.save()
            
            # Get audio duration
            duration = tts.get_audio_duration(audio_path)
            
            update_task_status(
                task_obj,
                'completed',
                result_data={'audio_duration': duration, 'audio_file': audio_path}
            )
            
            log_producer_event(
                youtube_video,
                'INFO',
                f"Audio generated successfully ({duration}s)",
                task=task_obj
            )
            
            return {'status': 'success', 'video_id': youtube_video_id, 'duration': duration}
            
        except Exception as e:
            logger.error(f"Error in text_to_speech: {str(e)}")
            youtube_video.status = 'failed'
            youtube_video.error_message = str(e)
            youtube_video.save()
            
            update_task_status(task_obj, 'failed', error_msg=str(e))
            log_producer_event(youtube_video, 'ERROR', f"TTS generation failed: {str(e)}", task=task_obj)
            
            raise
        
    except Exception as exc:
        logger.error(f"Error in text_to_speech task: {str(exc)}")
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=2)
def fetch_stock_videos(self, youtube_video_id: int, topic: str):
    """Download stock videos for the topic"""
    try:
        logger.info(f"Fetching stock videos for video {youtube_video_id}, topic: {topic}")
        
        youtube_video = YouTubeVideo.objects.get(id=youtube_video_id)
        task_obj = create_video_task(youtube_video, 'fetch_stock_videos')
        
        try:
            update_task_status(task_obj, 'running')
            
            # Initialize Pexels service
            pexels_api_key = settings.PEXELS_API_KEY
            if not pexels_api_key:
                raise VideoGenerationException("Pexels API key not configured")
            
            service = StockVideosService(api_key=pexels_api_key)
            
            # Download videos
            output_dir = os.path.join(settings.MEDIA_ROOT, 'stock_videos', str(youtube_video_id))
            os.makedirs(output_dir, exist_ok=True)
            
            downloaded_videos = service.download_videos_for_topic(
                topic=topic,
                output_dir=output_dir,
                num_videos=3
            )
            
            if not downloaded_videos:
                raise VideoGenerationException(f"No stock videos found for topic: {topic}")
            
            # Save stock video metadata
            for idx, video_path in enumerate(downloaded_videos):
                StockVideo.objects.create(
                    youtube_video=youtube_video,
                    pexels_video_id=f"{topic}_{idx}",
                    title=f"{topic} - Part {idx + 1}",
                    url='',
                    duration_seconds=0,
                    width=1920,
                    height=1080,
                    video_file=f'stock_videos/{youtube_video_id}/{os.path.basename(video_path)}',
                    used_in_final_video=True,
                    order_in_video=idx
                )
            
            update_task_status(
                task_obj,
                'completed',
                result_data={'videos_count': len(downloaded_videos), 'videos': downloaded_videos}
            )
            
            log_producer_event(
                youtube_video,
                'INFO',
                f"Downloaded {len(downloaded_videos)} stock videos",
                task=task_obj
            )
            
            return {'status': 'success', 'video_id': youtube_video_id, 'videos_count': len(downloaded_videos)}
            
        except Exception as e:
            logger.error(f"Error fetching stock videos: {str(e)}")
            
            update_task_status(task_obj, 'failed', error_msg=str(e))
            log_producer_event(youtube_video, 'ERROR', f"Stock videos fetch failed: {str(e)}", task=task_obj)
            
            raise
        
    except Exception as exc:
        logger.error(f"Error in fetch_stock_videos task: {str(exc)}")
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=1)
def generate_video(self, youtube_video_id: int):
    """Generate final video from audio and stock footage"""
    try:
        logger.info(f"Generating video for {youtube_video_id}")
        
        youtube_video = YouTubeVideo.objects.get(id=youtube_video_id)
        task_obj = create_video_task(youtube_video, 'generate_video')
        
        try:
            youtube_video.status = 'generating_video'
            youtube_video.save()
            
            update_task_status(task_obj, 'running')
            
            # Get audio file
            if not youtube_video.audio_file:
                raise VideoGenerationException("Audio file not found")
            
            audio_path = youtube_video.audio_file.path
            
            # Get stock videos
            stock_videos_qs = StockVideo.objects.filter(
                youtube_video=youtube_video,
                used_in_final_video=True
            ).order_by('order_in_video')
            
            stock_video_paths = [sv.video_file.path for sv in stock_videos_qs]
            
            if not stock_video_paths:
                raise VideoGenerationException("No stock videos found")
            
            # Initialize video generator
            output_dir = os.path.join(settings.MEDIA_ROOT, 'videos')
            generator = VideoGeneratorService(output_dir=output_dir)
            
            # Generate video
            output_file = os.path.join(output_dir, f"video_{youtube_video_id}.mp4")
            result = generator.generate_video(
                audio_file=audio_path,
                stock_videos=stock_video_paths,
                output_file=output_file,
                title=youtube_video.title
            )
            
            if not result:
                raise VideoGenerationException("Video generation failed")
            
            # Get video info
            video_info = generator.get_video_info(output_file)
            
            # Save video info
            youtube_video.video_file.name = f'videos/video_{youtube_video_id}.mp4'
            youtube_video.duration_seconds = int(video_info['duration'])
            youtube_video.video_width = video_info['width']
            youtube_video.video_height = video_info['height']
            youtube_video.video_fps = int(video_info['fps'])
            youtube_video.save()
            
            update_task_status(
                task_obj,
                'completed',
                result_data={
                    'video_file': output_file,
                    'duration': video_info['duration'],
                    'file_size': video_info['file_size']
                }
            )
            
            log_producer_event(
                youtube_video,
                'INFO',
                f"Video generated successfully ({video_info['duration']}s)",
                task=task_obj
            )
            
            return {'status': 'success', 'video_id': youtube_video_id, 'duration': video_info['duration']}
            
        except Exception as e:
            logger.error(f"Error generating video: {str(e)}")
            youtube_video.status = 'failed'
            youtube_video.error_message = str(e)
            youtube_video.save()
            
            update_task_status(task_obj, 'failed', error_msg=str(e))
            log_producer_event(youtube_video, 'ERROR', f"Video generation failed: {str(e)}", task=task_obj)
            
            raise
        
    except Exception as exc:
        logger.error(f"Error in generate_video task: {str(exc)}")
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=1)
def upload_to_youtube(self, youtube_video_id: int):
    """Upload video to YouTube"""
    try:
        logger.info(f"Uploading video {youtube_video_id} to YouTube")
        
        youtube_video = YouTubeVideo.objects.get(id=youtube_video_id)
        task_obj = create_video_task(youtube_video, 'upload_youtube')
        
        try:
            youtube_video.status = 'uploading'
            youtube_video.save()
            
            update_task_status(task_obj, 'running')
            
            # Validate video file
            if not youtube_video.video_file:
                raise VideoGenerationException("Video file not found")
            
            video_path = youtube_video.video_file.path
            
            if not os.path.exists(video_path):
                raise VideoGenerationException(f"Video file not found: {video_path}")
            
            # Initialize YouTube uploader
            try:
                uploader = YouTubeUploaderService(
                    client_id=settings.YOUTUBE_CLIENT_ID,
                    client_secret=settings.YOUTUBE_CLIENT_SECRET,
                    access_token=settings.YOUTUBE_ACCESS_TOKEN,
                    refresh_token=settings.YOUTUBE_REFRESH_TOKEN
                )
                
                uploader.authenticate()
                
            except Exception as e:
                raise VideoGenerationException(f"YouTube authentication failed: {str(e)}")
            
            # Upload video
            video_id = uploader.upload_video(
                video_path=video_path,
                title=youtube_video.title,
                description=youtube_video.description,
                tags=youtube_video.tags or [],
                category_id='22',  # People & Blogs
                is_private=False
            )
            
            if not video_id:
                raise VideoGenerationException("Failed to upload video to YouTube")
            
            # Save YouTube metadata
            youtube_video.youtube_video_id = video_id
            youtube_video.youtube_url = f"https://www.youtube.com/watch?v={video_id}"
            youtube_video.youtube_upload_date = timezone.now()
            youtube_video.status = 'published'
            youtube_video.save()
            
            # Wait for processing
            uploader.wait_for_processing(video_id)
            
            update_task_status(
                task_obj,
                'completed',
                result_data={'video_id': video_id, 'url': youtube_video.youtube_url}
            )
            
            log_producer_event(
                youtube_video,
                'INFO',
                f"Video uploaded to YouTube: {video_id}",
                task=task_obj
            )
            
            return {'status': 'success', 'youtube_video_id': video_id, 'youtube_url': youtube_video.youtube_url}
            
        except Exception as e:
            logger.error(f"Error uploading to YouTube: {str(e)}")
            youtube_video.status = 'failed'
            youtube_video.error_message = str(e)
            youtube_video.save()
            
            update_task_status(task_obj, 'failed', error_msg=str(e))
            log_producer_event(youtube_video, 'ERROR', f"YouTube upload failed: {str(e)}", task=task_obj)
            
            raise
        
    except Exception as exc:
        logger.error(f"Error in upload_to_youtube task: {str(exc)}")
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True)
def fetch_youtube_analytics(self):
    """Fetch analytics for published videos (runs every 6 hours)"""
    try:
        logger.info("Starting fetch_youtube_analytics task")
        
        # Get all published videos
        published_videos = YouTubeVideo.objects.filter(
            status='published',
            youtube_video_id__isnull=False
        )
        
        if not published_videos.exists():
            logger.info("No published videos to fetch analytics for")
            return {'status': 'success', 'videos_updated': 0}
        
        try:
            uploader = YouTubeUploaderService(
                client_id=settings.YOUTUBE_CLIENT_ID,
                client_secret=settings.YOUTUBE_CLIENT_SECRET,
                access_token=settings.YOUTUBE_ACCESS_TOKEN,
                refresh_token=settings.YOUTUBE_REFRESH_TOKEN
            )
            
            uploader.authenticate()
            
        except Exception as e:
            logger.error(f"YouTube authentication failed: {str(e)}")
            return {'status': 'error', 'message': 'Authentication failed'}
        
        # Fetch analytics for each video
        updated_count = 0
        for video in published_videos:
            try:
                status = uploader.get_video_status(video.youtube_video_id)
                if status:
                    # Update metadata (in production, you'd use YouTube Analytics API)
                    log_producer_event(
                        video,
                        'INFO',
                        f"Analytics fetched for {video.youtube_video_id}"
                    )
                    updated_count += 1
            except Exception as e:
                logger.error(f"Error fetching analytics for {video.youtube_video_id}: {str(e)}")
                continue
        
        logger.info(f"Analytics updated for {updated_count} videos")
        return {'status': 'success', 'videos_updated': updated_count}
        
    except Exception as exc:
        logger.error(f"Error in fetch_youtube_analytics: {str(exc)}")
        return {'status': 'error', 'message': str(exc)}


@shared_task(bind=True)
def generate_and_upload_youtube_video(self):
    """
    Main orchestration task - generates and uploads YouTube video
    Runs every 12 hours
    """
    try:
        logger.info("Starting generate_and_upload_youtube_video orchestration task")
        
        # Step 1: Fetch trending topics
        trending_result = fetch_trending_topics.apply_async()
        trending_result.get(timeout=300)  # Wait up to 5 minutes
        
        # Step 2: Get an unused trending topic
        topic_obj = TrendingTopic.objects.filter(used=False).first()
        if not topic_obj:
            logger.warning("No unused trending topics available")
            return {'status': 'error', 'message': 'No trending topics available'}
        
        topic = topic_obj.title
        
        # Step 3: Create YouTube video record
        youtube_video = YouTubeVideo.objects.create(
            title=f"Trending: {topic}",
            description=f"Latest trending topic: {topic}. Stay updated with what's trending now!",
            script='',
            trending_topic=topic_obj,
            status='pending',
            tags=[topic, 'trending', 'viral']
        )
        
        logger.info(f"Created YouTube video record: {youtube_video.id} for topic: {topic}")
        
        # Step 4: Execute pipeline
        try:
            # Generate script
            script_result = generate_script.apply_async(
                args=[youtube_video.id, topic],
                countdown=0
            )
            script_result.get(timeout=600)
            
            # Generate audio
            speech_result = text_to_speech.apply_async(
                args=[youtube_video.id],
                countdown=0
            )
            speech_result.get(timeout=1200)
            
            # Fetch stock videos
            stocks_result = fetch_stock_videos.apply_async(
                args=[youtube_video.id, topic],
                countdown=0
            )
            stocks_result.get(timeout=600)
            
            # Generate video
            gen_result = generate_video.apply_async(
                args=[youtube_video.id],
                countdown=0
            )
            gen_result.get(timeout=3600)
            
            # Upload to YouTube
            upload_result = upload_to_youtube.apply_async(
                args=[youtube_video.id],
                countdown=0
            )
            upload_result.get(timeout=3600)
            
            # Mark topic as used
            topic_obj.used = True
            topic_obj.used_at = timezone.now()
            topic_obj.save()
            
            logger.info(f"Video generation and upload completed successfully: {youtube_video.id}")
            
            return {
                'status': 'success',
                'video_id': youtube_video.id,
                'topic': topic,
                'youtube_url': youtube_video.youtube_url
            }
            
        except Exception as e:
            logger.error(f"Error in video pipeline: {str(e)}")
            youtube_video.status = 'failed'
            youtube_video.error_message = str(e)
            youtube_video.save()
            
            log_producer_event(youtube_video, 'ERROR', f"Pipeline failed: {str(e)}")
            
            raise
        
    except Exception as exc:
        logger.error(f"Error in generate_and_upload_youtube_video: {str(exc)}")
        return {'status': 'error', 'message': str(exc)}
