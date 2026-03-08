"""
Exceptions for video generation pipeline
"""


class VideoGenerationException(Exception):
    """Base exception for video generation errors"""
    pass


class TrendingTopicsException(VideoGenerationException):
    """Exception during trending topics fetch"""
    pass


class ScriptGenerationException(VideoGenerationException):
    """Exception during script generation"""
    pass


class TextToSpeechException(VideoGenerationException):
    """Exception during text-to-speech conversion"""
    pass


class StockVideosException(VideoGenerationException):
    """Exception during stock videos fetch"""
    pass


class VideoCreationException(VideoGenerationException):
    """Exception during video creation"""
    pass


class YouTubeUploadException(VideoGenerationException):
    """Exception during YouTube upload"""
    pass
