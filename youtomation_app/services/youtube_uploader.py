"""
YouTube Uploader Service
Handles uploading videos to YouTube using Data API v3
"""
import os
import logging
from typing import Dict, Optional, List
import time

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.api_python_client import discovery
from google.api_python_client.errors import HttpError

logger = logging.getLogger(__name__)

# YouTube API scopes
YOUTUBE_SCOPES = ['https://www.googleapis.com/auth/youtube.upload']


class YouTubeUploaderService:
    """Service for uploading videos to YouTube"""
    
    def __init__(self, client_id: str, client_secret: str, access_token: str = None, refresh_token: str = None):
        """Initialize YouTube uploader service"""
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.youtube = None
    
    def authenticate(self, token_file: str = 'token.json', credentials_file: str = 'credentials.json') -> bool:
        """
        Authenticate with YouTube API
        
        Args:
            token_file: Path to stored token
            credentials_file: Path to OAuth2 credentials file
            
        Returns:
            True if authenticated successfully
        """
        try:
            creds = None
            
            # Load existing token
            if os.path.exists(token_file):
                creds = Credentials.from_authorized_user_file(token_file, YOUTUBE_SCOPES)
            
            # Use provided access token if no file token
            if not creds and self.access_token:
                creds = Credentials(token=self.access_token, refresh_token=self.refresh_token)
            
            # If no token, authenticate using flow
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        credentials_file, YOUTUBE_SCOPES
                    )
                    creds = flow.run_console()
                
                # Save token for reuse
                with open(token_file, 'w') as token:
                    token.write(creds.to_json())
            
            self.youtube = discovery.build('youtube', 'v3', credentials=creds)
            logger.info("Successfully authenticated with YouTube API")
            return True
            
        except Exception as e:
            logger.error(f"YouTube authentication failed: {str(e)}")
            raise
    
    def upload_video(
        self,
        video_path: str,
        title: str,
        description: str,
        tags: List[str],
        category_id: str = '22',
        is_private: bool = False,
        is_not_for_kids: bool = True,
        **kwargs
    ) -> Optional[str]:
        """
        Upload video to YouTube
        
        Args:
            video_path: Path to video file
            title: Video title
            description: Video description
            tags: List of tags
            category_id: YouTube category ID (22=People & Blogs, 24=Entertainment, etc.)
            is_private: If True, video won't be searchable
            is_not_for_kids: Content is not made for kids
            **kwargs: Additional metadata
            
        Returns:
            YouTube video ID if successful, None otherwise
        """
        if not self.youtube:
            logger.error("Not authenticated with YouTube API")
            return None
        
        if not os.path.exists(video_path):
            logger.error(f"Video file not found: {video_path}")
            return None
        
        try:
            body = {
                'snippet': {
                    'title': title,
                    'description': description,
                    'tags': tags,
                    'categoryId': category_id,
                    'defaultLanguage': kwargs.get('language', 'en'),
                    'defaultAudioLanguage': kwargs.get('language', 'en'),
                },
                'status': {
                    'privacyStatus': 'private' if is_private else 'public',
                    'selfDeclaredMadeForKids': not is_not_for_kids,
                    'embeddable': True,
                    'publicStatsViewable': True,
                },
                'processingDetails': {
                    'processingStatus': 'processing'
                }
            }
            
            # Add optional fields
            if 'license' in kwargs:
                body['status']['license'] = kwargs['license']
            
            if 'recordingDetails' in kwargs:
                body['recordingDetails'] = kwargs['recordingDetails']
            
            # Get file size for resumable upload
            file_size = os.path.getsize(video_path)
            logger.info(f"Uploading video: {title} ({file_size / (1024**2):.2f} MB)")
            
            # Create media upload
            from googleapiclient.http import MediaFileUpload
            media = MediaFileUpload(video_path, chunksize=262144, resumable=True)
            
            # Execute insert request
            request = self.youtube.videos().insert(
                part='snippet,status,processingDetails',
                body=body,
                media_body=media
            )
            
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    progress = int(status.progress() * 100)
                    logger.info(f"Upload progress: {progress}%")
            
            video_id = response['id']
            logger.info(f"Video uploaded successfully. Video ID: {video_id}")
            
            return video_id
            
        except HttpError as e:
            logger.error(f"An HTTP error {e.resp.status} occurred: {e.content}")
            raise
        except Exception as e:
            logger.error(f"Error uploading video: {str(e)}")
            raise
    
    def get_video_status(self, video_id: str) -> Optional[Dict]:
        """
        Get video processing status
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            Video status information
        """
        if not self.youtube:
            return None
        
        try:
            request = self.youtube.videos().list(
                part='status,processingDetails',
                id=video_id
            )
            response = request.execute()
            
            if response['items']:
                return {
                    'status': response['items'][0].get('status', {}),
                    'processingDetails': response['items'][0].get('processingDetails', {})
                }
            return None
            
        except Exception as e:
            logger.error(f"Error getting video status: {str(e)}")
            return None
    
    def wait_for_processing(self, video_id: str, max_wait_seconds: int = 3600) -> bool:
        """
        Wait for YouTube to finish processing video
        
        Args:
            video_id: YouTube video ID
            max_wait_seconds: Maximum time to wait
            
        Returns:
            True if processing completed, False if timeout
        """
        start_time = time.time()
        check_interval = 30  # Check every 30 seconds
        
        while time.time() - start_time < max_wait_seconds:
            status = self.get_video_status(video_id)
            if status and status.get('processingDetails', {}).get('processingStatus') == 'succeeded':
                logger.info(f"Video {video_id} processing completed")
                return True
            
            logger.info(f"Waiting for video processing... {int(time.time() - start_time)}s elapsed")
            time.sleep(check_interval)
        
        logger.warning(f"Video processing timeout for {video_id}")
        return False
    
    def update_video_metadata(
        self,
        video_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        **kwargs
    ) -> bool:
        """
        Update video metadata
        
        Args:
            video_id: YouTube video ID
            title: New title
            description: New description
            tags: New tags
            
        Returns:
            True if updated successfully
        """
        if not self.youtube:
            return False
        
        try:
            # Get current metadata
            request = self.youtube.videos().list(
                part='snippet',
                id=video_id
            )
            response = request.execute()
            
            if not response['items']:
                logger.error(f"Video not found: {video_id}")
                return False
            
            snippet = response['items'][0]['snippet']
            
            # Update fields
            if title:
                snippet['title'] = title
            if description:
                snippet['description'] = description
            if tags:
                snippet['tags'] = tags
            
            # Update video
            request = self.youtube.videos().update(
                part='snippet',
                body={'id': video_id, 'snippet': snippet}
            )
            request.execute()
            
            logger.info(f"Video metadata updated: {video_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating video metadata: {str(e)}")
            return False
    
    def delete_video(self, video_id: str) -> bool:
        """
        Delete a video from YouTube
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            True if deleted successfully
        """
        if not self.youtube:
            return False
        
        try:
            self.youtube.videos().delete(id=video_id).execute()
            logger.info(f"Video deleted: {video_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting video: {str(e)}")
            return False
    
    def get_channel_statistics(self) -> Optional[Dict]:
        """Get channel statistics"""
        if not self.youtube:
            return None
        
        try:
            request = self.youtube.channels().list(
                part='statistics',
                mine=True
            )
            response = request.execute()
            
            if response['items']:
                return response['items'][0]['statistics']
            return None
            
        except Exception as e:
            logger.error(f"Error getting channel statistics: {str(e)}")
            return None
