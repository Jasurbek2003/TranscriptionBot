"""Gemini-based transcription service."""

import asyncio
import base64
import tempfile
import time
from pathlib import Path
from typing import Dict, Any, Union
from google import genai
from google.genai import types

from .base import BaseTranscriptionService
from core.logging import logger


class GeminiTranscriptionService(BaseTranscriptionService):
    """Gemini API transcription service."""

    def __init__(self, api_key: str):
        """Initialize Gemini transcription service.

        Args:
            api_key: Gemini API key
        """
        super().__init__(api_key)
        self.client = genai.Client(api_key=api_key)
        self.model = 'gemini-2.0-flash-exp'

    async def transcribe_from_bytes(self, file_bytes: bytes, media_type: str, duration: int = 0) -> str:
        """Transcribe media from bytes.

        Args:
            file_bytes: Media file content as bytes
            media_type: Type of media ("audio" or "video")
            duration: Duration in seconds

        Returns:
            Transcribed text
        """
        try:
            logger.info(f"Transcribing {media_type} from bytes (duration: {duration}s)")

            # Encode file data to base64
            file_data_base64 = base64.b64encode(file_bytes).decode('utf-8')

            # Create prompt
            prompt = """
            Please transcribe the audio/video content in this file.
            Provide only the transcribed text without any additional commentary or formatting.
            If there are multiple speakers, indicate speaker changes with [Speaker 1], [Speaker 2], etc.
            """

            # Create content with inline data using new API
            contents = [
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text=prompt),
                        types.Part(
                            inline_data=types.Blob(
                                mime_type=self._get_mime_type(media_type),
                                data=file_data_base64
                            )
                        ),
                    ],
                ),
            ]

            # Generate content using new API
            logger.info("Sending request to Gemini API...")
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model,
                contents=contents,
            )

            transcription_text = response.text.strip()
            logger.info(f"Transcription completed successfully ({len(transcription_text)} characters)")

            return transcription_text

        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            return None

    def _get_file_extension(self, media_type: str) -> str:
        """Get appropriate file extension for media type."""
        return "mp4" if media_type == "video" else "mp3"

    def _get_mime_type(self, media_type: str) -> str:
        """Get appropriate MIME type for media type."""
        if media_type == "video":
            return "video/mp4"
        return "audio/mpeg"

    async def transcribe_audio(self, file_path: Path, language: str = "auto") -> Dict[str, Any]:
        """Transcribe audio file using Gemini API.

        Args:
            file_path: Path to the audio file
            language: Language code for transcription

        Returns:
            Dictionary with transcription results
        """
        try:
            logger.info(f"Transcribing audio file: {file_path}")

            # For now, return a placeholder response
            # In a full implementation, you would upload the file to Gemini
            # and process the transcription
            return {
                "text": "Audio transcription placeholder - Gemini service not fully implemented",
                "confidence": 0.0,
                "language": language,
                "duration": 0
            }

        except Exception as e:
            logger.error(f"Audio transcription failed: {e}")
            raise

    async def transcribe_video(self, file_path: Path, language: str = "auto") -> Dict[str, Any]:
        """Transcribe video file using Gemini API.

        Args:
            file_path: Path to the video file
            language: Language code for transcription

        Returns:
            Dictionary with transcription results
        """
        try:
            logger.info(f"Transcribing video file: {file_path}")

            # For now, return a placeholder response
            return {
                "text": "Video transcription placeholder - Gemini service not fully implemented",
                "confidence": 0.0,
                "language": language,
                "duration": 0
            }

        except Exception as e:
            logger.error(f"Video transcription failed: {e}")
            raise

    async def get_supported_formats(self) -> Dict[str, list]:
        """Get supported audio and video formats.

        Returns:
            Dictionary with supported formats
        """
        return {
            "audio": ["mp3", "wav", "m4a", "ogg", "flac"],
            "video": ["mp4", "avi", "mov", "mkv", "webm"]
        }