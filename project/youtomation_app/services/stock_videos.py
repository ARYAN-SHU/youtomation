"""
Stock Videos Service
Fetches stock videos from Pexels API
"""
import logging
import os
import requests
from typing import List, Dict, Optional
from pathlib import Path
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

PEXELS_BASE_URL = 'https://api.pexels.com/videos/search'


class StockVideosService:
    """Service for fetching stock videos from Pexels"""
    
    def __init__(self, api_key: str):
        """
        Initialize Pexels API client
        
        Args:
            api_key: Pexels API key
        """
        self.api_key = api_key
        self.base_url = PEXELS_BASE_URL
        self.headers = {
            'Authorization': api_key,
        }
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def search_videos(
        self,
        query: str,
        page: int = 1,
        per_page: int = 15,
        min_duration: int = None,
        max_duration: int = None,
        orientation: str = None
    ) -> Optional[Dict]:
        """
        Search for videos on Pexels
        
        Args:
            query: Search query
            page: Page number
            per_page: Results per page (max 80)
            min_duration: Minimum video duration in seconds
            max_duration: Maximum video duration in seconds
            orientation: Video orientation ('portrait', 'landscape', 'square')
            
        Returns:
            Search results including videos list
        """
        try:
            params = {
                'query': query,
                'page': page,
                'per_page': per_page,
            }
            
            if min_duration:
                params['min_duration'] = min_duration
            if max_duration:
                params['max_duration'] = max_duration
            if orientation:
                params['orientation'] = orientation
            
            logger.info(f"Searching Pexels for: {query}")
            response = requests.get(self.base_url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"Found {len(data.get('videos', []))} videos for query: {query}")
            
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Pexels API request error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error searching videos: {str(e)}")
            raise
    
    def download_video(
        self,
        video_url: str,
        output_path: str,
        quality: str = 'hd'
    ) -> bool:
        """
        Download video from Pexels
        
        Args:
            video_url: Direct video URL
            output_path: Path to save video
            quality: Video quality ('hd', 'sd')
            
        Returns:
            True if download successful, False otherwise
        """
        try:
            logger.info(f"Downloading video from: {video_url}")
            
            # Create output directory
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Download video
            response = requests.get(video_url, timeout=30, stream=True)
            response.raise_for_status()
            
            # Calculate total file size
            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0
            chunk_size = 1024 * 1024  # 1MB chunks
            
            # Write video to file
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        progress = (downloaded_size / total_size * 100) if total_size > 0 else 0
                        if downloaded_size % (chunk_size * 10) == 0:  # Log every 10MB
                            logger.debug(f"Download progress: {progress:.1f}%")
            
            file_size = os.path.getsize(output_path)
            logger.info(f"Video downloaded successfully: {output_path} ({file_size / (1024**2):.2f} MB)")
            
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error downloading video: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during video download: {str(e)}")
            return False
    
    def get_videos_for_topic(
        self,
        topic: str,
        num_videos: int = 3,
        min_duration: int = 10,
        max_duration: int = 60
    ) -> List[Dict]:
        """
        Get stock videos for a topic
        
        Args:
            topic: Topic/keyword to search for
            num_videos: Number of videos to fetch
            min_duration: Minimum video duration
            max_duration: Maximum video duration
            
        Returns:
            List of video metadata dictionaries
        """
        try:
            results = self.search_videos(
                query=topic,
                per_page=num_videos,
                min_duration=min_duration,
                max_duration=max_duration,
                orientation='landscape'
            )
            
            if not results or not results.get('videos'):
                logger.warning(f"No videos found for topic: {topic}")
                return []
            
            videos = []
            for idx, video in enumerate(results['videos'][:num_videos]):
                video_data = {
                    'pexels_id': video.get('id'),
                    'title': video.get('url', '').split('/')[-1],
                    'url': video.get('url'),
                    'duration': video.get('duration'),
                    'width': video.get('width'),
                    'height': video.get('height'),
                    'photographer': video.get('user', {}).get('name'),
                    'videos': []
                }
                
                # Find best quality video file
                for quality in ['hd', 'sd']:
                    for video_file in video.get('video_files', []):
                        if video_file.get('quality') == quality:
                            video_data['videos'].append({
                                'quality': quality,
                                'url': video_file.get('link'),
                                'height': video_file.get('height'),
                                'width': video_file.get('width'),
                            })
                            break
                
                videos.append(video_data)
            
            logger.info(f"Retrieved {len(videos)} videos for topic: {topic}")
            return videos
            
        except Exception as e:
            logger.error(f"Error getting videos for topic: {str(e)}")
            return []
    
    def download_videos_for_topic(
        self,
        topic: str,
        output_dir: str,
        num_videos: int = 3
    ) -> List[str]:
        """
        Download stock videos for a topic
        
        Args:
            topic: Topic/keyword to search for
            output_dir: Directory to save videos
            num_videos: Number of videos to download
            
        Returns:
            List of downloaded video file paths
        """
        try:
            # Get videos for topic
            videos = self.get_videos_for_topic(topic, num_videos=num_videos)
            
            if not videos:
                logger.warning(f"No videos found for topic: {topic}")
                return []
            
            downloaded_videos = []
            
            for idx, video in enumerate(videos):
                try:
                    # Get HD quality video URL if available
                    video_url = None
                    for video_file in video.get('videos', []):
                        if video_file.get('quality') == 'hd':
                            video_url = video_file.get('url')
                            break
                    
                    if not video_url and video.get('videos'):
                        video_url = video['videos'][0].get('url')
                    
                    if not video_url:
                        logger.warning(f"No video URL found for {video['title']}")
                        continue
                    
                    # Download video
                    filename = f"{topic.replace(' ', '_')}_{idx + 1}.mp4"
                    output_path = os.path.join(output_dir, filename)
                    
                    if self.download_video(video_url, output_path):
                        downloaded_videos.append(output_path)
                    
                except Exception as e:
                    logger.error(f"Error downloading video {idx + 1}: {str(e)}")
                    continue
            
            logger.info(f"Downloaded {len(downloaded_videos)} videos for topic: {topic}")
            return downloaded_videos
            
        except Exception as e:
            logger.error(f"Error downloading videos for topic: {str(e)}")
            return []
    
    def search_similar_videos(
        self,
        video_id: int,
        num_videos: int = 5
    ) -> List[Dict]:
        """
        Search for similar videos
        
        Args:
            video_id: Pexels video ID
            num_videos: Number of similar videos to return
            
        Returns:
            List of similar videos
        """
        try:
            url = f"https://api.pexels.com/videos/{video_id}"
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            # Note: Pexels API doesn't directly return similar videos
            # This would need to be implemented using keyword extraction
            logger.info(f"Retrieved metadata for video: {video_id}")
            
            return []
            
        except Exception as e:
            logger.error(f"Error searching similar videos: {str(e)}")
            return []
    
    def get_video_metadata(self, video_id: int) -> Optional[Dict]:
        """
        Get detailed metadata for a video
        
        Args:
            video_id: Pexels video ID
            
        Returns:
            Video metadata dictionary
        """
        try:
            url = f"https://api.pexels.com/videos/{video_id}"
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            video = response.json()
            
            metadata = {
                'id': video.get('id'),
                'url': video.get('url'),
                'duration': video.get('duration'),
                'width': video.get('width'),
                'height': video.get('height'),
                'photographer': video.get('user', {}).get('name'),
                'photographer_url': video.get('user', {}).get('url'),
            }
            
            logger.info(f"Retrieved metadata for video: {video_id}")
            return metadata
            
        except Exception as e:
            logger.error(f"Error getting video metadata: {str(e)}")
            return None
