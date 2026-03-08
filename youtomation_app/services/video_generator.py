"""
Video Generator Service
Creates videos using MoviePy with stock footage and narration
"""
import logging
import os
import math
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from datetime import timedelta

logger = logging.getLogger(__name__)


class VideoGeneratorService:
    """Service for generating videos using MoviePy"""
    
    def __init__(
        self,
        output_dir: str,
        fps: int = 30,
        resolution: Tuple[int, int] = (1920, 1080),
        min_duration: int = 240,  # 4 minutes
        max_duration: int = 480,  # 8 minutes
    ):
        """
        Initialize video generator
        
        Args:
            output_dir: Directory to save generated videos
            fps: Frames per second (default: 30)
            resolution: Video resolution (default: 1920x1080)
            min_duration: Minimum video duration in seconds
            max_duration: Maximum video duration in seconds
        """
        self.output_dir = output_dir
        self.fps = fps
        self.resolution = resolution
        self.min_duration = min_duration
        self.max_duration = max_duration
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        logger.info(f"Video Generator initialized: {resolution}@{fps}fps")
    
    def generate_video(
        self,
        audio_file: str,
        stock_videos: List[str],
        subtitles: List[Dict] = None,
        output_file: str = None,
        title: str = 'Untitled'
    ) -> Optional[str]:
        """
        Generate complete video with audio and stock footage
        
        Args:
            audio_file: Path to audio file (narration)
            stock_videos: List of stock video file paths
            subtitles: List of subtitle dictionaries with start_time, end_time, text
            output_file: Output video file path
            title: Video title for logging
            
        Returns:
            Path to generated video file, or None if failed
        """
        try:
            from moviepy.editor import (
                VideoFileClip, AudioFileClip, CompositeVideoClip,
                CompositeAudioClip, vfx, TextClip, ColorClip
            )
            from moviepy.video.io.ffmpeg_tools import ffmpeg_extract_subclip
            import numpy as np
            
            logger.info(f"Starting video generation: {title}")
            
            # Validate inputs
            if not os.path.exists(audio_file):
                logger.error(f"Audio file not found: {audio_file}")
                return None
            
            if not stock_videos:
                logger.error("No stock videos provided")
                return None
            
            # Load audio to get duration
            try:
                audio_clip = AudioFileClip(audio_file)
                audio_duration = audio_clip.duration
            except Exception as e:
                logger.error(f"Error loading audio: {str(e)}")
                return None
            
            # Validate duration
            if audio_duration < self.min_duration:
                logger.warning(f"Audio too short: {audio_duration}s (min: {self.min_duration}s)")
                return None
            if audio_duration > self.max_duration:
                logger.warning(f"Audio too long: {audio_duration}s (max: {self.max_duration}s)")
                # Trim audio to max duration
                audio_clip = audio_clip.subclipped(0, self.max_duration)
                audio_duration = self.max_duration
            
            # Load and compose stock videos
            logger.info(f"Loading {len(stock_videos)} stock videos")
            video_clips = []
            total_loaded_duration = 0
            
            for video_path in stock_videos:
                if not os.path.exists(video_path):
                    logger.warning(f"Stock video not found: {video_path}")
                    continue
                
                try:
                    clip = VideoFileClip(video_path)
                    # Resize to target resolution
                    clip = clip.resize(height=self.resolution[1])
                    video_clips.append(clip)
                    total_loaded_duration += clip.duration
                    logger.debug(f"Loaded video: {video_path} ({clip.duration:.1f}s)")
                except Exception as e:
                    logger.error(f"Error loading stock video {video_path}: {str(e)}")
                    continue
            
            if not video_clips:
                logger.error("No valid stock videos loaded")
                return None
            
            # Create composite video by looping/cutting stock videos to match audio duration
            logger.info(f"Creating composite video (target duration: {audio_duration:.1f}s)")
            composite_clips = []
            current_time = 0
            
            while current_time < audio_duration:
                for clip in video_clips:
                    if current_time >= audio_duration:
                        break
                    
                    # Calculate how much of this clip we need
                    remaining_duration = audio_duration - current_time
                    clip_duration = min(clip.duration, remaining_duration)
                    
                    # Trim clip to needed duration
                    trimmed_clip = clip.subclipped(0, clip_duration)
                    trimmed_clip = trimmed_clip.set_start(current_time)
                    composite_clips.append(trimmed_clip)
                    
                    current_time += clip_duration
            
            # Create final video
            final_video = CompositeVideoClip(
                composite_clips,
                size=self.resolution
            )
            final_video = final_video.set_duration(audio_duration)
            
            # Add audio
            final_video = final_video.set_audio(audio_clip)
            
            # Add subtitles if provided
            if subtitles:
                logger.info(f"Adding {len(subtitles)} subtitles")
                final_video = self._add_subtitles(final_video, subtitles)
            
            # Generate output filename
            if not output_file:
                output_file = os.path.join(
                    self.output_dir,
                    f"{title.replace(' ', '_')}_{int(audio_duration)}s.mp4"
                )
            
            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            
            # Write video file
            logger.info(f"Writing video to: {output_file}")
            final_video.write_videofile(
                output_file,
                fps=self.fps,
                codec='libx264',
                audio_codec='aac',
                verbose=False,
                logger=None
            )
            
            # Cleanup
            for clip in video_clips:
                try:
                    clip.close()
                except:
                    pass
            try:
                final_video.close()
                audio_clip.close()
            except:
                pass
            
            file_size = os.path.getsize(output_file)
            logger.info(f"Video generated successfully: {output_file} ({file_size / (1024**2):.2f} MB)")
            
            return output_file
            
        except ImportError as e:
            logger.error(f"MoviePy not installed: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error generating video: {str(e)}")
            return None
    
    def _add_subtitles(self, video_clip, subtitles: List[Dict]):
        """
        Add subtitles to video
        
        Args:
            video_clip: MoviePy video clip
            subtitles: List of subtitle dictionaries
            
        Returns:
            Video clip with subtitles
        """
        try:
            from moviepy.editor import TextClip, CompositeVideoClip
            
            subtitle_clips = []
            
            for subtitle in subtitles:
                try:
                    # Create text clip
                    txt_clip = TextClip(
                        subtitle['text'],
                        fontsize=subtitle.get('font_size', 48),
                        color=subtitle.get('text_color', 'white'),
                        font=subtitle.get('font_name', 'Arial'),
                        method='caption',
                        size=(self.resolution[0] - 100, None)
                    )
                    
                    # Position at bottom center
                    txt_clip = txt_clip.set_position('center')
                    txt_clip = txt_clip.set_position(('center', self.resolution[1] - 100))
                    
                    # Set timing
                    txt_clip = txt_clip.set_start(subtitle['start_time'])
                    txt_clip = txt_clip.set_duration(substrate['end_time'] - subtitle['start_time'])
                    
                    subtitle_clips.append(txt_clip)
                    
                except Exception as e:
                    logger.error(f"Error adding subtitle: {str(e)}")
                    continue
            
            if subtitle_clips:
                # Composite with video
                final = CompositeVideoClip(
                    [video_clip] + subtitle_clips,
                    size=self.resolution
                )
                return final
            
            return video_clip
            
        except Exception as e:
            logger.error(f"Error adding subtitles: {str(e)}")
            return video_clip
    
    def create_intro_clip(
        self,
        title: str,
        duration: float = 3.0,
        color: str = '000000'
    ) -> Optional[str]:
        """
        Create intro clip with title
        
        Args:
            title: Title text
            duration: Clip duration in seconds
            color: Background color (hex)
            
        Returns:
            Path to intro clip video file
        """
        try:
            from moviepy.editor import ColorClip, TextClip, CompositeVideoClip
            
            # Create background
            bg = ColorClip(size=self.resolution, color=tuple(int(color[i:i+2], 16) for i in (0, 2, 4)))
            bg = bg.set_duration(duration)
            
            # Create text
            txt = TextClip(title, fontsize=80, color='white', font='Arial-Bold')
            txt = txt.set_duration(duration)
            txt = txt.set_position('center')
            
            # Composite
            video = CompositeVideoClip([bg, txt], size=self.resolution)
            
            # Save
            output_file = os.path.join(self.output_dir, 'intro.mp4')
            video.write_videofile(output_file, fps=self.fps, verbose=False, logger=None)
            video.close()
            
            logger.info(f"Intro clip created: {output_file}")
            return output_file
            
        except Exception as e:
            logger.error(f"Error creating intro clip: {str(e)}")
            return None
    
    def create_outro_clip(
        self,
        text: str = 'Thanks for watching! Subscribe for more.',
        duration: float = 5.0,
        color: str = '000000'
    ) -> Optional[str]:
        """
        Create outro clip
        
        Args:
            text: Outro text
            duration: Clip duration in seconds
            color: Background color (hex)
            
        Returns:
            Path to outro clip video file
        """
        try:
            from moviepy.editor import ColorClip, TextClip, CompositeVideoClip
            
            # Create background
            bg = ColorClip(size=self.resolution, color=tuple(int(color[i:i+2], 16) for i in (0, 2, 4)))
            bg = bg.set_duration(duration)
            
            # Create text
            txt = TextClip(text, fontsize=60, color='white', font='Arial')
            txt = txt.set_duration(duration)
            txt = txt.set_position('center')
            
            # Composite
            video = CompositeVideoClip([bg, txt], size=self.resolution)
            
            # Save
            output_file = os.path.join(self.output_dir, 'outro.mp4')
            video.write_videofile(output_file, fps=self.fps, verbose=False, logger=None)
            video.close()
            
            logger.info(f"Outro clip created: {output_file}")
            return output_file
            
        except Exception as e:
            logger.error(f"Error creating outro clip: {str(e)}")
            return None
    
    def get_video_info(self, video_file: str) -> Optional[Dict]:
        """
        Get video file information
        
        Args:
            video_file: Path to video file
            
        Returns:
            Video information dictionary
        """
        try:
            from moviepy.editor import VideoFileClip
            
            if not os.path.exists(video_file):
                logger.error(f"Video file not found: {video_file}")
                return None
            
            clip = VideoFileClip(video_file)
            
            info = {
                'duration': clip.duration,
                'fps': clip.fps,
                'size': clip.size,
                'width': clip.size[0],
                'height': clip.size[1],
                'file_size': os.path.getsize(video_file),
            }
            
            clip.close()
            
            return info
            
        except Exception as e:
            logger.error(f"Error getting video info: {str(e)}")
            return None
