"""Base transcription service interface."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict


class BaseTranscriptionService(ABC):
    """Abstract base class for transcription services."""

    def __init__(self, api_key: str):
        """Initialize the transcription service.

        Args:
            api_key: API key for the service
        """
        self.api_key = api_key

    @abstractmethod
    async def transcribe_audio(self, file_path: Path, language: str = "auto") -> Dict[str, Any]:
        """Transcribe audio file.

        Args:
            file_path: Path to the audio file
            language: Language code for transcription (default: auto-detect)

        Returns:
            Dictionary containing:
                - text: Transcribed text
                - confidence: Confidence score (0-1)
                - language: Detected/used language
                - duration: Audio duration in seconds
        """
        pass

    @abstractmethod
    async def transcribe_video(self, file_path: Path, language: str = "auto") -> Dict[str, Any]:
        """Transcribe video file.

        Args:
            file_path: Path to the video file
            language: Language code for transcription (default: auto-detect)

        Returns:
            Dictionary containing:
                - text: Transcribed text
                - confidence: Confidence score (0-1)
                - language: Detected/used language
                - duration: Video duration in seconds
        """
        pass

    @abstractmethod
    async def get_supported_formats(self) -> Dict[str, list]:
        """Get supported audio and video formats.

        Returns:
            Dictionary with 'audio' and 'video' keys containing lists of supported formats
        """
        pass
