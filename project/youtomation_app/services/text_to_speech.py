"""
Text to Speech Service
Converts scripts to audio using gTTS or Coqui TTS
"""
import logging
import os
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class TextToSpeechService:
    """Service for converting text to speech"""
    
    def __init__(self, engine: str = 'gtts', language: str = 'en'):
        """
        Initialize TTS service
        
        Args:
            engine: TTS engine ('gtts' or 'coqui')
            language: Language code (e.g., 'en', 'es', 'fr')
        """
        self.engine = engine.lower()
        self.language = language
        
        if self.engine == 'coqui':
            self._initialize_coqui()
        elif self.engine != 'gtts':
            raise ValueError(f"Unsupported TTS engine: {engine}")
        
        logger.info(f"Text-to-Speech service initialized with {self.engine} engine")
    
    def _initialize_coqui(self):
        """Initialize Coqui TTS"""
        try:
            from TTS.api import TTS
            # Use 'tts_models/en/ljspeech/tacotron2-DDC' for high quality
            self.tts_model = TTS(model_name='tts_models/en/ljspeech/tacotron2-DDC', gpu=False)
            logger.info("Coqui TTS model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Coqui TTS: {str(e)}")
            raise
    
    def generate_audio_gtts(
        self,
        text: str,
        output_path: str,
        language: str = None,
        slow: bool = False
    ) -> bool:
        """
        Generate audio using Google Text-to-Speech
        
        Args:
            text: Text to convert to speech
            output_path: Path to save audio file
            language: Language code (override default)
            slow: If True, slower speech rate
            
        Returns:
            True if successful, False otherwise
        """
        try:
            from gtts import gTTS
            
            lang = language or self.language
            
            # Create gtts object
            tts = gTTS(text=text, lang=lang, slow=slow)
            
            # Create output directory if needed
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Save audio
            tts.save(output_path)
            
            file_size = os.path.getsize(output_path)
            logger.info(f"Audio generated with gTTS: {output_path} ({file_size / 1024:.2f} KB)")
            
            return True
            
        except Exception as e:
            logger.error(f"Error generating audio with gTTS: {str(e)}")
            return False
    
    def generate_audio_coqui(
        self,
        text: str,
        output_path: str,
        speaker: str = 'ljspeech',
        speed: float = 1.0
    ) -> bool:
        """
        Generate audio using Coqui TTS
        
        Args:
            text: Text to convert to speech
            output_path: Path to save audio file
            speaker: Speaker model
            speed: Speech speed (0.5-2.0)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not hasattr(self, 'tts_model'):
                logger.error("Coqui TTS model not initialized")
                return False
            
            # Create output directory if needed
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Generate speech
            self.tts_model.tts_to_file(
                text=text,
                file_path=output_path,
                speaker=speaker,
                speed=speed
            )
            
            file_size = os.path.getsize(output_path)
            logger.info(f"Audio generated with Coqui: {output_path} ({file_size / 1024:.2f} KB)")
            
            return True
            
        except Exception as e:
            logger.error(f"Error generating audio with Coqui: {str(e)}")
            return False
    
    def generate_audio(
        self,
        text: str,
        output_path: str,
        **kwargs
    ) -> bool:
        """
        Generate audio using configured engine
        
        Args:
            text: Text to convert to speech
            output_path: Path to save audio file
            **kwargs: Additional parameters for the engine
            
        Returns:
            True if successful, False otherwise
        """
        if not text or not text.strip():
            logger.error("Empty text provided for audio generation")
            return False
        
        if self.engine == 'gtts':
            return self.generate_audio_gtts(text, output_path, **kwargs)
        elif self.engine == 'coqui':
            return self.generate_audio_coqui(text, output_path, **kwargs)
        else:
            logger.error(f"Unknown TTS engine: {self.engine}")
            return False
    
    def split_text_by_duration(
        self,
        text: str,
        target_duration: int = 30,
        engine: str = None
    ) -> list:
        """
        Split text into chunks for target duration
        
        Estimated speech rates:
        - gTTS: ~150 words per minute
        - Coqui: ~160 words per minute
        
        Args:
            text: Text to split
            target_duration: Target duration per chunk in seconds
            engine: Override engine for calculation
            
        Returns:
            List of text chunks
        """
        engine = engine or self.engine
        
        # Words per minute estimation
        wpm = 160 if engine == 'coqui' else 150
        wps = wpm / 60  # Words per second
        
        # Target words per chunk
        target_words = int(target_duration * wps)
        
        words = text.split()
        chunks = []
        current_chunk = []
        
        for word in words:
            current_chunk.append(word)
            if len(current_chunk) >= target_words:
                chunks.append(' '.join(current_chunk))
                current_chunk = []
        
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        logger.info(f"Text split into {len(chunks)} chunks with target {target_duration}s duration")
        return chunks
    
    def sanitize_text(self, text: str) -> str:
        """
        Sanitize text for TTS
        
        Args:
            text: Text to sanitize
            
        Returns:
            Sanitized text
        """
        # Replace common abbreviations
        replacements = {
            'Mr.': 'Mister',
            'Mrs.': 'Missus',
            'Dr.': 'Doctor',
            'Prof.': 'Professor',
            'USP': 'U.S.P',
            'CEO': 'C.E.O',
            'API': 'A.P.I',
            'URL': 'U.R.L',
            'HTTP': 'H.T.T.P',
        }
        
        for original, replacement in replacements.items():
            text = text.replace(original, replacement)
        
        return text
    
    def get_audio_duration(self, audio_path: str) -> Optional[float]:
        """
        Get duration of audio file in seconds
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Duration in seconds, or None if error
        """
        try:
            from pydub import AudioSegment
            
            audio = AudioSegment.from_file(audio_path)
            duration = len(audio) / 1000.0  # Convert to seconds
            
            logger.info(f"Audio duration: {duration:.2f}s")
            return duration
            
        except Exception as e:
            logger.error(f"Error getting audio duration: {str(e)}")
            return None
    
    def combine_audio_chunks(
        self,
        audio_paths: list,
        output_path: str,
        gap_ms: int = 500
    ) -> bool:
        """
        Combine multiple audio files into one
        
        Args:
            audio_paths: List of audio file paths
            output_path: Output audio file path
            gap_ms: Gap between audio chunks in milliseconds
            
        Returns:
            True if successful, False otherwise
        """
        try:
            from pydub import AudioSegment
            
            if not audio_paths:
                logger.error("No audio files to combine")
                return False
            
            # Load first audio
            combined = AudioSegment.from_file(audio_paths[0])
            
            # Add remaining audio files with gaps
            for audio_path in audio_paths[1:]:
                gap = AudioSegment.silent(duration=gap_ms)
                audio = AudioSegment.from_file(audio_path)
                combined += gap + audio
            
            # Create output directory if needed
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Export combined audio
            combined.export(output_path, format='mp3', bitrate='192k')
            
            file_size = os.path.getsize(output_path)
            duration = len(combined) / 1000.0
            logger.info(f"Audio combined: {output_path} ({duration:.2f}s, {file_size / 1024:.2f} KB)")
            
            return True
            
        except Exception as e:
            logger.error(f"Error combining audio files: {str(e)}")
            return False
